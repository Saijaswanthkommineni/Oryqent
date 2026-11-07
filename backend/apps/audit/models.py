import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        INSTITUTION_CREATED = "institution.created", "Institution created"
        INSTITUTION_UPDATED = "institution.updated", "Institution updated"
        MEMBERSHIP_CREATED = "membership.created", "Membership created"
        MEMBERSHIP_ROLE_CHANGED = "membership.role_changed", "Membership role changed"
        MEMBERSHIP_DEACTIVATED = "membership.deactivated", "Membership deactivated"
        MEMBERSHIP_REACTIVATED = "membership.reactivated", "Membership reactivated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        "institutions.Institution",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    action = models.CharField(max_length=64, choices=Action.choices)
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=["institution", "-created_at"],
                name="audit_institution_created_idx",
            ),
            models.Index(fields=["actor", "-created_at"], name="audit_actor_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.action} ({self.target_type}:{self.target_id})"
