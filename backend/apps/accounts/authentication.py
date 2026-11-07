from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class VersionedJWTAuthentication(JWTAuthentication):
    """Reject tokens issued before the account's last credential invalidation."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        token_version = validated_token.get("auth_version", 0)
        if token_version != user.auth_version:
            raise AuthenticationFailed("Token has been revoked.", code="token_revoked")
        return user
