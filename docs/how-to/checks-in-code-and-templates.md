# Check access in code and templates

Outside class-based views — in a function view, a service, a serializer, or a
template — use the three functions directly.

```python
from ambit.services.authorization import (
    has_authorized_scope,   # "should this exist for them at all?"
    authorized_queryset,    # "which rows may they see?"
    can_access_object,      # "may they act on this exact object?"
    has_any_scope,          # "do they hold this permission anywhere, any scope?"
)
```

## In a function view

```python
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if not can_access_object(request.user, "sales.view_order", order, WITHIN_REACH):
        raise Http404          # don't reveal it exists
    ...
```

## Filtering a queryset

```python
orders = authorized_queryset(request.user, "sales.view_order",
                             Order.objects.all(), WITHIN_REACH)
```

## Deciding whether to draw a link or section

`has_authorized_scope` is the cheap "could they reach *any* of this?" question —
use it to decide whether a nav item, dashboard tile, or "Add" button should
exist. A control that 403s is worse than no control.

```python
context["can_manage_orders"] = has_authorized_scope(
    request.user, "sales.change_order", WITHIN_REACH,
)
```

`has_any_scope(user, permission)` is even coarser — it ignores the policy and
asks only whether the user holds the permission under *any* grant. Good for a
top-level "is this feature relevant to them at all" check.

## In templates

`ambit` ships no template tags — compute the booleans in the view and pass
them in context (above), which keeps templates fast and dumb:

```django
{% if can_manage_orders %}
  <a href="{% url 'order-add' %}">New order</a>
{% endif %}
```

If you'd rather call it inline, a two-line custom tag wraps it:

```python
# yourapp/templatetags/authz.py
from django import template
from ambit.services.authorization import has_authorized_scope
from yourapp.authz import WITHIN_REACH

register = template.Library()

@register.simple_tag(takes_context=True)
def can(context, permission):
    return has_authorized_scope(context["request"].user, permission, WITHIN_REACH)
```

```django
{% load authz %}
{% can "sales.change_order" as may_manage %}
{% if may_manage %} ... {% endif %}
```

## Superusers

A Django superuser passes every check — `authorized_queryset` returns the full
queryset, `has_authorized_scope` and `has_any_scope` return `True`. Scope
applies to everyone else.
