from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.forms import OryqentUserChangeForm, OryqentUserCreationForm
from apps.accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = OryqentUserCreationForm
    form = OryqentUserChangeForm
    model = User
    ordering = ("email",)
    list_display = ("email", "full_name", "is_platform_admin", "is_active", "is_staff")
    list_filter = ("is_platform_admin", "is_active", "is_staff")
    search_fields = ("email", "full_name")
    readonly_fields = ("last_login", "date_joined", "auth_version")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name",)}),
        (
            "Access",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_platform_admin",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Security", {"fields": ("auth_version", "last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password1", "password2", "is_platform_admin"),
            },
        ),
    )
