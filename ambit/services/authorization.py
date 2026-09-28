from ..dimensions import is_self_resolved, resolve_self
from .scopes import get_scope_constraints, resolve_targets, scope_queryset


_MISSING = object()

_CACHE_ATTR = "_authorization_scope_cache"


def _split_permission(permission):
    try:
        app_label, codename = permission.split(".", 1)
    except ValueError:
        raise ValueError(
            "Permission must use the format 'app_label.codename'"
        )
    return app_label, codename


def _usable(user):
    return bool(user and user.is_authenticated and user.is_active)


def _grants(user):
    """
    Every scope this user holds, indexed by the permission that grants
    it. Two queries for the whole picture, memoized on the user.

    Built in one go rather than per permission because a single page
    render asks about a dozen *different* permissions -- one per list,
    tile and section -- and a per-permission query meant a dozen
    near-identical joins. Constraints are loaded only for scopes that
    have them: a global scope short-circuits every check without ever
    looking at one.
    """
    from django.db.models import prefetch_related_objects

    from ..models import Scope

    # (app_label, codename, scope_id) triples. Both permission halves
    # come off the SAME joined permission row, which is the property the
    # original single-filter() form existed to guarantee: read across
    # two separate joins, a codename from one role could pair with an
    # app_label from another.
    triples = (
        Scope.objects.filter(
            assignments__user=user,
            assignments__is_active=True,
            assignments__role__is_active=True,
            is_active=True,
        )
        .values_list(
            "assignments__role__permissions__content_type__app_label",
            "assignments__role__permissions__codename",
            "pk",
        )
        .distinct()
    )

    by_permission = {}
    wanted = set()
    for app_label, codename, scope_id in triples:
        if app_label is None or codename is None:
            continue  # a role with no permissions grants nothing
        by_permission.setdefault(f"{app_label}.{codename}", set()).add(scope_id)
        wanted.add(scope_id)

    if not wanted:
        return {}

    scopes = {s.pk: s for s in Scope.objects.filter(pk__in=wanted)}

    # Only constrained scopes need their constraints resolved, and they
    # are resolved for all of them at once rather than per scope.
    constrained = [s for s in scopes.values() if not s.is_global]
    if constrained:
        prefetch_related_objects(constrained, "constraints__target")

    return {
        permission: [scopes[sid] for sid in sorted(ids, key=str) if sid in scopes]
        for permission, ids in by_permission.items()
    }


def authorized_scopes(user, permission):
    """
    Every active Scope granting `permission` to this user, with each
    scope's constraints -- and each constraint's target object -- already
    loaded when it has any.

    Memoized on the user instance. `request.user` is one object for the
    life of a request, so the cache is naturally request-scoped and
    cannot leak between users or survive into the next request. It
    caches the *grant set*, not any decision about an object, so it can
    never widen access to a specific record; the scope checks themselves
    still run in full on every call. Code that changes a user's own role
    assignments mid-request must call `clear_authorization_cache(user)`
    -- nothing does today.
    """
    if not _usable(user):
        return []

    # Validates the format even when the answer is cached.
    _split_permission(permission)

    grants = getattr(user, _CACHE_ATTR, None)
    if grants is None:
        grants = _grants(user)
        setattr(user, _CACHE_ATTR, grants)

    return grants.get(permission, [])


def clear_authorization_cache(user):
    """Drop the memoized grant set -- after changing this user's roles."""
    if user is not None and hasattr(user, _CACHE_ATTR):
        delattr(user, _CACHE_ATTR)


def has_global_scope(user, permission):
    """
    Does a grant of `permission` reach everything? A superuser
    does, the same way `authorized_queryset` and `has_authorized_scope`
    already answer for one -- callers must never read the grant set
    directly to decide this, or the superuser falls through the floor.
    """
    if not _usable(user):
        return False
    if user.is_superuser:
        return True
    return any(scope.is_global for scope in authorized_scopes(user, permission))


def has_any_scope(user, permission):
    """Does any grant, whatever its scope, carry `permission`? A superuser: yes."""
    if not _usable(user):
        return False
    if user.is_superuser:
        return True
    return bool(authorized_scopes(user, permission))


def authorized_queryset(
    user,
    permission,
    queryset,
    policy,
):
    if not _usable(user):
        return queryset.none()

    if user.is_superuser:
        return queryset

    scopes = authorized_scopes(user, permission)

    if not scopes:
        return queryset.none()

    # Resolved in memory now, not with two extra COUNT queries.
    if any(scope.is_global for scope in scopes):
        return queryset

    # Which rows the scopes reach, as a set of primary keys...
    reached = queryset.model._default_manager.none()
    for scope in scopes:
        reached = reached | scope_queryset(
            queryset.model._default_manager.all(), scope, policy, user=user,
        )

    # ...applied to the caller's queryset as a semi-join. The scope Qs
    # walk multi-valued relations (a user's many assignments, a row's
    # many links), so filtering the caller's rows through those joins
    # directly would multiply them -- DISTINCT hides that from a list
    # but not from a Count() the caller adds afterwards, and it costs a
    # hash over every column (ciphertext included). `pk IN (subquery)`
    # keeps the caller's ordering, select_related and annotations
    # intact, and -- as long as the subquery carries no DISTINCT --
    # Postgres pulls it up into a semi-join driven by the caller's
    # indexes (the date index on registers, say) rather than
    # materialising every reachable row first.
    return queryset.filter(pk__in=reached.values("pk"))


def can_access_object(
    user,
    permission,
    obj,
    policy,
):
    """
    Can the user perform `permission` on this exact object?
    """

    queryset = obj.__class__.objects.filter(
        pk=obj.pk
    )

    return authorized_queryset(
        user,
        permission,
        queryset,
        policy,
    ).exists()


def can_access_values(
    user,
    permission,
    values,
    policy,
    fallback_obj=None,
):
    if not _usable(user):
        return False

    if user.is_superuser:
        return True

    for scope in authorized_scopes(user, permission):
        if scope.is_global:
            return True

        constraints = get_scope_constraints(scope)

        if not constraints:
            continue

        if _values_satisfy_constraints(
            values,
            constraints,
            policy,
            fallback_obj=fallback_obj,
            user=user,
        ):
            return True

    return False


def can_create(
    user,
    permission,
    values,
    policy,
):
    return can_access_values(
        user,
        permission,
        values,
        policy,
    )


def can_update(
    user,
    permission,
    obj,
    values,
    policy,
):
    if not can_access_object(
        user,
        permission,
        obj,
        policy,
    ):
        return False

    return can_access_values(
        user,
        permission,
        values,
        policy,
        fallback_obj=obj,
    )


def _values_satisfy_constraints(
    values,
    constraints,
    policy,
    fallback_obj=None,
    user=None,
):
    for dimension, targets in constraints.items():
        binding = policy.get_binding(dimension)

        if binding is None:
            return False

        targets = resolve_targets(dimension, targets, user)

        if not targets:
            return False

        if binding.check is not None:
            if not binding.check(values, fallback_obj, targets):
                return False
            continue

        if binding.effective_value_lookup is None:
            # A Q-only binding with no write check: nobody creates or
            # moves a row through it.
            return False

        value = _resolve_value(
            values,
            fallback_obj,
            binding.effective_value_lookup,
        )

        if value is _MISSING:
            return False

        if value not in targets:
            return False

    return True


def _resolve_value(
    values,
    obj,
    lookup,
):
    """
    Resolve a scope value from submitted form values first,
    then fall back to the existing object.

    Supports nested lookups such as:

        team__region
        member__team__region
    """

    parts = lookup.split("__")
    root = parts[0]

    # A "pk" binding means the scope targets *this model's own rows*
    # (a Team scoped by team, a Region scoped by region). The value
    # to compare against the scope's targets is then the object itself,
    # not its pk -- targets are model instances, and a UUID is never
    # `in` a list of those. On create there is no object yet, so this
    # fails closed: a scope can't mint new rows of the thing it is
    # scoped to.
    if lookup == "pk":
        return obj if obj is not None else _MISSING

    if root in values:
        value = values[root]

    elif obj is not None:
        value = getattr(
            obj,
            root,
            _MISSING,
        )

    else:
        return _MISSING

    if value is _MISSING:
        return _MISSING

    for part in parts[1:]:
        if value is None:
            return None

        value = getattr(
            value,
            part,
            _MISSING,
        )

        if value is _MISSING:
            return _MISSING

    return value


def has_authorized_scope(
    user,
    permission,
    policy,
):
    """
    Could this user reach *any* row of this kind of thing? The coarse
    "should this page/link/section exist for them at all" question --
    not "may they touch this specific object", which is
    can_access_object().

    Answered from the memoized grant set (see authorized_scopes), and
    the verdict itself memoized per policy on top -- the UI asks this
    once per nav item, per dashboard tile and per section heading, so a
    single page render asks it 15+ times with the same few arguments.
    """
    if not _usable(user):
        return False

    if user.is_superuser:
        return True

    cache = getattr(user, "_authorized_scope_cache", None)
    if cache is None:
        cache = {}
        user._authorized_scope_cache = cache

    # Keyed on what the answer actually depends on -- see
    # ScopePolicy.dimensions -- not the policy object's identity.
    key = (permission, policy.dimensions)
    if key in cache:
        return cache[key]

    result = _has_authorized_scope_uncached(user, permission, policy)
    cache[key] = result
    return result


def _has_authorized_scope_uncached(
    user,
    permission,
    policy,
):
    for scope in authorized_scopes(user, permission):
        if scope.is_global:
            return True

        constraints = get_scope_constraints(scope)

        if not constraints:
            continue

        valid = True

        for dimension, targets in constraints.items():
            if not targets:
                valid = False
                break

            if not policy.supports(dimension):
                valid = False
                break

            # A self-resolving grant reaches nothing for a user it resolves
            # to None for, so the page or link should not exist for them.
            if is_self_resolved(dimension) and resolve_self(dimension, user) is None:
                valid = False
                break

        if valid:
            return True

    return False