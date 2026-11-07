from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.institutions.models import Institution, InstitutionMembership

PASSWORD = "Initial-Password-2026!"
NEW_ACCOUNT_PASSWORD = "Created-Account-2026!Alpha"


class SecurityBoundaryTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.platform = User.objects.create_user(
            email="platform@example.com",
            password=PASSWORD,
            full_name="Platform Admin",
            is_platform_admin=True,
        )
        self.admin_a = User.objects.create_user(
            email="admin.a@example.com",
            password=PASSWORD,
            full_name="Admin A",
        )
        self.teacher_a = User.objects.create_user(
            email="teacher.a@example.com",
            password=PASSWORD,
            full_name="Teacher A",
        )
        self.admin_b = User.objects.create_user(
            email="admin.b@example.com",
            password=PASSWORD,
            full_name="Admin B",
        )
        self.institution_a = Institution.objects.create(name="Alpha College", slug="alpha")
        self.institution_b = Institution.objects.create(name="Beta College", slug="beta")
        self.membership_admin_a = InstitutionMembership.objects.create(
            institution=self.institution_a,
            user=self.admin_a,
            role=InstitutionMembership.Role.INSTITUTION_ADMIN,
        )
        self.membership_teacher_a = InstitutionMembership.objects.create(
            institution=self.institution_a,
            user=self.teacher_a,
            role=InstitutionMembership.Role.TEACHER,
        )
        self.membership_admin_b = InstitutionMembership.objects.create(
            institution=self.institution_b,
            user=self.admin_b,
            role=InstitutionMembership.Role.INSTITUTION_ADMIN,
        )

    def login(self, email: str) -> None:
        response = self.client.post(
            reverse("auth-login"),
            {"email": email, "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_all_tenant_endpoints_reject_unauthenticated_requests(self):
        member_url = reverse(
            "institution-member-detail",
            kwargs={
                "institution_id": self.institution_a.id,
                "membership_id": self.membership_teacher_a.id,
            },
        )
        requests = [
            ("get", reverse("institution-list"), None),
            ("post", reverse("institution-list"), {}),
            (
                "get",
                reverse("institution-detail", kwargs={"institution_id": self.institution_a.id}),
                None,
            ),
            (
                "patch",
                reverse("institution-detail", kwargs={"institution_id": self.institution_a.id}),
                {"name": "Injected"},
            ),
            (
                "get",
                reverse("institution-members", kwargs={"institution_id": self.institution_a.id}),
                None,
            ),
            (
                "post",
                reverse("institution-members", kwargs={"institution_id": self.institution_a.id}),
                {},
            ),
            ("patch", member_url, {"role": InstitutionMembership.Role.STUDENT}),
            (
                "get",
                reverse("institution-audit", kwargs={"institution_id": self.institution_a.id}),
                None,
            ),
        ]

        for method, url, data in requests:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, data, format="json")
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_client_supplied_institution_ids_cannot_override_url_tenant(self):
        self.login(self.admin_a.email)

        listing = self.client.get(
            reverse("institution-list"),
            {
                "institution_id": str(self.institution_b.id),
                "institution": str(self.institution_b.id),
            },
        )
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual([item["slug"] for item in listing.data["results"]], ["alpha"])

        detail = self.client.get(
            reverse("institution-detail", kwargs={"institution_id": self.institution_a.id}),
            {
                "institution_id": str(self.institution_b.id),
                "institution": str(self.institution_b.id),
            },
            HTTP_X_INSTITUTION_ID=str(self.institution_b.id),
        )
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["id"], str(self.institution_a.id))
        self.assertEqual(detail.data["slug"], "alpha")

    def test_membership_creation_ignores_injected_institution_and_privilege_fields(self):
        self.login(self.admin_a.email)
        response = self.client.post(
            reverse("institution-members", kwargs={"institution_id": self.institution_a.id}),
            {
                "email": "new.student@example.com",
                "full_name": "New Student",
                "role": InstitutionMembership.Role.STUDENT,
                "password": NEW_ACCOUNT_PASSWORD,
                "institution": str(self.institution_b.id),
                "institution_id": str(self.institution_b.id),
                "user": str(self.platform.id),
                "created_by": str(self.platform.id),
                "is_platform_admin": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        created = InstitutionMembership.objects.select_related("user").get(pk=response.data["id"])
        self.assertEqual(created.institution, self.institution_a)
        self.assertEqual(created.role, InstitutionMembership.Role.STUDENT)
        self.assertEqual(created.user.email, "new.student@example.com")
        self.assertFalse(created.user.is_platform_admin)
        self.assertFalse(
            InstitutionMembership.objects.filter(
                institution=self.institution_b,
                user=created.user,
            ).exists()
        )

    def test_jwt_tenant_and_role_claims_are_not_trusted(self):
        token = AccessToken.for_user(self.teacher_a)
        token["auth_version"] = self.teacher_a.auth_version
        token["institution_id"] = str(self.institution_b.id)
        token["role"] = InstitutionMembership.Role.INSTITUTION_ADMIN
        token["is_platform_admin"] = True
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        read_other = self.client.get(
            reverse("institution-detail", kwargs={"institution_id": self.institution_b.id})
        )
        self.assertEqual(read_other.status_code, status.HTTP_403_FORBIDDEN)

        promote_self = self.client.patch(
            reverse(
                "institution-member-detail",
                kwargs={
                    "institution_id": self.institution_a.id,
                    "membership_id": self.membership_teacher_a.id,
                },
            ),
            {"role": InstitutionMembership.Role.INSTITUTION_ADMIN},
            format="json",
        )
        self.assertEqual(promote_self.status_code, status.HTTP_403_FORBIDDEN)

        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertFalse(me.data["is_platform_admin"])

    def test_membership_cannot_be_self_promoted_to_administrator(self):
        self.login(self.teacher_a.email)
        response = self.client.patch(
            reverse(
                "institution-member-detail",
                kwargs={
                    "institution_id": self.institution_a.id,
                    "membership_id": self.membership_teacher_a.id,
                },
            ),
            {"role": InstitutionMembership.Role.INSTITUTION_ADMIN},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.membership_teacher_a.refresh_from_db()
        self.assertEqual(self.membership_teacher_a.role, InstitutionMembership.Role.TEACHER)

    def test_cross_tenant_membership_writes_are_denied(self):
        self.login(self.admin_a.email)

        create_other = self.client.post(
            reverse("institution-members", kwargs={"institution_id": self.institution_b.id}),
            {
                "email": "injected@example.com",
                "full_name": "Injected User",
                "role": InstitutionMembership.Role.STUDENT,
                "password": NEW_ACCOUNT_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(create_other.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(email="injected@example.com").exists())

        update_other = self.client.patch(
            reverse(
                "institution-member-detail",
                kwargs={
                    "institution_id": self.institution_b.id,
                    "membership_id": self.membership_admin_b.id,
                },
            ),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(update_other.status_code, status.HTTP_403_FORBIDDEN)
        self.membership_admin_b.refresh_from_db()
        self.assertTrue(self.membership_admin_b.is_active)

    def test_duplicate_membership_is_blocked_by_database_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                InstitutionMembership.objects.create(
                    institution=self.institution_a,
                    user=self.teacher_a,
                    role=InstitutionMembership.Role.STUDENT,
                )

        self.assertEqual(
            InstitutionMembership.objects.filter(
                institution=self.institution_a,
                user=self.teacher_a,
            ).count(),
            1,
        )

    def test_duplicate_account_email_prevents_second_membership(self):
        self.login(self.admin_a.email)
        response = self.client.post(
            reverse("institution-members", kwargs={"institution_id": self.institution_a.id}),
            {
                "email": "TEACHER.A@Example.COM",
                "full_name": "Duplicate Teacher",
                "role": InstitutionMembership.Role.STUDENT,
                "password": NEW_ACCOUNT_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            InstitutionMembership.objects.filter(
                institution=self.institution_a,
                user=self.teacher_a,
            ).count(),
            1,
        )
