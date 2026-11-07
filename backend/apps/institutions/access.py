from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import ValidationError

from apps.institutions.models import Institution, InstitutionMembership


@dataclass(frozen=True)
class InstitutionAccess:
    institution: Institution
    membership: InstitutionMembership | None
    is_platform_admin: bool


def resolve_institution_access(
    *,
    user,
    institution_id: UUID | str,
    allowed_roles: frozenset[str] | None = None,
) -> InstitutionAccess | None:
    """Resolve access from server-side membership, never from client-supplied roles."""

    if not user or not user.is_authenticated or not user.is_active:
        return None

    try:
        institution = Institution.objects.filter(pk=institution_id).first()
    except TypeError, ValueError, ValidationError:
        return None
    if institution is None:
        return None

    if user.is_platform_admin:
        return InstitutionAccess(institution=institution, membership=None, is_platform_admin=True)

    membership = (
        InstitutionMembership.objects.filter(
            institution=institution,
            user=user,
            is_active=True,
        )
        .select_related("user")
        .first()
    )
    if membership is None:
        return None
    if institution.status != Institution.Status.ACTIVE:
        return None
    if allowed_roles is not None and membership.role not in allowed_roles:
        return None
    return InstitutionAccess(
        institution=institution,
        membership=membership,
        is_platform_admin=False,
    )


def has_active_role(*, user, institution: Institution, roles: set[str] | frozenset[str]) -> bool:
    if user.is_platform_admin and user.is_active:
        return True
    return InstitutionMembership.objects.filter(
        user=user,
        institution=institution,
        role__in=roles,
        is_active=True,
    ).exists()
