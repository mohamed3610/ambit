# Build a permission console

Django stores permissions as `orders.add_order`. An administrator building a
role thinks "Orders — Add". The **catalog** maps one to the other, grouped for
display, so a role form can draw a tidy matrix instead of a 200-row
multi-select.

`ambit` ships an **empty** catalog — you register the permissions your console
should offer. Anything not registered is simply not offered (and a role that
already carries it keeps it).

## Register your catalog

Once at startup (e.g. `AppConfig.ready()`):

```python
from ambit.catalog import Entry, register_catalog

register_catalog("Sales", [
    Entry("sales", "order",  "Orders", "A customer order."),
    Entry("sales", "refund", "Refunds", actions=("view", "add")),
])
register_catalog("Access", [
    Entry("ambit", "role", "Roles"),
    Entry("ambit", "roleassignment", "Give access", "A login gets a role somewhere."),
])
```

Each `Entry`:

| Field | Meaning |
|---|---|
| `app_label`, `model` | Which Django model's permissions |
| `label`, `hint` | The words a human reads |
| `actions` | Which of `view/add/change/delete` to offer (default: all four) |
| `codenames` | Map an action to a custom permission, e.g. `codenames=(("change", "approve_refund"),)` |

## Render the matrix

`catalog_permissions()` returns the actual `Permission` objects the catalog
offers, keyed by `(app_label, codename)` — feed it to your role form:

```python
from ambit.catalog import catalog_permissions, ACTIONS, ACTION_LABELS

perms = catalog_permissions()   # {(app_label, codename): Permission}
```

Group by `Entry` and lay out a column per action (`ACTION_LABELS` gives the
"See / Add / Change / Remove" headers).

## Describe a single permission

`describe(permission)` gives the human label for any permission — for an audit
log, a "you granted…" message, or a review screen:

```python
from ambit.catalog import describe

describe(order_change_permission)   # "Orders · Change"
describe(uncatalogued_permission)   # falls back to "app.codename"
```
