"""
The engine, exercised on a deliberately non-school domain (teams + own
records) -- the proof that ambit carries no school semantics: the same
engine authorises anything you register dimensions for.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from ambit.catalog import Entry, clear_catalog, describe, register_catalog
from ambit.dimensions import clear_dimensions, register_dimension
from ambit.models import Role, RoleAssignment
from ambit.policies import ScopeBinding, ScopePolicy
from ambit.services.authorization import (
    authorized_queryset,
    can_access_object,
    has_authorized_scope,
)
from ambit.services.scope_builder import scope_for
from tests.orgtest.models import Team, Widget

User = get_user_model()
PERM = "orgtest.view_widget"


class EngineTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        clear_dimensions()
        register_dimension("team", "Team", model_label="orgtest.Team")
        register_dimension("own", "Own records", resolves_to=lambda user: user)
        cls.policy = ScopePolicy({
            "team": ScopeBinding(queryset_lookup="team"),
            "own": ScopeBinding(queryset_lookup="owner"),
        })

    def setUp(self):
        self.alice = User.objects.create(username="alice")
        self.bob = User.objects.create(username="bob")
        self.carol = User.objects.create(username="carol")
        self.north = Team.objects.create(name="North")
        self.south = Team.objects.create(name="South")
        self.wN = Widget.objects.create(name="wN", team=self.north)
        self.wS = Widget.objects.create(name="wS", team=self.south)
        self.wB = Widget.objects.create(name="wB", team=self.north, owner=self.bob)
        self.wBs = Widget.objects.create(name="wBs", team=self.south, owner=self.bob)
        self.role = Role.objects.create(name="Viewer")
        self.role.permissions.add(
            Permission.objects.get(codename="view_widget", content_type__app_label="orgtest"))

    def grant(self, user, targets):
        RoleAssignment.objects.create(user=user, role=self.role, scope=scope_for(targets))

    def seen(self, user):
        return set(authorized_queryset(user, PERM, Widget.objects.all(), self.policy)
                   .values_list("name", flat=True))

    # --- row-backed dimension ---------------------------------------------
    def test_row_backed_scope_limits_to_that_value(self):
        self.grant(self.alice, {"team": self.north})
        self.assertEqual(self.seen(self.alice), {"wN", "wB"})   # everything in North

    def test_out_of_scope_object_is_refused(self):
        self.grant(self.alice, {"team": self.north})
        self.assertTrue(can_access_object(self.alice, PERM, self.wN, self.policy))
        self.assertFalse(can_access_object(self.alice, PERM, self.wS, self.policy))

    # --- self-resolving dimension -----------------------------------------
    def test_self_resolving_scope_follows_the_user(self):
        self.grant(self.bob, {"own": True})
        self.assertEqual(self.seen(self.bob), {"wB", "wBs"})    # his, across both teams

    def test_self_resolving_reaches_nothing_without_an_own_target(self):
        self.grant(self.alice, {"own": True})                  # Alice owns nothing
        self.assertEqual(self.seen(self.alice), set())

    # --- strict intersection ----------------------------------------------
    def test_intersection_requires_every_named_dimension(self):
        self.grant(self.bob, {"team": self.north, "own": True})  # in North AND his own
        self.assertEqual(self.seen(self.bob), {"wB"})

    # --- global & no grant ------------------------------------------------
    def test_global_scope_sees_everything(self):
        self.grant(self.alice, {})                              # empty -> global
        self.assertEqual(self.seen(self.alice), {"wN", "wS", "wB", "wBs"})

    def test_no_grant_sees_nothing(self):
        self.assertEqual(self.seen(self.carol), set())
        self.assertFalse(has_authorized_scope(self.carol, PERM, self.policy))

    def test_has_authorized_scope_true_when_reachable(self):
        self.grant(self.alice, {"team": self.north})
        self.assertTrue(has_authorized_scope(self.alice, PERM, self.policy))

    # --- scope reuse ------------------------------------------------------
    def test_scope_for_is_idempotent(self):
        self.assertEqual(scope_for({"team": self.north}).pk,
                         scope_for({"team": self.north}).pk)


class CatalogTests(TestCase):
    def setUp(self):
        clear_catalog()
        register_catalog("Widgets", [Entry("orgtest", "widget", "Widgets", "A widget.")])
        self.perm = Permission.objects.get(codename="view_widget", content_type__app_label="orgtest")

    def test_describe_uses_human_words(self):
        self.assertEqual(describe(self.perm), "Widgets · See")

    def test_uncatalogued_permission_falls_back_to_codename(self):
        clear_catalog()
        self.assertEqual(describe(self.perm), "orgtest.view_widget")
