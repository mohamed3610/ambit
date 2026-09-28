"""
Base model classes ambit's own models build on. Vendored so the package is
self-contained -- your application can keep its own equivalents; these are
only used by ambit's Role / Scope / RoleAssignment / ScopeConstraint tables.
"""
import uuid

from django.db import models


def new_id():
    """
    A primary key: UUIDv7 (time-ordered, so indexes stay tidy) where the
    runtime has it (Python 3.14+), UUIDv4 elsewhere. A named function rather
    than `uuid.uuid7` itself so migrations import on any Python.
    """
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=new_id, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
