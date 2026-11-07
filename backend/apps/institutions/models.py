import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower


class Institution(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    timezone = models.CharField(max_length=64, default="UTC")
    settings = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_institutions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(Lower("slug"), name="institutions_slug_ci_unique"),
        ]
        indexes = [models.Index(fields=["status"], name="institutions_status_idx")]

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.slug = self.slug.strip().lower()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValidationError({"timezone": "Unknown IANA timezone."}) from exc

    def __str__(self) -> str:
        return self.name


class InstitutionMembership(models.Model):
    class Role(models.TextChoices):
        INSTITUTION_ADMIN = "institution_admin", "Institution administrator"
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        Institution,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="institution_memberships",
    )
    role = models.CharField(max_length=32, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "institution"],
                name="institutions_membership_user_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["institution", "is_active"],
                name="membership_inst_active_idx",
            ),
            models.Index(fields=["institution", "role"], name="membership_inst_role_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.institution.name} ({self.role})"
