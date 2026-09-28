# Concepts

`ambit` is a small set of pieces that compose. The engine is invariant; the
only thing that changes between one organisation and another is the set of
dimensions you register.

## Dimensions

A **dimension** is an axis access can be limited along. There are two kinds:

- **Row-backed** — a grant points at a row of a model (a `Team`, a
  `Department`). The scope stores which rows; the engine filters by them.
- **Self-resolving** — there is no stored row. It resolves at request time to
  the acting user's own value via a `resolves_to(user)` callable ("own
  records" → the user; "own teaching" → the user's `Teacher`). A user it
  resolves to `None` for reaches nothing through it.

```python
from ambit.dimensions import register_dimension

register_dimension("region", "Region", model_label="sales.Region")     # row-backed
register_dimension("own", "Own records", resolves_to=lambda u: u)      # self-resolving
```

`ambit` ships **no** dimensions — registering them is how you teach the engine
your organisation's shape.

## Scopes

A **scope** is a set of per-dimension constraints — a point in the space the
dimensions define. The defining rule is **strict intersection**:

> A scope of `{region: North, own}` authorises action where the object is in
> North **and** belongs to the user. Every named dimension must be satisfied;
> dimensions the scope doesn't mention impose no limit.

A scope with no constraints is **global** — it covers everything. Build scopes
with `scope_for`, which reuses an existing identical scope or creates one:

```python
from ambit.services.scope_builder import scope_for

scope_for({"region": north})               # in North
scope_for({"region": north, "own": True})  # in North, and their own
scope_for({})                              # everywhere
```

## Policies

A **policy** says which dimensions a given permission is checked against, and
how to reach each dimension's value on the object — a `ScopeBinding` per
dimension:

```python
from ambit.policies import ScopePolicy, ScopeBinding, GLOBAL_SCOPE_POLICY

WITHIN_REACH = ScopePolicy({
    "region": ScopeBinding(queryset_lookup="office__region"),
    "own":    ScopeBinding(queryset_lookup="owner"),
})
```

The plain form is a lookup path. For conditions a path can't express (a
condition on the joined row itself, or an OR of two routes) a binding takes a
`q` callable that returns a `Q`, and a `check` for the create/change case. A
policy naming no dimensions is `GLOBAL_SCOPE_POLICY`.

## Roles and grants

A **role** (`Role`) is a named bundle of Django permissions. A **grant**
(`RoleAssignment`) gives a user a role at a scope:

```python
from ambit.models import Role, RoleAssignment

role = Role.objects.create(name="Regional manager")
role.permissions.add(view_order, change_order)
RoleAssignment.objects.create(user=heba, role=role, scope=scope_for({"region": north}))
# "Heba is a Regional manager in North"
```

## Checking access

Three functions cover the cases you need:

| Function | Question it answers |
|---|---|
| `has_authorized_scope(user, permission, policy)` | Should this page/section/link exist for them at all? |
| `authorized_queryset(user, permission, queryset, policy)` | Which rows of this may they see? |
| `can_access_object(user, permission, obj, policy)` | May they act on this exact object? |

```python
from ambit.services.authorization import (
    has_authorized_scope, authorized_queryset, can_access_object,
)
```

Class-based views can use the mixins in `ambit.mixins`
(`ScopedQuerysetMixin`, `ScopedObjectMixin`, `ScopedCreateMixin`,
`ScopedUpdateMixin`) so the checks happen automatically from a `permission`
and an `authorization_policy` attribute.

## Catalog (optional)

A console building roles wants human words, not `orders.add_order`. The
**catalog** maps permissions to labels, grouped for display. `ambit` ships an
empty catalog; you register your own:

```python
from ambit.catalog import Entry, register_catalog, describe

register_catalog("Orders", [
    Entry("orders", "order", "Orders", "A customer order."),
    Entry("orders", "refund", "Refunds", actions=("view", "add")),
])

describe(some_permission)   # -> "Orders · Add"
```
