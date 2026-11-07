from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.audit.services import record_event
from apps.institutions.access import has_active_role
from apps.institutions.models import Institution, InstitutionMembership


def _validated_password(password: str, *, email: str, full_name: str) -> str:
    candidate = User(email=email, full_name=full_name)
    try:
        validate_password(password, user=candidate)
    except DjangoValidationError as exc:
        raise ValidationError({"password": list(exc.messages)}) from exc
    return password


def _require_platform_admin(actor: User) -> None:
    if not (actor.is_active and actor.is_platform_admin):
        raise PermissionDenied("Platform administrator access is required.")


def _require_institution_admin(actor: User, institution: Institution) -> None:
    if not actor.is_active:
        raise PermissionDenied("Your account is inactive.")
    if actor.is_platform_admin:
        return
    if institution.status != Institution.Status.ACTIVE:
        raise PermissionDenied("This institution is suspended.")
    if not has_active_role(
        user=actor,
        institution=institution,
        roles={InstitutionMembership.Role.INSTITUTION_ADMIN},
    ):
        raise PermissionDenied("Institution administrator access is required.")


def create_institution_with_admin(
    *,
    actor: User,
    name: str,
    slug: str,
    timezone: str,
    settings: dict,
    admin_email: str,
    admin_full_name: str,
    admin_password: str,
    request=None,
) -> tuple[Institution, InstitutionMembership]:
    _require_platform_admin(actor)
    normalized_email = admin_email.strip().casefold()
    normalized_slug = slug.strip().lower()
    _validated_password(
        admin_password,
        email=normalized_email,
        full_name=admin_full_name,
    )

    try:
        with transaction.atomic():
            if Institution.objects.filter(slug__iexact=normalized_slug).exists():
                raise ValidationError({"slug": ["An institution with this slug already exists."]})
            if User.objects.filter(email__iexact=normalized_email).exists():
                raise ValidationError(
                    {"admin": {"email": ["A user with this email already exists."]}}
                )

            institution = Institution.objects.create(
                name=name,
                slug=normalized_slug,
                timezone=timezone,
                settings=settings,
                created_by=actor,
            )
            admin_user = User.objects.create_user(
                email=normalized_email,
                password=admin_password,
                full_name=admin_full_name,
            )
            membership = InstitutionMembership.objects.create(
                institution=institution,
                user=admin_user,
                role=InstitutionMembership.Role.INSTITUTION_ADMIN,
                created_by=actor,
            )
            record_event(
                action=AuditLog.Action.INSTITUTION_CREATED,
                actor=actor,
                institution=institution,
                target_type="institution",
                target_id=str(institution.pk),
                metadata={"slug": institution.slug, "admin_user_id": str(admin_user.pk)},
                request=request,
            )
            record_event(
                action=AuditLog.Action.MEMBERSHIP_CREATED,
                actor=actor,
                institution=institution,
                target_type="membership",
                target_id=str(membership.pk),
                metadata={
                    "user_id": str(admin_user.pk),
                    "role": membership.role,
                },
                request=request,
            )
            return institution, membership
    except IntegrityError as exc:
        raise ValidationError(
            {"detail": "The institution or administrator conflicts with an existing record."}
        ) from exc


def update_institution(
    *,
    actor: User,
    institution: Institution,
    changes: dict,
    request=None,
) -> Institution:
    with transaction.atomic():
        locked = Institution.objects.select_for_update().get(pk=institution.pk)
        _require_institution_admin(actor, locked)
        if "status" in changes and not actor.is_platform_admin:
            raise PermissionDenied("Only platform administrators can change institution status.")

        changed_fields = []
        for field, value in changes.items():
            if field not in {"name", "timezone", "settings", "status"}:
                continue
            if getattr(locked, field) != value:
                setattr(locked, field, value)
                changed_fields.append(field)
        if not changed_fields:
            return locked

        locked.save(update_fields=[*changed_fields, "updated_at"])
        record_event(
            action=AuditLog.Action.INSTITUTION_UPDATED,
            actor=actor,
            institution=locked,
            target_type="institution",
            target_id=str(locked.pk),
            metadata={"changed_fields": changed_fields},
            request=request,
        )
        return locked


def create_membership(
    *,
    actor: User,
    institution: Institution,
    email: str,
    full_name: str,
    role: str,
    password: str,
    request=None,
) -> InstitutionMembership:
    normalized_email = email.strip().casefold()
    if role not in InstitutionMembership.Role.values:
        raise ValidationError({"role": ["Unknown institution role."]})

    try:
        with transaction.atomic():
            locked = Institution.objects.select_for_update().get(pk=institution.pk)
            _require_institution_admin(actor, locked)
            if not actor.is_platform_admin and role == InstitutionMembership.Role.INSTITUTION_ADMIN:
                raise PermissionDenied(
                    "Only platform administrators can create institution administrators."
                )
            _validated_password(password, email=normalized_email, full_name=full_name)
            if User.objects.filter(email__iexact=normalized_email).exists():
                raise ValidationError({"email": ["A user with this email already exists."]})

            user = User.objects.create_user(
                email=normalized_email,
                password=password,
                full_name=full_name,
            )
            membership = InstitutionMembership.objects.create(
                institution=locked,
                user=user,
                role=role,
                created_by=actor,
            )
            record_event(
                action=AuditLog.Action.MEMBERSHIP_CREATED,
                actor=actor,
                institution=locked,
                target_type="membership",
                target_id=str(membership.pk),
                metadata={"user_id": str(user.pk), "role": role},
                request=request,
            )
            return membership
    except IntegrityError as exc:
        raise ValidationError(
            {"detail": "The membership conflicts with an existing record."}
        ) from exc


def update_membership(
    *,
    actor: User,
    institution: Institution,
    membership_id,
    changes: dict,
    request=None,
) -> InstitutionMembership:
    with transaction.atomic():
        locked_institution = Institution.objects.select_for_update().get(pk=institution.pk)
        _require_institution_admin(actor, locked_institution)
        membership = (
            InstitutionMembership.objects.select_for_update()
            .select_related("user")
            .filter(pk=membership_id, institution=locked_institution)
            .first()
        )
        if membership is None:
            raise ValidationError({"detail": "Membership not found in this institution."})

        if (
            not actor.is_platform_admin
            and membership.role == InstitutionMembership.Role.INSTITUTION_ADMIN
        ):
            raise PermissionDenied(
                "Only platform administrators can modify institution administrators."
            )

        new_role = changes.get("role", membership.role)
        new_active = changes.get("is_active", membership.is_active)
        if new_role not in InstitutionMembership.Role.values:
            raise ValidationError({"role": ["Unknown institution role."]})
        if not actor.is_platform_admin and new_role == InstitutionMembership.Role.INSTITUTION_ADMIN:
            raise PermissionDenied(
                "Only platform administrators can assign institution administrator roles."
            )

        losing_admin = (
            membership.role == InstitutionMembership.Role.INSTITUTION_ADMIN
            and membership.is_active
            and (new_role != InstitutionMembership.Role.INSTITUTION_ADMIN or new_active is False)
        )
        if losing_admin:
            other_admin_exists = (
                InstitutionMembership.objects.filter(
                    institution=locked_institution,
                    role=InstitutionMembership.Role.INSTITUTION_ADMIN,
                    is_active=True,
                )
                .exclude(pk=membership.pk)
                .exists()
            )
            if not other_admin_exists:
                raise ValidationError(
                    {"detail": "The institution must retain at least one active administrator."}
                )

        role_changed = new_role != membership.role
        active_changed = new_active != membership.is_active
        if not role_changed and not active_changed:
            return membership

        old_role = membership.role
        old_active = membership.is_active
        membership.role = new_role
        membership.is_active = new_active
        membership.save(update_fields=["role", "is_active", "updated_at"])

        metadata = {
            "user_id": str(membership.user_id),
            "old_role": old_role,
            "new_role": new_role,
            "old_is_active": old_active,
            "new_is_active": new_active,
        }
        if role_changed:
            record_event(
                action=AuditLog.Action.MEMBERSHIP_ROLE_CHANGED,
                actor=actor,
                institution=locked_institution,
                target_type="membership",
                target_id=str(membership.pk),
                metadata=metadata,
                request=request,
            )
        if active_changed:
            record_event(
                action=(
                    AuditLog.Action.MEMBERSHIP_REACTIVATED
                    if new_active
                    else AuditLog.Action.MEMBERSHIP_DEACTIVATED
                ),
                actor=actor,
                institution=locked_institution,
                target_type="membership",
                target_id=str(membership.pk),
                metadata=metadata,
                request=request,
            )

        membership.institution = locked_institution
        return membership
