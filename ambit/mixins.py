"""
Class-based view mixins wiring Django views to the scoped authorization
layer in accounts/authorization/services/.

Usage:

    class GradeListView(ScopedQuerysetMixin, ListView):
        model = Grade
        permission = "grade.view_grade"
        authorization_policy = GRADE_SCOPE_POLICY

    class GradeDetailView(ScopedObjectMixin, DetailView):
        model = Grade
        permission = "grade.view_grade"
        authorization_policy = GRADE_SCOPE_POLICY

    class GradeCreateView(ScopedCreateMixin, CreateView):
        model = Grade
        fields = ["name", "stage", "order"]
        permission = "grade.add_grade"
        authorization_policy = GRADE_SCOPE_POLICY

    class GradeUpdateView(ScopedUpdateMixin, UpdateView):
        model = Grade
        fields = ["name", "stage", "order"]
        permission = "grade.change_grade"
        authorization_policy = GRADE_SCOPE_POLICY

    class GradeDeleteView(ScopedObjectMixin, DeleteView):
        model = Grade
        permission = "grade.delete_grade"
        authorization_policy = GRADE_SCOPE_POLICY

`permission` and `authorization_policy` are deliberately plain class
attributes. If either needs to vary per request, override
get_permission() or get_authorization_policy().
"""

"""
CAREFUL: Scoped mixins must appear before the Django generic view class
in the inheritance list so their get_queryset/get_object/form_valid
overrides participate in the MRO.
"""

from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from .services.authorization import (
    authorized_queryset,
    can_create,
    can_update,
    has_authorized_scope,
)


class ScopedPermissionMixin:
    permission = None
    authorization_policy = None

    def get_permission(self):
        if not self.permission:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must set "
                "`permission`."
            )

        return self.permission

    def get_authorization_policy(self):
        if self.authorization_policy is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must set "
                "`authorization_policy`."
            )

        return self.authorization_policy

    def get_authorization_values(self, form):
        """
        Extra values a scope check needs beyond form.cleaned_data --
        for a field the scope's policy reaches through (e.g.
        "classroom__grade__stage") that isn't itself a form field
        because it's fixed by the URL instead of chosen by the user
        (see ClassroomCreateView setting `classroom` from a URL kwarg,
        not a submitted value). Without this, can_create() has nothing
        to resolve that lookup's root from on a brand-new object,
        since there's no existing instance to fall back to the way
        can_update() falls back to self.object.

        Override and return e.g. {"classroom": self.classroom}.
        Merged *underneath* cleaned_data, so a real form field always
        wins if the two ever overlap.
        """
        return {}

    def dispatch(self, request, *args, **kwargs):
        if not has_authorized_scope(
            request.user,
            self.get_permission(),
            self.get_authorization_policy(),
        ):
            raise PermissionDenied(
                "You don't have permission to access this page."
            )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )


class ScopedQuerysetMixin(ScopedPermissionMixin):
    """
    For ListView-style views: the listing only ever contains what the
    user's role assignments actually cover.
    """

    def get_queryset(self):
        return authorized_queryset(
            self.request.user,
            self.get_permission(),
            super().get_queryset(),
            self.get_authorization_policy(),
        )


class ScopedObjectMixin(ScopedPermissionMixin):
    """
    For DetailView/UpdateView/DeleteView: an object outside the user's
    scope 404s exactly like one that doesn't exist.
    """

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        scoped = authorized_queryset(
            self.request.user,
            self.get_permission(),
            queryset,
            self.get_authorization_policy(),
        )

        pk_kwarg = getattr(
            self,
            "pk_url_kwarg",
            "pk",
        )

        return get_object_or_404(
            scoped,
            pk=self.kwargs[pk_kwarg],
        )


class ScopedCreateMixin(ScopedPermissionMixin):
    """
    For CreateView: rejects a submission whose values fall outside the
    user's scope before anything is saved.
    """

    def form_valid(self, form):
        values = {
            **self.get_authorization_values(form),
            **form.cleaned_data,
        }

        if not can_create(
            self.request.user,
            self.get_permission(),
            values,
            self.get_authorization_policy(),
        ):
            raise PermissionDenied(
                "You don't have access to create a record "
                "with these values."
            )

        # Backstop, not the primary defense: a field fixed by the URL
        # (not in the form) is invisible to the form's own
        # validate_unique(), so a constraint involving it can only be
        # caught here, at the database, instead of as a normal field
        # error. Forms with that shape should still validate it
        # themselves in clean() for a message pointing at the right
        # field -- this only guarantees a raw IntegrityError can never
        # reach the user, even if that check is missing or a race
        # slips past it.
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            form.add_error(
                None,
                "This couldn't be saved because it conflicts with an "
                "existing record. Check the values and try again.",
            )
            return self.form_invalid(form)


class ScopedUpdateMixin(ScopedObjectMixin):
    """
    For UpdateView: the existing object must be in scope, and submitted
    values must remain within scope.
    """

    def form_valid(self, form):
        if not can_update(
            self.request.user,
            self.get_permission(),
            self.object,
            form.cleaned_data,
            self.get_authorization_policy(),
        ):
            raise PermissionDenied(
                "You don't have access to update this record "
                "with these values."
            )

        # See the matching comment in ScopedCreateMixin.form_valid --
        # this is a backstop for constraints involving a field that
        # isn't in the form, not the primary defense.
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            form.add_error(
                None,
                "This couldn't be saved because it conflicts with an "
                "existing record. Check the values and try again.",
            )
            return self.form_invalid(form)
