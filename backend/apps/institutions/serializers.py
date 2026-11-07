from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from apps.audit.models import AuditLog
from apps.institutions.models import Institution, InstitutionMembership

RESERVED_SLUGS = {"admin", "api", "auth", "health", "www"}


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise serializers.ValidationError("Unknown IANA timezone.") from exc
    return value


class InstitutionSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = (
            "id",
            "name",
            "slug",
            "status",
            "timezone",
            "settings",
            "role",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_role(self, institution) -> str | None:
        memberships = getattr(institution, "_current_memberships", None)
        if memberships is not None:
            return memberships[0].role if memberships else None
        membership = self.context.get("membership")
        if membership is not None and membership.institution_id == institution.id:
            return membership.role
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self.context.get("can_manage", False):
            data.pop("settings", None)
        return data


class InstitutionAdminInputSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    full_name = serializers.CharField(max_length=255, trim_whitespace=True)
    password = serializers.CharField(
        write_only=True,
        min_length=12,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    def validate_email(self, value: str) -> str:
        return value.strip().casefold()


class InstitutionCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, trim_whitespace=True)
    slug = serializers.SlugField(max_length=100)
    timezone = serializers.CharField(max_length=64, default="UTC")
    settings = serializers.JSONField(default=dict)
    admin = InstitutionAdminInputSerializer()

    def validate_slug(self, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in RESERVED_SLUGS:
            raise serializers.ValidationError("This slug is reserved.")
        return normalized

    def validate_timezone(self, value: str) -> str:
        return validate_timezone(value)

    def validate_settings(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Settings must be a JSON object.")
        return value


class InstitutionUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, trim_whitespace=True, required=False)
    timezone = serializers.CharField(max_length=64, required=False)
    settings = serializers.JSONField(required=False)
    status = serializers.ChoiceField(choices=Institution.Status.choices, required=False)

    def validate_timezone(self, value: str) -> str:
        return validate_timezone(value)

    def validate_settings(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Settings must be a JSON object.")
        return value

    def validate_status(self, value: str) -> str:
        request = self.context.get("request")
        if request is None or not request.user.is_platform_admin:
            raise serializers.ValidationError(
                "Only platform administrators can change institution status."
            )
        return value


class MemberUserSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)


class MembershipSerializer(serializers.ModelSerializer):
    user = MemberUserSerializer(read_only=True)

    class Meta:
        model = InstitutionMembership
        fields = ("id", "user", "role", "is_active", "created_at", "updated_at")
        read_only_fields = fields


class MembershipCreateSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    full_name = serializers.CharField(max_length=255, trim_whitespace=True)
    role = serializers.ChoiceField(choices=InstitutionMembership.Role.choices)
    password = serializers.CharField(
        write_only=True,
        min_length=12,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    def validate_email(self, value: str) -> str:
        return value.strip().casefold()


class MembershipUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=InstitutionMembership.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if "role" not in attrs and "is_active" not in attrs:
            raise serializers.ValidationError("Provide at least one of role or is_active.")
        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "action",
            "actor_email",
            "target_type",
            "target_id",
            "metadata",
            "ip_address",
            "user_agent",
            "request_id",
            "created_at",
        )
        read_only_fields = fields
