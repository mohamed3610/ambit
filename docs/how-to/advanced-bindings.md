# Advanced bindings (the Q form)

A `ScopeBinding`'s plain form is a lookup path — `queryset_lookup="team"`
filters `team__pk__in=<targets>`. That covers most cases. When a path can't
express the rule, a binding takes a **`q` callable** instead.

Use the Q form for:

- **A condition on the joined row itself** — "assigned to this team *as the
  active lead*", not merely "linked to this team".
- **An OR of two routes** — a row is in reach via either of two relations.

## Shape

```python
from django.db.models import Q
from ambit.policies import ScopeBinding

def by_active_assignment(target_ids):
    return Q(assignments__team_id__in=target_ids, assignments__is_active=True)

ScopeBinding(q=by_active_assignment, check=...)
```

- `q(target_ids)` returns the `Q` used to filter the queryset for reads.
- `check(...)` answers the create/change question the queryset can't (there's
  no row yet on create). It's given the submitted values, the existing object
  (or `None`), and the resolved targets.

## Fail-closed on writes

A `q` binding **with no `check`** fails closed on writes: nobody can create or
change a row through it. That's deliberate — a filter that only knows how to
*read* must not silently authorise *writing*. Supply `check` when the
dimension should permit writes.

## When to reach for it

Prefer the plain `queryset_lookup` — it's simpler and composes cleanly under
strict intersection. Reach for `q`/`check` only when the relationship carries a
condition (active/primary/current) or genuinely branches. If you find yourself
writing complex `q`s everywhere, that's usually a sign a relation wants a
cleaner model, not a cleverer binding.
