from django.urls import path

from apps.institutions.views import (
    InstitutionAuditListView,
    InstitutionDetailView,
    InstitutionListCreateView,
    MembershipDetailView,
    MembershipListCreateView,
)

urlpatterns = [
    path("institutions/", InstitutionListCreateView.as_view(), name="institution-list"),
    path(
        "institutions/<uuid:institution_id>/",
        InstitutionDetailView.as_view(),
        name="institution-detail",
    ),
    path(
        "institutions/<uuid:institution_id>/members/",
        MembershipListCreateView.as_view(),
        name="institution-members",
    ),
    path(
        "institutions/<uuid:institution_id>/members/<uuid:membership_id>/",
        MembershipDetailView.as_view(),
        name="institution-member-detail",
    ),
    path(
        "institutions/<uuid:institution_id>/audit-events/",
        InstitutionAuditListView.as_view(),
        name="institution-audit",
    ),
]
