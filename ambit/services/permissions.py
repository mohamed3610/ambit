def has_permission(user, permission):
    """
    permission format:
        "authorization.view_role"
        "students.view_student"
        "grades.change_grade"
    """

    if not user or not user.is_authenticated:
        return False

    if not user.is_active:
        return False

    # Django superusers retain normal Django semantics.
    if user.is_superuser:
        return True

    try:
        app_label, codename = permission.split(".", 1)
    except ValueError:
        raise ValueError(
            "Permission must use the format 'app_label.codename'"
        )

    return user.role_assignments.filter(
        is_active=True,
        role__is_active=True,
        scope__is_active=True,
        role__permissions__content_type__app_label=app_label,
        role__permissions__codename=codename,
    ).exists()