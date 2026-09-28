from dataclasses import dataclass
from enum import StrEnum

from django.apps import apps


class ScopeDimension(StrEnum):
    STAGE = "stage"
    DEPARTMENT = "department"
    # The narrowest unit today: "just her class". A classroom-only scope
    # reaches Classroom, CourseOffering, TeacherAssignment and Enrollment
    # and deliberately nothing grade- or department-level (curriculum,
    # subjects, the roster itself) -- see the intersection semantics in
    # services/scopes.py. Adding a dimension = one enum member, one
    # registry entry below, and a ScopeBinding on each policy that can
    # reach it; policies that can't express it need no change.
    CLASSROOM = "classroom"
    # "What I teach." The one dimension with no target row: it resolves
    # at request time to the signed-in person's own Teacher record, so a
    # school defines a Teacher role once, scoped to Own teaching, and
    # every teacher's grant follows her assignments -- reassign her and
    # her lessons, rosters and registers move with no change to access.
    # A login with no Teacher record reaches nothing through it.
    OWN = "own"


@dataclass(frozen=True)
class ScopeDimensionDefinition:
    label: str
    # None for a self-resolving dimension (OWN): no row to point at.
    model_label: str | None
    # How "Give access" offers it: "A stage", "One section". A sentence,
    # because the console reads as "<person> is a <role> in <where>".
    pick_label: str = ""
    # Ties the picked row into that sentence ("in Grade 1 · A").
    preposition: str = "in"


SCOPE_DIMENSIONS = {
    ScopeDimension.STAGE: ScopeDimensionDefinition(
        label="Stage",
        model_label="stage.Stage",
        pick_label="A stage",
    ),
    ScopeDimension.DEPARTMENT: ScopeDimensionDefinition(
        label="Department",
        model_label="department.Department",
        pick_label="A department",
    ),
    ScopeDimension.CLASSROOM: ScopeDimensionDefinition(
        label="Section",
        model_label="classroom.Classroom",
        pick_label="One section",
    ),
    ScopeDimension.OWN: ScopeDimensionDefinition(
        label="Own teaching",
        model_label=None,
        pick_label="Only what they teach themselves",
        preposition="for",
    ),
}


def get_scope_dimension(value):
    try:
        return ScopeDimension(value)
    except ValueError:
        return None


def get_scope_dimension_definition(value):
    dimension = get_scope_dimension(value)

    if dimension is None:
        return None

    return SCOPE_DIMENSIONS.get(dimension)


def get_scope_dimension_model(value):
    definition = get_scope_dimension_definition(value)

    if definition is None or definition.model_label is None:
        return None

    return apps.get_model(definition.model_label)


def is_self_resolved(value):
    """True for a dimension whose target is the signed-in person, not a row."""
    definition = get_scope_dimension_definition(value)
    return definition is not None and definition.model_label is None


def scope_dimension_choices():
    return [
        (dimension.value, definition.label)
        for dimension, definition in SCOPE_DIMENSIONS.items()
    ]
