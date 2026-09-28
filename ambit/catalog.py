"""
The permission catalogue, in a console's own words.

Django knows "orders.add_order"; an administrator building a role knows
"Orders -- Add". This maps one to the other, grouped the way a console is
grouped, so a role form can draw a matrix instead of a raw multi-select.

ambit ships an **empty** catalogue. The application registers its own
sections and entries (typically at startup), naming the permissions it
wants a console to offer. Permissions not registered are simply not
offered -- and a role that already carries one keeps it untouched.

    from ambit.catalog import Entry, register_catalog
    register_catalog("Orders", [
        Entry("orders", "order", "Orders", "A customer order."),
        Entry("orders", "refund", "Refunds", actions=("view", "add")),
    ])
"""

from dataclasses import dataclass

from django.contrib.auth.models import Permission

ACTIONS = ("view", "add", "change", "delete")
ACTION_LABELS = {"view": "See", "add": "Add", "change": "Change", "delete": "Remove"}


@dataclass(frozen=True)
class Entry:
    app_label: str
    model: str
    label: str
    hint: str = ""
    # Some things have no meaningful add/delete from the console.
    actions: tuple = ACTIONS
    # A custom permission shown in one of the four columns: {"change":
    # "approve_refund"} draws "Refunds -- Change" as its own row.
    codenames: tuple = ()

    @property
    def key(self):
        return f"{self.app_label}.{self.model}"

    def codename(self, action):
        return dict(self.codenames).get(action) or f"{action}_{self.model}"


# (section_label, [Entry, ...]) in display order. Populated by the app via
# register_catalog(); empty until then.
CATALOG = []


def register_catalog(section, entries):
    """Add a titled section of entries to the catalogue."""
    CATALOG.append((section, list(entries)))


def clear_catalog():
    """Empty the catalogue (tests, or a full re-registration)."""
    CATALOG.clear()


def entries():
    for _, group in CATALOG:
        yield from group


def catalog_permissions():
    """{(app_label, codename): Permission} for everything the catalogue offers."""
    wanted = {}
    for entry in entries():
        for action in entry.actions:
            wanted[(entry.app_label, entry.codename(action))] = None
    if not wanted:
        return {}
    found = Permission.objects.filter(
        content_type__app_label__in={a for a, _ in wanted},
    ).select_related("content_type")
    for permission in found:
        key = (permission.content_type.app_label, permission.codename)
        if key in wanted:
            wanted[key] = permission
    return {key: perm for key, perm in wanted.items() if perm is not None}


def describe(permission):
    """"Orders · Add" for a catalogued permission, else the raw codename."""
    for entry in entries():
        if entry.app_label == permission.content_type.app_label:
            for action in entry.actions:
                if permission.codename == entry.codename(action):
                    return f"{entry.label} · {ACTION_LABELS[action]}"
    return f"{permission.content_type.app_label}.{permission.codename}"
