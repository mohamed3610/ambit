# ambit

[![PyPI](https://img.shields.io/pypi/v/django-ambit.svg)](https://pypi.org/project/django-ambit/)
[![Django versions](https://img.shields.io/pypi/frameworkversions/django/django-ambit.svg)](https://pypi.org/project/django-ambit/)
[![License](https://img.shields.io/pypi/l/django-ambit.svg)](https://github.com/mohamed3610/ambit/blob/main/LICENSE)
[![Docs](https://img.shields.io/readthedocs/django-ambit.svg)](https://django-ambit.readthedocs.io/)
[![Django Packages](https://img.shields.io/badge/Django_Packages-ambit-0C4B33)](https://djangopackages.org/packages/p/ambit/)

**Scoped, multi-dimensional authorization for Django.**

Most authorization answers one question: *what* may this user do? `ambit`
answers the one that actually shapes real organisations: *what, and
**where***. A department head may edit staff — but only in their department.
A regional manager sees orders — but only in their region. A teacher marks
work — but only their own classes.

Django's built-in permissions are global: hold `orders.change_order` and you
can change every order. `ambit` adds the missing axis — **scope** — without
changing how you write permissions.

```python
has_authorized_scope(user, "orders.change_order", WITHIN_REGION)   # anywhere in reach?
authorized_queryset(user, "orders.view_order", Order.objects.all(), WITHIN_REGION)  # the rows they may see
can_access_object(user, "orders.change_order", order, WITHIN_REGION)  # this exact one?
```

## The idea: the engine is invariant, the dimensions are yours

A **dimension** is an axis access can be limited along. `ambit` ships *none* —
you register the ones your organisation actually has. A school registers
`stage / department / classroom / own-teaching`; a company registers
`region / department / team / own`. The scope math, the roles and grants, the
strict-intersection semantics — all identical. **The semantics change; the
functionality doesn't.**

That's the whole design: the same engine authorises a school and a sales org,
because it never knew what a "classroom" or a "region" *was* — only that it's
a dimension with values a grant may constrain.

## Install

```bash
pip install django-ambit
```

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

## Quickstart

**1. Register your dimensions** (once, e.g. in an `AppConfig.ready()`):

```python
from ambit.dimensions import register_dimension

# row-backed: a grant points at a Team row
register_dimension("team", "Team", model_label="sales.Team")

# self-resolving: no stored row — resolves to the user's own value at request time
register_dimension("own", "Own records", resolves_to=lambda user: user)
```

**2. Describe how a permission reaches your models** — a *policy* maps each
dimension to a lookup path on the object being checked:

```python
from ambit.policies import ScopePolicy, ScopeBinding

WITHIN_REACH = ScopePolicy({
    "team": ScopeBinding(queryset_lookup="team"),
    "own":  ScopeBinding(queryset_lookup="owner"),
})
```

**3. Grant access** — a *role* (a bundle of Django permissions) at a *scope*
(a point in the space your dimensions define):

```python
from ambit.models import Role, RoleAssignment
from ambit.services.scope_builder import scope_for

role = Role.objects.create(name="Rep")
role.permissions.add(view_order_permission)

# "Alice is a Rep in Team North"
RoleAssignment.objects.create(user=alice, role=role, scope=scope_for({"team": north}))
```

**4. Check** — anywhere in a view, queryset, or template helper:

```python
from ambit.services.authorization import (
    has_authorized_scope, authorized_queryset, can_access_object,
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

## Concepts

| Concept | What it is |
|---|---|
| **Dimension** | An axis access is limited along. *Row-backed* (points at a row, e.g. a Team) or *self-resolving* (resolves to the user's own value, e.g. "own records"). |
| **Scope** | A set of per-dimension constraints. **Strict intersection**: `{team: North, own}` means *in North **and** their own*. A scope with no constraints is global. |
| **Policy** | Which dimensions a permission is checked against, and the lookup path to each on the target model. |
| **Role** | A named bundle of Django permissions. |
| **Grant** (`RoleAssignment`) | A user holds a role at a scope. |
| **Catalog** | An optional, human-worded map of the permissions a console should offer (`register_catalog`). |

## Status

`ambit` is the authorization engine extracted from a production multi-tenant
Django system and generalised to any organisation. It's early (alpha) but the
core is battle-tested. The API may still shift before 1.0.

## License

MIT — see [LICENSE](LICENSE).
