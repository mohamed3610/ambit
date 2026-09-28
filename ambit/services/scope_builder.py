"""
Scopes as the console builds them.

An administrator doesn't think in Scope rows; she thinks "Maths, in
Primary". This turns that thought into constraints, finds the Scope that
already says exactly that -- so two people limited the same way share
one scope and it reads as one thing in the Scopes list -- or creates it
with a name a human would have typed.
"""

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from ..dimensions import SCOPE_DIMENSIONS, ScopeDimension, is_self_resolved
from ..models import Scope, ScopeConstraint

WHOLE_SCHOOL = "Whole school"


def target_label(constraint):
    """"Primary", "Own teaching" -- what a constraint points at, in words."""
    if is_self_resolved(constraint.dimension):
        return SCOPE_DIMENSIONS[ScopeDimension(constraint.dimension)].label
    return str(constraint.target) if constraint.target is not None else None


def constraint_keys(scope):
    """{(dimension, object_id)} -- the identity of a constrained scope."""
    return {(c.dimension, c.object_id) for c in scope.constraints.all()}


def describe(scope):
    """"Primary × Mathematics", or "Whole school"."""
    if scope.is_global:
        return WHOLE_SCHOOL
    order = {dim.value: i for i, dim in enumerate(ScopeDimension)}
    constraints = sorted(scope.constraints.all(), key=lambda c: order.get(c.dimension, 99))
    parts = [label for label in map(target_label, constraints) if label]
    return " × ".join(parts) or scope.name


def where_phrase(scope):
    """
    The tail of "<person> is a <role> …": "for the whole school",
    "in Grade 1 · A", "in Primary × Mathematics", "for what they teach
    themselves", "in Mathematics, only what they teach themselves".
    """
    if scope.is_global:
        return f"for the {WHOLE_SCHOOL.lower()}"
    order = {dim.value: i for i, dim in enumerate(ScopeDimension)}
    constraints = sorted(scope.constraints.all(), key=lambda c: order.get(c.dimension, 99))
    if scope.name and scope.name != describe(scope):
        return f"in {scope.name}"   # someone named it: "in Primary maths, section A"
    placed = [target_label(c) for c in constraints if not is_self_resolved(c.dimension)]
    own = any(is_self_resolved(c.dimension) for c in constraints)
    placed = [p for p in placed if p]
    if placed and own:
        return f"in {' × '.join(placed)}, only what they teach themselves"
    if own:
        return "for what they teach themselves"
    return f"in {' × '.join(placed)}" if placed else scope.name


def _normalise(targets):
    # A self-resolving dimension is picked (True) or not (False/None);
    # the others carry a row or None.
    return {ScopeDimension(k): v for k, v in targets.items() if v is not None and v is not False}


def _name_of(dimension, target):
    return SCOPE_DIMENSIONS[dimension].label if is_self_resolved(dimension) else str(target)


def auto_name(targets):
    """"Primary × Mathematics" -- the name a person would have typed."""
    targets = _normalise(targets)
    if not targets:
        return WHOLE_SCHOOL
    return " × ".join(_name_of(dim, targets[dim]) for dim in ScopeDimension if dim in targets)


def find_scope(targets):
    """The existing scope limited to exactly these targets, or None. Never creates."""
    targets = _normalise(targets)
    if not targets:
        return Scope.objects.filter(is_global=True, is_active=True).order_by("created_at").first()

    wanted = {
        (dim.value, None if is_self_resolved(dim) else obj.pk) for dim, obj in targets.items()
    }
    candidates = Scope.objects.filter(
        is_global=False, is_active=True,
        constraints__dimension__in=[dim.value for dim in targets],
    ).distinct().prefetch_related("constraints")
    for scope in candidates:
        if constraint_keys(scope) == wanted:
            return scope
    return None


def scope_for(targets, name=""):
    """
    The scope limited to exactly these targets -- {dimension: instance}
    with None values ignored -- found or created. An empty mapping means
    the whole school. `name` is what a new scope is called ("Primary
    maths, section A") instead of the spelled-out limit; an existing
    scope keeps the name it has.
    """
    existing = find_scope(targets)
    if existing is not None:
        return existing
    targets = _normalise(targets)
    if not targets:
        return Scope.objects.create(name=WHOLE_SCHOOL, is_global=True)

    with transaction.atomic():
        scope = Scope.objects.create(name=name.strip() or auto_name(targets))
        for dim, obj in targets.items():
            if is_self_resolved(dim):
                ScopeConstraint.objects.create(scope=scope, dimension=dim.value)
            else:
                ScopeConstraint.objects.create(
                    scope=scope, dimension=dim.value,
                    content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk,
                )
    return scope


def dimension_fields():
    """
    (dimension, label, model) for every dimension in the registry, in
    order; model is None for a self-resolving dimension (a yes/no, not
    a picker).
    """
    from django.apps import apps
    return [
        (dim, definition.label, apps.get_model(definition.model_label) if definition.model_label else None)
        for dim, definition in SCOPE_DIMENSIONS.items()
    ]
