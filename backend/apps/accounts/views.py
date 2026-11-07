import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.serializers import (
    EmailTokenObtainPairSerializer,
    LogoutSerializer,
    MeSerializer,
    PasswordChangeSerializer,
    VersionedTokenRefreshSerializer,
)
from apps.accounts.services import change_password

logger = logging.getLogger("apps.accounts")


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"
    serializer_class = EmailTokenObtainPairSerializer


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token_refresh"
    serializer_class = VersionedTokenRefreshSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            if str(token.get("user_id")) != str(request.user.pk):
                raise TokenError("Token does not belong to the authenticated user.")
            token.blacklist()
        except TokenError as exc:
            raise ValidationError({"refresh": [str(exc)]}) from exc
        logger.info(
            "User logged out", extra={"event": "auth.logout", "actor_id": str(request.user.pk)}
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_change"

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        change_password(user=request.user, new_password=serializer.validated_data["new_password"])
        logger.info(
            "User changed password; all tokens revoked",
            extra={"event": "auth.password_changed", "actor_id": str(request.user.pk)},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
