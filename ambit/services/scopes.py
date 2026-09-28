from collections import defaultdict

from ..dimensions import is_self_resolved, resolve_self


class _Self:
    """Placeholder target of a self-resolving constraint until a user resolves it."""

    def __repr__(self):
        return "<self>"


SELF_TARGET = _Self()


def get_scope_constraints(scope):
    """
    Returns the constraints grouped by dimension.

    Example:
    {
        "department": [<Department: Sales>],
        "region": [<Region: North>],
        "own": [SELF_TARGET],
    }

    Returns None for a global scope. A self-resolving constraint has no
    row to point at; its bucket holds the SELF_TARGET marker, which
    resolve_targets() swaps for the user's own target.
    """

    if not scope.is_active:
        return {}

    if scope.is_global:
        return None

    grouped = defaultdict(list)

    for constraint in scope.constraints.all():
        # Touch the dimension's bucket even if the target below turns
        # out to be broken, so a dimension with only broken targets
        # still resolves to an empty list instead of disappearing.
        # scope_queryset then filters it to __in=[], which fails
        # closed -- a missing dimension key would instead skip the
        # filter and silently widen access.
        bucket = grouped[constraint.dimension]

        if is_self_resolved(constraint.dimension):
            bucket.append(SELF_TARGET)
            continue

        target = constraint.target
        if target is not None:
            bucket.append(target)

    return dict(grouped)


def resolve_targets(dimension, targets, user):
    """The rows a constraint bucket stands for, for this user. Empty = fail closed.

    A self-resolving dimension ignores the stored bucket and resolves to the
    user's own target via the dimension's `resolves_to`; a user with no own
    target reaches nothing through it.
    """
    if is_self_resolved(dimension):
        target = resolve_self(dimension, user)
        return [target] if target is not None else []
    return targets


def scope_queryset(queryset, scope, policy, user=None):
    if not scope.is_active:
        return queryset.none()

    if scope.is_global:
        return queryset

    constraints = get_scope_constraints(scope)

    if not constraints:
        return queryset.none()

    for dimension, targets in constraints.items():
        binding = policy.get_binding(dimension)

        if binding is None:
            return queryset.none()

        target_ids = [
            target.pk
            for target in resolve_targets(dimension, targets, user)
        ]

        if binding.q is not None:
            queryset = queryset.filter(binding.q(target_ids))
            continue

        lookup = binding.queryset_lookup

        if lookup == "pk":
            queryset = queryset.filter(
                pk__in=target_ids
            )
        else:
            queryset = queryset.filter(
                **{
                    f"{lookup}__pk__in": target_ids
                }
            )

    # No DISTINCT here. The only caller (authorized_queryset) uses this
    # as a `pk IN (...)` subquery, where duplicates are harmless and a
    # DISTINCT would stop Postgres pulling the subquery up into a
    # semi-join driven by the caller's own indexes -- with it, every
    # scoped register list scanned the whole table first.
    return queryset
