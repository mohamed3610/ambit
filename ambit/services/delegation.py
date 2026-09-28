"""
What may this administrator hand to others?

The rule: nobody delegates power they do not hold. An administrator
editing a role may only tick permissions she herself has (through any
active grant), and may only give out roles made entirely of such
permissions. Without this, "may change a role's name" is one edit away
from "may do everything", and "may give access" is one self-grant away
from the same.

Platform superusers are outside the rule -- they bootstrap the school.
"""

from django.contrib.auth.models import Permission

from ..models import Role


def delegable_permission_pks(user):
    """Only globally held permissions may be delegated to arbitrary coverage.

    A permission name alone is not authority to expand its scope. Until
    structural scope containment is implemented, this conservative ceiling
    applies both to grants and edits of roles already assigned elsewhere.
    """
    if user.is_superuser:
        return None
    return set(
        Permission.objects.filter(
            authorization_roles__is_active=True,
            authorization_roles__assignments__user=user,
            authorization_roles__assignments__is_active=True,
            authorization_roles__assignments__scope__is_active=True,
            authorization_roles__assignments__scope__is_global=True,
        ).values_list("pk", flat=True)
    )


def delegable_roles(user):
    """Active roles made only of permissions this user holds -- the ones she may grant."""
    delegable = delegable_permission_pks(user)
    roles = Role.objects.filter(is_active=True)
    if delegable is None:
        return roles
    beyond_reach = Permission.objects.exclude(pk__in=delegable)
    return roles.exclude(permissions__in=beyond_reach).distinct()


def may_manage_login(editor, account):
    """Recovery and identity changes cannot be used to acquire greater power."""
    if not editor.is_active:
        return False
    if editor.is_superuser:
        return True
    if account.is_superuser or account.is_staff:
        return False
    ceiling = delegable_permission_pks(editor)
    held = set(Permission.objects.filter(
        authorization_roles__is_active=True,
        authorization_roles__assignments__user=account,
        authorization_roles__assignments__is_active=True,
        authorization_roles__assignments__scope__is_active=True,
    ).values_list('pk', flat=True))
    held.update(account.user_permissions.values_list('pk', flat=True))
    held.update(Permission.objects.filter(group__user=account).values_list('pk', flat=True))
    return held <= ceiling
