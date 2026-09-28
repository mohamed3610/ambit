# ambit

**Scoped, multi-dimensional authorization for Django.**

Most authorization answers one question: *what* may this user do? `ambit`
answers the one that actually shapes real organisations: **what, and *where***.

A department head may edit staff — but only in their department. A regional
manager sees orders — but only in their region. A teacher marks work — but
only their own classes.

Django's built-in permissions are global: hold `orders.change_order` and you
can change *every* order. `ambit` adds the missing axis — **scope** — without
changing how you write permissions.

```python
has_authorized_scope(user, "orders.change_order", WITHIN_REGION)      # anywhere in reach?
authorized_queryset(user, "orders.view_order", Order.objects.all(), WITHIN_REGION)  # the rows they may see
can_access_object(user, "orders.change_order", order, WITHIN_REGION)  # this exact one?
```

## The idea: the engine is invariant, the dimensions are yours

A **dimension** is an axis access can be limited along. `ambit` ships *none* —
you register the ones your organisation actually has. A school registers
`stage / department / classroom / own-teaching`; a company registers
`region / department / team / own`. The scope math, the roles and grants, the
strict-intersection semantics — all identical.

> **The semantics change; the functionality doesn't.**

That's the whole design: the same engine authorises a school and a sales org,
because it never knew what a "classroom" or a "region" *was* — only that it's
a dimension with values a grant may constrain.

## Where to go next

- **[Getting started](getting-started.md)** — install, register dimensions, and run your first scoped check.
- **[Concepts](concepts.md)** — dimensions, scopes, policies, roles and grants, in depth.

## Status

`ambit` is the authorization engine extracted from a production multi-tenant
Django system and generalised to any organisation. It's early (alpha) but the
core is battle-tested. The API may still shift before 1.0.

Licensed under the MIT License.
