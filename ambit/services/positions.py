"""
Leadership, read back from the grants.

"Who is the class teacher of 2A?" is not a field on the section. It is
whoever holds a *position* role (Role.is_position) in a scope limited
to that section. This module answers that for one object or a page of
them, in a fixed number of queries.
"""

from collections import defaultdict
from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType

from ..models import RoleAssignment, ScopeConstraint
from .scope_builder import describe


@dataclass
class Position:
    role: object
    user: object
    scope: object

    @property
    def title(self):
        return self.role.name

    @property
    def where(self):
        """Extra qualification when the scope is narrower than the page: "Primary" on a department."""
        return describe(self.scope) if len(self.scope.constraints.all()) > 1 else ""


def positions_for(model, objects):
    """
    {object pk: [Position, ...]} for every position role held in a scope
    constrained to one of `objects`. Three queries whatever the page size.
    """
    pks = [o.pk for o in objects]
    if not pks:
        return {}
    content_type = ContentType.objects.get_for_model(model)
    scope_to_objects = defaultdict(set)
    for scope_id, object_id in ScopeConstraint.objects.filter(
        content_type=content_type, object_id__in=pks,
    ).values_list("scope_id", "object_id"):
        scope_to_objects[scope_id].add(object_id)

    grants = RoleAssignment.objects.filter(
        scope_id__in=scope_to_objects, is_active=True,
        role__is_active=True, role__is_position=True, scope__is_active=True,
        user__is_active=True,
    ).select_related("role", "user", "scope").prefetch_related("scope__constraints__target").order_by(
        "role__name", "user__last_name", "user__first_name",
    )

    result = defaultdict(list)
    for grant in grants:
        for object_id in scope_to_objects[grant.scope_id]:
            result[object_id].append(Position(role=grant.role, user=grant.user, scope=grant.scope))
    return dict(result)


def positions_of(user):
    """The titles this login holds, with where: [(Position)], for a person's own page."""
    grants = RoleAssignment.objects.filter(
        user=user, is_active=True, role__is_active=True, role__is_position=True, scope__is_active=True,
    ).select_related("role", "scope").prefetch_related("scope__constraints__target").order_by("role__name")
    return [Position(role=g.role, user=user, scope=g.scope) for g in grants]
