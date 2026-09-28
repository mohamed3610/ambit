"""
Scopes as a console builds them.

An administrator doesn't think in Scope rows; she thinks "Maths, in
Region North". This turns that thought into constraints, finds the Scope
that already says exactly that -- so two people limited the same way share
one scope and it reads as one thing in a list -- or creates it with a name
a human would have typed.

Presentation strings here (WHOLE_ORG, the phrasing helpers) are sensible
defaults; an application can wrap them to match its own vocabulary.
"""

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from ..dimensions import (
    get_scope_dimension_definition,
    is_self_resolved,
    registered_dimensions,
)
from ..models import Scope, ScopeConstraint

WHOLE_ORG = "Everywhere"


def _order():
    """Dimension display order: the order they were registered in."""
    return {key: i for i, key in enumerate(registered_dimensions())}


def target_label(constraint):
    """What a constraint points at, in words: a row's name, or a
    self-resolving dimension's label."""
    if is_self_resolved(constraint.dimension):
        definition = get_scope_dimension_definition(constraint.dimension)
        return definition.label if definition else constraint.dimension
    return str(constraint.target) if constraint.target is not None else None


def constraint_keys(scope):
    """{(dimension, object_id)} -- the identity of a constrained scope."""
    return {(c.dimension, c.object_id) for c in scope.constraints.all()}


def describe(scope):
    """"North × Sales", or "Everywhere"."""
    if scope.is_global:
        return WHOLE_ORG
    order = _order()
    constraints = sorted(scope.constraints.all(), key=lambda c: order.get(c.dimension, 99))
    parts = [label for label in map(target_label, constraints) if label]
    return " × ".join(parts) or scope.name


def where_phrase(scope):
    """
    The tail of "<person> is a <role> …": "everywhere", "in Region North",
    "in North × Sales", "for own records", "in Sales, own records only".
    """
    if scope.is_global:
        return WHOLE_ORG.lower()
    order = _order()
    constraints = sorted(scope.constraints.all(), key=lambda c: order.get(c.dimension, 99))
    if scope.name and scope.name != describe(scope):
        return f"in {scope.name}"   # someone named it
    placed = [p for p in (target_label(c) for c in constraints
                          if not is_self_resolved(c.dimension)) if p]
    self_definitions = [get_scope_dimension_definition(c.dimension)
                        for c in constraints if is_self_resolved(c.dimension)]
    self_phrase = ", ".join(d.label.lower() for d in self_definitions if d)
    if placed and self_phrase:
        return f"in {' × '.join(placed)}, {self_phrase} only"
    if self_phrase:
        return f"for {self_phrase}"
    return f"in {' × '.join(placed)}" if placed else scope.name


def _normalise(targets):
    # A self-resolving dimension is picked (True) or not (False/None); the
    # others carry a row or None. Keys are normalised to string dimension keys.
    return {str(k): v for k, v in targets.items() if v is not None and v is not False}


def _name_of(dimension, target):
    definition = get_scope_dimension_definition(dimension)
    if is_self_resolved(dimension):
        return definition.label if definition else dimension
    return str(target)


def auto_name(targets):
    """"North × Sales" -- the name a person would have typed."""
    targets = _normalise(targets)
    if not targets:
        return WHOLE_ORG
    return " × ".join(_name_of(dim, targets[dim])
                      for dim in registered_dimensions() if dim in targets)


def find_scope(targets):
    """The existing scope limited to exactly these targets, or None. Never creates."""
    targets = _normalise(targets)
    if not targets:
        return Scope.objects.filter(is_global=True, is_active=True).order_by("created_at").first()

    wanted = {
        (dim, None if is_self_resolved(dim) else str(obj.pk)) for dim, obj in targets.items()
    }
    candidates = Scope.objects.filter(
        is_global=False, is_active=True,
        constraints__dimension__in=list(targets),
    ).distinct().prefetch_related("constraints")
    for scope in candidates:
        if constraint_keys(scope) == wanted:
            return scope
    return None


def scope_for(targets, name=""):
    """
    The scope limited to exactly these targets -- {dimension: instance}
    with None values ignored -- found or created. An empty mapping means
    everywhere. `name` is what a new scope is called instead of the
    spelled-out limit; an existing scope keeps the name it has.
    """
    existing = find_scope(targets)
    if existing is not None:
        return existing
    targets = _normalise(targets)
    if not targets:
        return Scope.objects.create(name=WHOLE_ORG, is_global=True)

    with transaction.atomic():
        scope = Scope.objects.create(name=name.strip() or auto_name(targets))
        for dim, obj in targets.items():
            if is_self_resolved(dim):
                ScopeConstraint.objects.create(scope=scope, dimension=dim)
            else:
                ScopeConstraint.objects.create(
                    scope=scope, dimension=dim,
                    content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk,
                )
    return scope


def dimension_fields():
    """
    (dimension_key, label, model) for every registered dimension, in order;
    model is None for a self-resolving dimension (a yes/no, not a picker).
    """
    from django.apps import apps
    return [
        (key, definition.label,
         apps.get_model(definition.model_label) if definition.model_label else None)
        for key, definition in registered_dimensions().items()
    ]
