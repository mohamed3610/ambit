# Grant and revoke access

Access is a **grant**: a user holds a **role** at a **scope**.

## Create a role

A role is a named bundle of Django permissions.

```python
from django.contrib.auth.models import Permission
from ambit.models import Role

manager = Role.objects.create(name="Regional manager")
manager.permissions.add(
    Permission.objects.get(codename="view_order", content_type__app_label="sales"),
    Permission.objects.get(codename="change_order", content_type__app_label="sales"),
)
```

## Build a scope

Use `scope_for` — it finds the existing scope for exactly those targets or
creates one, so everyone limited the same way shares a single scope (and it
reads as one thing in a "who has access where" list).

```python
from ambit.services.scope_builder import scope_for

scope_for({"region": north})               # in North
scope_for({"region": north, "own": True})  # in North, and only their own
scope_for({})                              # everywhere (global)
```

Keys are your registered dimension names. A row-backed dimension takes the
row; a self-resolving one takes `True` to include it.

## Give the grant

```python
from ambit.models import RoleAssignment

RoleAssignment.objects.create(user=heba, role=manager, scope=scope_for({"region": north}))
# "Heba is a Regional manager in North"
```

## Revoke

Deactivate the grant (keeps the history) or delete it:

```python
RoleAssignment.objects.filter(user=heba, role=manager).update(is_active=False)
# or, to remove entirely:
RoleAssignment.objects.filter(user=heba, role=manager).delete()
```

An inactive grant reaches nothing; the user's other grants are unaffected.

## Read a grant back in words

`scope_builder` turns a scope into human phrasing for a console:

```python
from ambit.services.scope_builder import describe, where_phrase

describe(scope)       # "North × Sales"
where_phrase(scope)   # "in North × Sales"  /  "everywhere"  /  "for own records"
```
