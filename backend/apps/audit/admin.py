from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "actor", "institution", "target_type", "target_id")
    list_filter = ("action", "institution")
    search_fields = ("target_id", "actor__email", "request_id")
    readonly_fields = (
        "id",
        "institution",
        "actor",
        "action",
        "target_type",
        "target_id",
        "metadata",
        "ip_address",
        "user_agent",
        "request_id",
        "created_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
