from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "is_platform_admin", "date_joined")
        read_only_fields = fields


class MembershipContextSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    role = serializers.CharField(read_only=True)
    institution = serializers.SerializerMethodField()

    def get_institution(self, membership) -> dict:
        institution = membership.institution
        return {
            "id": str(institution.id),
            "name": institution.name,
            "slug": institution.slug,
            "status": institution.status,
            "timezone": institution.timezone,
        }


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def get_token(self, user):
        token = super().get_token(user)
        token["auth_version"] = user.auth_version
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        from apps.institutions.models import InstitutionMembership

        memberships = (
            InstitutionMembership.objects.filter(
                user=self.user,
                is_active=True,
                institution__status="active",
            )
            .select_related("institution")
            .order_by("institution__name")
        )
        data["user"] = UserSerializer(self.user).data
        data["memberships"] = MembershipContextSerializer(memberships, many=True).data
        return data


class VersionedTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            refresh = RefreshToken(attrs["refresh"])
        except TokenError as exc:
            raise AuthenticationFailed(str(exc), code="invalid_token") from exc

        user_id = refresh.get("user_id")
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None or refresh.get("auth_version", 0) != user.auth_version:
            raise AuthenticationFailed("Token has been revoked.", code="token_revoked")
        return super().validate(attrs)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True, trim_whitespace=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, min_length=12)

    def validate_current_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": ["The new password must differ from the current password."]}
            )
        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        return attrs


class MeSerializer(serializers.ModelSerializer):
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "is_platform_admin",
            "date_joined",
            "memberships",
        )
        read_only_fields = ("id", "email", "is_platform_admin", "date_joined", "memberships")

    def get_memberships(self, user) -> list[dict]:
        memberships = (
            user.institution_memberships.filter(is_active=True)
            .select_related("institution")
            .order_by("institution__name")
        )
        return MembershipContextSerializer(memberships, many=True).data

    def update(self, instance, validated_data):
        instance.full_name = validated_data.get("full_name", instance.full_name)
        instance.save(update_fields=["full_name"])
        return instance
