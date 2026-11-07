from rest_framework.permissions import BasePermission

from apps.institutions.access import resolve_institution_access
from apps.institutions.models import InstitutionMembership


class InstitutionAccessPermission(BasePermission):
    """Verify tenant membership from the URL's institution UUID."""

    message = "You do not have access to this institution."
    allowed_roles: frozenset[str] | None = None

    def has_permission(self, request, view) -> bool:
        institution_id = view.kwargs.get("institution_id")
        access = resolve_institution_access(
            user=request.user,
            institution_id=institution_id,
            allowed_roles=self.allowed_roles,
        )
        if access is None:
            return False
        view.institution_access = access
        view.institution = access.institution
        view.membership = access.membership
        return True


class IsInstitutionMember(InstitutionAccessPermission):
    pass


class IsInstitutionAdmin(InstitutionAccessPermission):
    allowed_roles = frozenset({InstitutionMembership.Role.INSTITUTION_ADMIN})


class IsInstitutionStaff(InstitutionAccessPermission):
    allowed_roles = frozenset(
        {InstitutionMembership.Role.INSTITUTION_ADMIN, InstitutionMembership.Role.TEACHER}
    )
