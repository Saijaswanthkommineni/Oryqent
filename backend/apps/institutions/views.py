from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsPlatformAdmin
from apps.audit.models import AuditLog
from apps.institutions.models import Institution, InstitutionMembership
from apps.institutions.permissions import IsInstitutionAdmin, IsInstitutionMember
from apps.institutions.serializers import (
    AuditLogSerializer,
    InstitutionCreateSerializer,
    InstitutionSerializer,
    InstitutionUpdateSerializer,
    MembershipCreateSerializer,
    MembershipSerializer,
    MembershipUpdateSerializer,
)
from apps.institutions.services import (
    create_institution_with_admin,
    create_membership,
    update_institution,
    update_membership,
)


class InstitutionListCreateView(ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPlatformAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Institution.objects.all()
        if not self.request.user.is_platform_admin:
            queryset = queryset.filter(
                memberships__user=self.request.user,
                memberships__is_active=True,
                status=Institution.Status.ACTIVE,
            )
        current_memberships = InstitutionMembership.objects.filter(
            user=self.request.user,
            is_active=True,
        )
        return queryset.prefetch_related(
            Prefetch("memberships", queryset=current_memberships, to_attr="_current_memberships")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return InstitutionCreateSerializer
        return InstitutionSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["can_manage"] = False
        return context

    def create(self, request, *args, **kwargs):
        serializer = InstitutionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        institution, membership = create_institution_with_admin(
            actor=request.user,
            name=data["name"],
            slug=data["slug"],
            timezone=data["timezone"],
            settings=data["settings"],
            admin_email=data["admin"]["email"],
            admin_full_name=data["admin"]["full_name"],
            admin_password=data["admin"]["password"],
            request=request,
        )
        output = InstitutionSerializer(
            institution,
            context={"request": request, "can_manage": True, "membership": membership},
        )
        return Response(output.data, status=status.HTTP_201_CREATED)


class InstitutionDetailView(APIView):
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsInstitutionAdmin()]
        return [IsInstitutionMember()]

    def get(self, request, institution_id):
        can_manage = request.user.is_platform_admin or (
            self.membership is not None
            and self.membership.role == InstitutionMembership.Role.INSTITUTION_ADMIN
        )
        serializer = InstitutionSerializer(
            self.institution,
            context={"request": request, "can_manage": can_manage, "membership": self.membership},
        )
        return Response(serializer.data)

    def patch(self, request, institution_id):
        serializer = InstitutionUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        institution = update_institution(
            actor=request.user,
            institution=self.institution,
            changes=serializer.validated_data,
            request=request,
        )
        can_manage = True
        output = InstitutionSerializer(
            institution,
            context={"request": request, "can_manage": can_manage, "membership": self.membership},
        )
        return Response(output.data)


class MembershipListCreateView(ListCreateAPIView):
    permission_classes = [IsInstitutionAdmin]
    serializer_class = MembershipSerializer

    def get_queryset(self):
        return InstitutionMembership.objects.filter(institution=self.institution).select_related(
            "user"
        )

    def create(self, request, institution_id):
        serializer = MembershipCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        membership = create_membership(
            actor=request.user,
            institution=self.institution,
            email=data["email"],
            full_name=data["full_name"],
            role=data["role"],
            password=data["password"],
            request=request,
        )
        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )


class MembershipDetailView(APIView):
    permission_classes = [IsInstitutionAdmin]
    http_method_names = ["patch", "head", "options"]

    def patch(self, request, institution_id, membership_id):
        membership = get_object_or_404(
            InstitutionMembership.objects.select_related("user"),
            pk=membership_id,
            institution=self.institution,
        )
        serializer = MembershipUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = update_membership(
            actor=request.user,
            institution=self.institution,
            membership_id=membership.pk,
            changes=serializer.validated_data,
            request=request,
        )
        return Response(MembershipSerializer(membership).data)


class InstitutionAuditListView(ListAPIView):
    permission_classes = [IsInstitutionAdmin]
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        return AuditLog.objects.filter(institution=self.institution).select_related("actor")
