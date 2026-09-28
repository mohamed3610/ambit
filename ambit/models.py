# accounts/authorization/models.py

from django.contrib.auth.models import Permission

from .base import UUIDModel, TimeStampedModel
from django.db import models


from django.conf import settings
from django.core.exceptions import ValidationError

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from .dimensions import (
    get_scope_dimension_definition,
    get_scope_dimension_model,
    is_self_resolved,
    scope_dimension_choices,
)

class Role(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=100)

    permissions = models.ManyToManyField(
        Permission,
        related_name="authorization_roles",
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    # A position is a role worth naming on the pages it applies to
    # ("Region Lead" on a region, "Team Lead" on a team). Leadership is
    # not a field on the target model -- it is a grant, read back where it
    # matters. An application decides which of its roles are titles.
    is_position = models.BooleanField(
        default=False,
        help_text="Show holders of this role as a position on the pages its "
                  "scope applies to.",
    )

    def __str__(self):
        return self.name


class Scope(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    is_global = models.BooleanField(
        default=False,
        help_text="Applies to all records regardless of scope constraints.",
    )

    def __str__(self):
        return self.name


class RoleAssignment(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    scope = models.ForeignKey(
        Scope,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "scope"],
                name="unique_user_role_scope",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.role} - {self.scope}"


class ScopeConstraint(UUIDModel, TimeStampedModel):
    scope = models.ForeignKey(
        Scope,
        on_delete=models.CASCADE,
        related_name="constraints",
    )

    dimension = models.CharField(
        max_length=50,
        choices=scope_dimension_choices,
    )

    # Both empty for a self-resolving dimension: the
    # target is whoever is signed in, not a row.
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    # A CharField, not a UUIDField: a target row may have any primary-key
    # type (UUID, int, ...). Django's GenericForeignKey stores the pk as
    # text and casts on lookup, so this reaches any model.
    object_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    target = GenericForeignKey(
        "content_type",
        "object_id",
    )

    def clean(self):
        super().clean()

        definition = get_scope_dimension_definition(
            self.dimension
        )

        if definition is None:
            raise ValidationError({
                "dimension":
                    f"Unknown scope dimension: {self.dimension}"
            })

        expected_model = get_scope_dimension_model(
            self.dimension
        )

        if is_self_resolved(self.dimension):
            if self.content_type_id or self.object_id:
                raise ValidationError({
                    "object_id":
                        f"'{definition.label}' resolves to the signed-in "
                        "person and takes no target."
                })
            return

        if not self.content_type_id or not self.object_id:
            raise ValidationError({
                "object_id":
                    f"Dimension '{self.dimension}' needs a "
                    f"{definition.label} to point at."
            })

        if self.content_type_id:
            actual_model = self.content_type.model_class()

            if actual_model is not expected_model:
                raise ValidationError({
                    "content_type":
                        f"Dimension '{self.dimension}' must target "
                        f"{definition.label}."
                })

        if (
            self.content_type_id
            and self.object_id
            and self.target is None
        ):
            raise ValidationError({
                "object_id":
                    "The scope constraint points to an object "
                    "that does not exist."
            })
    def __str__(self):
        if is_self_resolved(self.dimension):
            return f"{self.scope}: {get_scope_dimension_definition(self.dimension).label}"
        return f"{self.scope}: {self.dimension} = {self.target}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "scope",
                    "dimension",
                    "content_type",
                    "object_id",
                ],
                name="unique_scope_constraint",
                nulls_distinct=False,
            )
        ]