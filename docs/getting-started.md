# Getting started

## Install

```bash
pip install django-ambit
```

Add it to your Django project:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "ambit",
]
```

```bash
python manage.py migrate
```

## 1. Register your dimensions

`ambit` ships no dimensions — you declare the axes your organisation limits
access along. Do it once at startup, e.g. in an `AppConfig.ready()`:

```python
from ambit.dimensions import register_dimension

# row-backed: a grant points at a Team row
register_dimension("team", "Team", model_label="sales.Team")

# self-resolving: no stored row — resolves to the user's own value at request time
register_dimension("own", "Own records", resolves_to=lambda user: user)
```

A **row-backed** dimension is constrained to specific rows (a grant "in Team
North"). A **self-resolving** dimension has no stored row: it resolves, per
request, to the acting user's own value (their own records, their own
teaching). A user it resolves to `None` for reaches nothing through it.

## 2. Describe how a permission reaches your models

A **policy** maps each dimension to a lookup path on the object being checked:

```python
from ambit.policies import ScopePolicy, ScopeBinding

WITHIN_REACH = ScopePolicy({
    "team": ScopeBinding(queryset_lookup="team"),
    "own":  ScopeBinding(queryset_lookup="owner"),
})
```

A policy that names no dimensions is the global policy
(`ambit.policies.GLOBAL_SCOPE_POLICY`): holding the permission at all is enough.

## 3. Grant access

A **role** is a bundle of Django permissions; a **grant** gives a user that
role at a **scope**:

```python
from ambit.models import Role, RoleAssignment
from ambit.services.scope_builder import scope_for

role = Role.objects.create(name="Rep")
role.permissions.add(view_order_permission)

# "Alice is a Rep in Team North"
RoleAssignment.objects.create(user=alice, role=role, scope=scope_for({"team": north}))
```

`scope_for` finds an existing scope for exactly those targets or creates one,
so two people limited the same way share one scope. An empty mapping means
everywhere.

## 4. Check

```python
from ambit.services.authorization import (
    has_authorized_scope,   # "should this page/section exist for them at all?"
    authorized_queryset,    # "which rows may they see?"
    can_access_object,      # "may they act on this exact object?"
)

authorized_queryset(alice, "sales.view_order", Order.objects.all(), WITHIN_REACH)
# -> only orders in Team North
```

Or drop the mixins onto class-based views and never write a check by hand:

```python
from ambit.mixins import ScopedQuerysetMixin

class OrderListView(ScopedQuerysetMixin, ListView):
    model = Order
    permission = "sales.view_order"
    authorization_policy = WITHIN_REACH
```

Next: the **[Concepts](concepts.md)** page explains scopes, strict
intersection, and self-resolution in depth.
