"""
Scope dimensions: the axes access can be limited along.

ambit ships **no** dimensions. An application registers its own and the
engine treats them all the same -- a school registers stage / department /
classroom / own-teaching; a company registers region / department / team /
own. The machinery is invariant; only the registered dimensions change.
Register once at startup, e.g. in your AppConfig.ready().

A dimension is one of two kinds:

* **row-backed** -- a grant points at a row of `model_label` (e.g. a
  Department). The scope stores which rows; the engine filters by them.
* **self-resolving** -- there is no stored row. It resolves at request
  time to the acting user's own value via `resolves_to(user)` (e.g. "own
  teaching" -> the user's Teacher record, "own" -> the user themselves).
  A user for whom it resolves to None reaches nothing through it.
"""
from dataclasses import dataclass
from typing import Callable, Optional

from django.apps import apps


@dataclass(frozen=True)
class ScopeDimensionDefinition:
    key: str
    label: str
    # Row-backed: "app_label.Model". None for a self-resolving dimension.
    model_label: Optional[str] = None
    # Self-resolving only: callable(user) -> the user's own target row (or None).
    resolves_to: Optional[Callable] = None
    # How a console offers it: "A stage", "One section" -- a sentence, because
    # a grant reads as "<person> is a <role> <preposition> <where>".
    pick_label: str = ""
    preposition: str = "in"

    @property
    def is_self_resolving(self):
        return self.model_label is None


_REGISTRY: "dict[str, ScopeDimensionDefinition]" = {}


def register_dimension(key, label, *, model_label=None, resolves_to=None,
                       pick_label="", preposition="in"):
    """Declare a dimension. Pass `model_label` for a row-backed axis OR
    `resolves_to` for a self-resolving one -- exactly one of the two."""
    key = str(key)
    if (model_label is None) == (resolves_to is None):
        raise ValueError(
            f"Dimension {key!r} must be either row-backed (model_label) or "
            f"self-resolving (resolves_to) -- not both, not neither.")
    definition = ScopeDimensionDefinition(
        key=key, label=label, model_label=model_label, resolves_to=resolves_to,
        pick_label=pick_label, preposition=preposition)
    _REGISTRY[key] = definition
    return definition


def clear_dimensions():
    """Empty the registry (tests)."""
    _REGISTRY.clear()


def registered_dimensions():
    """The registry, in registration order -- the canonical order for
    labelling and display."""
    return dict(_REGISTRY)


def get_scope_dimension(value):
    """The canonical key if registered, else None."""
    key = str(value)
    return key if key in _REGISTRY else None


def get_scope_dimension_definition(value):
    return _REGISTRY.get(str(value))


def get_scope_dimension_model(value):
    definition = get_scope_dimension_definition(value)
    if definition is None or definition.model_label is None:
        return None
    return apps.get_model(definition.model_label)


def is_self_resolved(value):
    """True for a dimension whose target is the acting user, not a stored row."""
    definition = get_scope_dimension_definition(value)
    return definition is not None and definition.model_label is None


def resolve_self(value, user):
    """The user's own target for a self-resolving dimension, or None.

    Memoized on the user for the request -- like the grant set is -- so a
    resolver that hits the database runs once per user per request.
    """
    definition = get_scope_dimension_definition(value)
    if definition is None or definition.resolves_to is None:
        return None
    cache = getattr(user, "_ambit_self_targets", None)
    if cache is None:
        cache = {}
        try:
            user._ambit_self_targets = cache
        except (AttributeError, TypeError):
            return definition.resolves_to(user)  # can't cache on this user object
    if definition.key not in cache:
        cache[definition.key] = definition.resolves_to(user)
    return cache[definition.key]


def scope_dimension_choices():
    """The choices for ScopeConstraint.dimension -- whatever is registered."""
    return [(d.key, d.label) for d in _REGISTRY.values()]
