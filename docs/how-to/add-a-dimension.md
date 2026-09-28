# Add a new dimension

Adding an axis of authority is three small steps: register the dimension, add
a binding to each policy that should reach it, and (for a self-resolving one)
supply the resolver. Nothing else in the engine changes.

## 1. Register it

Do this once at startup — an `AppConfig.ready()` is the natural home, so it
runs before any request.

```python
# yourapp/apps.py
from django.apps import AppConfig

class YourAppConfig(AppConfig):
    name = "yourapp"

    def ready(self):
        from ambit.dimensions import register_dimension

        # row-backed: constrained to specific rows
        register_dimension("region", "Region", model_label="sales.Region")

        # self-resolving: resolves to the user's own value per request
        register_dimension("own", "Own records", resolves_to=lambda user: user)
```

`pick_label` and `preposition` are optional and only affect how a console
phrases the dimension ("A region", "in").

## 2. Bind it on the policies that use it

A policy only constrains the dimensions it names. Add a `ScopeBinding` giving
the lookup path to that dimension's value on the model:

```python
from ambit.policies import ScopePolicy, ScopeBinding

WITHIN_REACH = ScopePolicy({
    "region": ScopeBinding(queryset_lookup="office__region"),
    "own":    ScopeBinding(queryset_lookup="owner"),
})
```

A policy that *can't* express a dimension simply omits it — no change needed.
Grants scoped to a dimension a policy doesn't support reach nothing under that
policy (fail closed).

## 3. That's it

Grants can now target the new dimension:

```python
scope_for({"region": north})
scope_for({"region": north, "own": True})   # strict intersection
```

Every check — `authorized_queryset`, `can_access_object`,
`has_authorized_scope` — picks it up automatically, because the engine reads
the registry, not a hard-coded list.

## Row-backed vs self-resolving

| | Row-backed | Self-resolving |
|---|---|---|
| Declared with | `model_label="app.Model"` | `resolves_to=lambda user: ...` |
| A grant stores | the chosen row(s) | nothing — resolved per request |
| Example | "in Region North" | "their own records" |
| No target for a user | n/a | reaches nothing (fails closed) |

A self-resolving resolver is called once per user per request (memoized), so
it's fine to hit the database in it.
