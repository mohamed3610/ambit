from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable

from .dimensions import ScopeDimension


@dataclass(frozen=True)
class ScopeBinding:
    """
    How one scope dimension reaches one model.

    The plain form is a lookup path: `queryset_lookup` filters rows
    (grade__stage__pk__in=targets) and `value_lookup` (defaulting to the
    same path) is walked as attributes off submitted form values when a
    row is being created or changed.

    The Q form is for what a path can't say -- a condition on the joined
    row itself ("taught by X *as the active primary teacher*"), or an OR
    of two routes. `q(target_ids)` returns the Q to filter with; `check`
    answers the create/change question for it, given the submitted
    values, the existing object (or None) and the resolved targets. A Q
    binding with no `check` fails closed on writes: nobody can mint a
    row through it.
    """

    queryset_lookup: str | None = None
    value_lookup: str | None = None
    q: Callable | None = None
    check: Callable | None = None

    def __post_init__(self):
        if self.queryset_lookup is None and self.q is None:
            raise ValueError("A ScopeBinding needs a lookup path or a q builder.")

    @property
    def effective_value_lookup(self):
        return self.value_lookup or self.queryset_lookup


class ScopePolicy:
    def __init__(self, bindings=None):
        normalized = {}

        for dimension, binding in (bindings or {}).items():
            normalized[ScopeDimension(dimension)] = binding

        self._bindings = MappingProxyType(normalized)

    def get_binding(self, dimension):
        try:
            dimension = ScopeDimension(dimension)
        except ValueError:
            return None

        return self._bindings.get(dimension)

    def supports(self, dimension):
        return self.get_binding(dimension) is not None

    @property
    def dimensions(self):
        """
        The dimensions this policy can express, as a hashable set.

        Used as a cache key rather than the policy object's identity:
        whether a user can reach *any* row under a policy depends only on
        which dimensions it supports, and `id()` is reusable after a
        policy is garbage collected -- fine for today's module-level
        constants, wrong the moment one is built per request.
        """
        return frozenset(self._bindings)


GLOBAL_SCOPE_POLICY = ScopePolicy()
