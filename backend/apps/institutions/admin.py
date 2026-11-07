from django.contrib import admin

from apps.institutions.models import Institution, InstitutionMembership


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "timezone", "created_at")
    list_filter = ("status", "timezone")
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at", "created_by")


@admin.register(InstitutionMembership)
class InstitutionMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "institution", "role", "is_active", "updated_at")
    list_filter = ("role", "is_active", "institution")
    search_fields = ("user__email", "user__full_name", "institution__name")
    readonly_fields = ("id", "created_at", "updated_at", "created_by")
    list_select_related = ("user", "institution")
