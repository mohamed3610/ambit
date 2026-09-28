# Test your authorization

Authorization is exactly the kind of logic you want under test — a wrong scope
is a data leak. The pattern: register dimensions, grant a scope, assert what a
user can and can't reach.

## The shape of a test

```python
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from ambit.dimensions import clear_dimensions, register_dimension
from ambit.models import Role, RoleAssignment
from ambit.policies import ScopeBinding, ScopePolicy
from ambit.services.authorization import authorized_queryset, can_access_object
from ambit.services.scope_builder import scope_for
from sales.models import Region, Order

User = get_user_model()


class OrderScopeTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        clear_dimensions()
        register_dimension("region", "Region", model_label="sales.Region")
        register_dimension("own", "Own records", resolves_to=lambda u: u)
        cls.policy = ScopePolicy({
            "region": ScopeBinding(queryset_lookup="region"),
            "own":    ScopeBinding(queryset_lookup="owner"),
        })

    def setUp(self):
        self.alice = User.objects.create(username="alice")
        self.north = Region.objects.create(name="North")
        self.south = Region.objects.create(name="South")
        self.n1 = Order.objects.create(region=self.north)
        self.s1 = Order.objects.create(region=self.south)
        self.role = Role.objects.create(name="Rep")
        self.role.permissions.add(
            Permission.objects.get(codename="view_order", content_type__app_label="sales"))

    def seen(self, user):
        return set(authorized_queryset(user, "sales.view_order",
                                       Order.objects.all(), self.policy))

    def test_scoped_to_north_sees_only_north(self):
        RoleAssignment.objects.create(
            user=self.alice, role=self.role, scope=scope_for({"region": self.north}))
        self.assertEqual(self.seen(self.alice), {self.n1})
        self.assertFalse(
            can_access_object(self.alice, "sales.view_order", self.s1, self.policy))

    def test_no_grant_sees_nothing(self):
        self.assertEqual(self.seen(self.alice), set())
```

## The cases worth covering for every scoped model

- **In scope**: a user granted a scope sees exactly the rows in it.
- **Out of scope**: `can_access_object` is `False` for a row outside it; a
  detail view 404s.
- **Strict intersection**: a two-dimension grant reaches only the overlap.
- **Self-resolving**: an "own" grant follows the user, and reaches *nothing*
  for a user with no own target.
- **No grant**: sees nothing; `has_authorized_scope` is `False`.
- **Global**: an empty scope sees everything.

## Isolation tip

Dimensions live in a process-wide registry. Register them in `setUpClass`
(after `clear_dimensions()`), or in a fixture your tests share, so registration
from one test class doesn't leak surprising state into another.

## Running the engine's own suite

`ambit`'s tests run without a project:

```bash
python runtests.py
```
