# Protect class-based views

The mixins in `ambit.mixins` wire Django's generic views to the scoped
authorization layer, so you never write a check by hand. Each sets two
attributes: `permission` and `authorization_policy`.

```python
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from ambit.mixins import (
    ScopedQuerysetMixin, ScopedObjectMixin, ScopedCreateMixin, ScopedUpdateMixin,
)
from .models import Order
from .authz import WITHIN_REACH   # your ScopePolicy


class OrderListView(ScopedQuerysetMixin, ListView):
    model = Order
    permission = "sales.view_order"
    authorization_policy = WITHIN_REACH


class OrderDetailView(ScopedObjectMixin, DetailView):
    model = Order
    permission = "sales.view_order"
    authorization_policy = WITHIN_REACH


class OrderCreateView(ScopedCreateMixin, CreateView):
    model = Order
    fields = ["customer", "region"]
    permission = "sales.add_order"
    authorization_policy = WITHIN_REACH


class OrderUpdateView(ScopedUpdateMixin, UpdateView):
    model = Order
    fields = ["customer", "region"]
    permission = "sales.change_order"
    authorization_policy = WITHIN_REACH


class OrderDeleteView(ScopedObjectMixin, DeleteView):
    model = Order
    permission = "sales.delete_order"
    authorization_policy = WITHIN_REACH
```

What each mixin does:

| Mixin | Effect |
|---|---|
| `ScopedQuerysetMixin` | Narrows `get_queryset()` to the rows the user's grants reach. A list shows only what they may see. |
| `ScopedObjectMixin` | 404s an object outside the user's reach (detail / delete). Not "403" — it doesn't confirm the row exists. |
| `ScopedCreateMixin` | Refuses to create a row the user couldn't then reach — a scope can't mint rows beyond itself. |
| `ScopedUpdateMixin` | `ScopedObjectMixin` plus the create-side check on the submitted values. |

Add `LoginRequiredMixin` first in the bases so anonymous users are sent to
login rather than seeing an empty list.

## When the target dimension comes from the URL, not the form

On create, a value the scope reaches through may be fixed by the URL rather
than submitted (e.g. a nested resource). Provide it via
`get_authorization_values`:

```python
class LineItemCreateView(ScopedCreateMixin, CreateView):
    model = LineItem
    permission = "sales.add_lineitem"
    authorization_policy = WITHIN_REACH

    def get_authorization_values(self, form):
        return {"order": self.order}   # merged under cleaned_data
```
