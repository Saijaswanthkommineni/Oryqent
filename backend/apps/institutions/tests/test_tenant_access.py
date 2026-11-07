from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.institutions.models import Institution, InstitutionMembership

PASSWORD = "Initial-Password-2026!"
NEW_ACCOUNT_PASSWORD = "Created-Account-2026!Alpha"


class TenantAPITestCase(APITestCase):
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
        self.student_a = User.objects.create_user(
            email="student.a@example.com",
            password=PASSWORD,
            full_name="Student A",
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
        self.membership_student_a = InstitutionMembership.objects.create(
            institution=self.institution_a,
            user=self.student_a,
            role=InstitutionMembership.Role.STUDENT,
        )
        self.membership_admin_b = InstitutionMembership.objects.create(
            institution=self.institution_b,
            user=self.admin_b,
            role=InstitutionMembership.Role.INSTITUTION_ADMIN,
        )

    def login(self, email: str, password: str = PASSWORD) -> dict:
        response = self.client.post(
            reverse("auth-login"),
            {"email": email, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data

    def test_institution_list_is_scoped_to_membership_and_includes_role(self):
        self.login(self.admin_a.email)
        response = self.client.get(reverse("institution-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["slug"], "alpha")
        self.assertEqual(
            response.data["results"][0]["role"],
            InstitutionMembership.Role.INSTITUTION_ADMIN,
        )

    def test_platform_admin_lists_every_institution_without_membership(self):
        self.login(self.platform.email)
        response = self.client.get(reverse("institution-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["slug"] for item in response.data["results"]},
            {"alpha", "beta"},
        )

    def test_member_detail_hides_settings_from_non_administrators(self):
        self.login(self.teacher_a.email)
        response = self.client.get(
            reverse("institution-detail", kwargs={"institution_id": self.institution_a.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("settings", response.data)

        self.login(self.admin_a.email)
        admin_response = self.client.get(
            reverse("institution-detail", kwargs={"institution_id": self.institution_a.id})
        )
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.assertIn("settings", admin_response.data)

    def test_cross_tenant_read_write_and_member_management_are_denied(self):
        self.login(self.teacher_a.email)
        read_other = self.client.get(
            reverse("institution-detail", kwargs={"institution_id": self.institution_b.id})
        )
        self.assertEqual(read_other.status_code, status.HTTP_403_FORBIDDEN)

        self.login(self.admin_a.email)
        patch_other = self.client.patch(
            reverse("institution-detail", kwargs={"institution_id": self.institution_b.id}),
            {"name": "Compromised"},
            format="json",
        )
        self.assertEqual(patch_other.status_code, status.HTTP_403_FORBIDDEN)
        self.institution_b.refresh_from_db()
        self.assertEqual(self.institution_b.name, "Beta College")

        members_other = self.client.get(
            reverse("institution-members", kwargs={"institution_id": self.institution_b.id})
        )
        self.assertEqual(members_other.status_code, status.HTTP_403_FORBIDDEN)

        audit_other = self.client.get(
            reverse("institution-audit", kwargs={"institution_id": self.institution_b.id})
        )
        self.assertEqual(audit_other.status_code, status.HTTP_403_FORBIDDEN)

    def test_membership_from_another_tenant_cannot_be_updated_through_own_path(self):
        self.login(self.admin_a.email)
        response = self.client.patch(
            reverse(
                "institution-member-detail",
                kwargs={
                    "institution_id": self.institution_a.id,
                    "membership_id": self.membership_admin_b.id,
                },
            ),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_and_student_cannot_manage_members(self):
        for account in (self.teacher_a, self.student_a):
            self.login(account.email)
            listing = self.client.get(
                reverse("institution-members", kwargs={"institution_id": self.institution_a.id})
            )
            self.assertEqual(listing.status_code, status.HTTP_403_FORBIDDEN)

            creation = self.client.post(
                reverse("institution-members", kwargs={"institution_id": self.institution_a.id}),
                {
                    "email": f"new-{account.email}",
                    "full_name": "Injected User",
                    "role": InstitutionMembership.Role.STUDENT,
                    "password": NEW_ACCOUNT_PASSWORD,
                },
                format="json",
            )
            self.assertEqual(creation.status_code, status.HTTP_403_FORBIDDEN)

    def test_institution_admin_creates_teacher_with_hashed_password_and_audit(self):
        self.login(self.admin_a.email)
        response = self.client.post(
            reverse("institution-members", kwargs={"institution_id": self.institution_a.id}),
            {
                "email": "New.Teacher@Example.com",
                "full_name": "New Teacher",
                "role": InstitutionMembership.Role.TEACHER,
                "password": NEW_ACCOUNT_PASSWORD,
            },
            format="json",
            HTTP_X_REQUEST_ID="test-request-0001",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["user"]["email"], "new.teacher@example.com")
        self.assertEqual(response.data["role"], InstitutionMembership.Role.TEACHER)

        user = User.objects.get(email="new.teacher@example.com")
        self.assertTrue(user.check_password(NEW_ACCOUNT_PASSWORD))
        self.assertNotEqual(user.password, NEW_ACCOUNT_PASSWORD)

        event = AuditLog.objects.get(
            action=AuditLog.Action.MEMBERSHIP_CREATED,
            target_id=str(response.data["id"]),
        )
        self.assertEqual(event.actor, self.admin_a)
        self.assertEqual(event.institution, self.institution_a)
        self.assertEqual(event.request_id, "test-request-0001")

    def test_institution_admin_cannot_create_or_promote_another_administrator(self):
        self.login(self.admin_a.email)
        create_admin = self.client.post(
            reverse("institution-members", kwargs={"institution_id": self.institution_a.id}),
            {
                "email": "second.admin@example.com",
                "full_name": "Second Admin",
                "role": InstitutionMembership.Role.INSTITUTION_ADMIN,
                "password": NEW_ACCOUNT_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(create_admin.status_code, status.HTTP_403_FORBIDDEN)

        promote = self.client.patch(
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
        self.assertEqual(promote.status_code, status.HTTP_403_FORBIDDEN)

        modify_admin = self.client.patch(
            reverse(
                "institution-member-detail",
                kwargs={
                    "institution_id": self.institution_a.id,
                    "membership_id": self.membership_admin_a.id,
                },
            ),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(modify_admin.status_code, status.HTTP_403_FORBIDDEN)

    def test_deactivating_membership_blocks_tenant_access_immediately(self):
        teacher_tokens = self.login(self.teacher_a.email)
        self.login(self.admin_a.email)
        response = self.client.patch(
            reverse(
                "institution-member-detail",
                kwargs={
                    "institution_id": self.institution_a.id,
                    "membership_id": self.membership_teacher_a.id,
                },
            ),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_active"])
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.MEMBERSHIP_DEACTIVATED,
                target_id=str(self.membership_teacher_a.id),
            ).exists()
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {teacher_tokens['access']}")
        tenant = self.client.get(
            reverse("institution-detail", kwargs={"institution_id": self.institution_a.id})
        )
        self.assertEqual(tenant.status_code, status.HTTP_403_FORBIDDEN)
        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["memberships"], [])

    def test_platform_admin_cannot_remove_the_last_active_admin(self):
        self.login(self.platform.email)
        response = self.client.patch(
            reverse(
                "institution-member-detail",
                kwargs={
                    "institution_id": self.institution_a.id,
                    "membership_id": self.membership_admin_a.id,
                },
            ),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("at least one active administrator", response.data["error"]["message"])

        created = self.client.post(
            reverse("institution-members", kwargs={"institution_id": self.institution_a.id}),
            {
                "email": "second.admin@example.com",
                "full_name": "Second Admin",
                "role": InstitutionMembership.Role.INSTITUTION_ADMIN,
                "password": NEW_ACCOUNT_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        second_membership_id = created.data["id"]

        first_deactivated = self.client.patch(
            reverse(
                "institution-member-detail",
                kwargs={
                    "institution_id": self.institution_a.id,
                    "membership_id": self.membership_admin_a.id,
                },
            ),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(first_deactivated.status_code, status.HTTP_200_OK)

        last_deactivated = self.client.patch(
            reverse(
                "institution-member-detail",
                kwargs={
                    "institution_id": self.institution_a.id,
                    "membership_id": second_membership_id,
                },
            ),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(last_deactivated.status_code, status.HTTP_400_BAD_REQUEST)

    def test_platform_admin_creates_institution_and_first_admin_atomically(self):
        self.login(self.platform.email)
        response = self.client.post(
            reverse("institution-list"),
            {
                "name": "Gamma University",
                "slug": "GAMMA",
                "timezone": "Asia/Kolkata",
                "settings": {"grading": "percentage"},
                "admin": {
                    "email": "Gamma.Admin@Example.com",
                    "full_name": "Gamma Admin",
                    "password": NEW_ACCOUNT_PASSWORD,
                },
            },
            format="json",
            HTTP_X_REQUEST_ID="create-gamma-001",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["slug"], "gamma")
        self.assertEqual(response.data["status"], Institution.Status.ACTIVE)

        institution = Institution.objects.get(slug="gamma")
        membership = InstitutionMembership.objects.get(institution=institution)
        self.assertEqual(membership.user.email, "gamma.admin@example.com")
        self.assertEqual(membership.role, InstitutionMembership.Role.INSTITUTION_ADMIN)
        self.assertTrue(membership.user.check_password(NEW_ACCOUNT_PASSWORD))

        actions = set(
            AuditLog.objects.filter(institution=institution).values_list("action", flat=True)
        )
        self.assertEqual(
            actions,
            {
                AuditLog.Action.INSTITUTION_CREATED,
                AuditLog.Action.MEMBERSHIP_CREATED,
            },
        )
        self.assertTrue(
            AuditLog.objects.filter(
                institution=institution,
                request_id="create-gamma-001",
            ).exists()
        )

        self.login("gamma.admin@example.com", NEW_ACCOUNT_PASSWORD)
        scoped = self.client.get(reverse("institution-list"))
        self.assertEqual(
            [item["slug"] for item in scoped.data["results"]],
            ["gamma"],
        )

    def test_non_platform_user_cannot_create_institutions(self):
        self.login(self.admin_a.email)
        response = self.client.post(
            reverse("institution-list"),
            {
                "name": "Unauthorized",
                "slug": "unauthorized",
                "admin": {
                    "email": "new@example.com",
                    "full_name": "New Admin",
                    "password": NEW_ACCOUNT_PASSWORD,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Institution.objects.filter(slug="unauthorized").exists())

    def test_duplicate_slug_and_duplicate_admin_email_are_rejected(self):
        self.login(self.platform.email)
        duplicate_slug = self.client.post(
            reverse("institution-list"),
            {
                "name": "Duplicate",
                "slug": "ALPHA",
                "admin": {
                    "email": "brand.new@example.com",
                    "full_name": "Brand New",
                    "password": NEW_ACCOUNT_PASSWORD,
                },
            },
            format="json",
        )
        self.assertEqual(duplicate_slug.status_code, status.HTTP_400_BAD_REQUEST)

        duplicate_email = self.client.post(
            reverse("institution-list"),
            {
                "name": "Duplicate Email",
                "slug": "duplicate-email",
                "admin": {
                    "email": "ADMIN.A@example.com",
                    "full_name": "Existing Admin",
                    "password": NEW_ACCOUNT_PASSWORD,
                },
            },
            format="json",
        )
        self.assertEqual(duplicate_email.status_code, status.HTTP_400_BAD_REQUEST)

    def test_suspension_blocks_tenant_access_but_not_platform_administration(self):
        self.login(self.platform.email)
        suspended = self.client.patch(
            reverse("institution-detail", kwargs={"institution_id": self.institution_a.id}),
            {"status": Institution.Status.SUSPENDED},
            format="json",
        )
        self.assertEqual(suspended.status_code, status.HTTP_200_OK)
        self.assertEqual(suspended.data["status"], Institution.Status.SUSPENDED)

        platform_read = self.client.get(
            reverse("institution-detail", kwargs={"institution_id": self.institution_a.id})
        )
        self.assertEqual(platform_read.status_code, status.HTTP_200_OK)

        self.login(self.admin_a.email)
        denied = self.client.get(
            reverse("institution-detail", kwargs={"institution_id": self.institution_a.id})
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        scoped = self.client.get(reverse("institution-list"))
        self.assertNotIn("alpha", [item["slug"] for item in scoped.data["results"]])

    def test_institution_admin_cannot_suspend_or_change_immutable_slug(self):
        self.login(self.admin_a.email)
        response = self.client.patch(
            reverse("institution-detail", kwargs={"institution_id": self.institution_a.id}),
            {"status": Institution.Status.SUSPENDED, "slug": "takeover"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data["error"]["details"])
        self.institution_a.refresh_from_db()
        self.assertEqual(self.institution_a.slug, "alpha")
        self.assertEqual(self.institution_a.status, Institution.Status.ACTIVE)

    def test_institution_admin_updates_name_and_audit_is_recorded(self):
        self.login(self.admin_a.email)
        response = self.client.patch(
            reverse("institution-detail", kwargs={"institution_id": self.institution_a.id}),
            {"name": "Alpha College Renamed"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Alpha College Renamed")
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.INSTITUTION_UPDATED,
                institution=self.institution_a,
                actor=self.admin_a,
            ).exists()
        )

    def test_invalid_timezone_and_reserved_slug_are_rejected(self):
        self.login(self.platform.email)
        invalid_timezone = self.client.patch(
            reverse("institution-detail", kwargs={"institution_id": self.institution_a.id}),
            {"timezone": "Mars/Olympus_Mons"},
            format="json",
        )
        self.assertEqual(invalid_timezone.status_code, status.HTTP_400_BAD_REQUEST)

        reserved = self.client.post(
            reverse("institution-list"),
            {
                "name": "Reserved",
                "slug": "admin",
                "admin": {
                    "email": "reserved@example.com",
                    "full_name": "Reserved Admin",
                    "password": NEW_ACCOUNT_PASSWORD,
                },
            },
            format="json",
        )
        self.assertEqual(reserved.status_code, status.HTTP_400_BAD_REQUEST)

    def test_audit_log_is_institution_scoped_and_admin_only(self):
        self.login(self.admin_a.email)
        admin_response = self.client.get(
            reverse("institution-audit", kwargs={"institution_id": self.institution_a.id})
        )
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)

        self.login(self.teacher_a.email)
        teacher_response = self.client.get(
            reverse("institution-audit", kwargs={"institution_id": self.institution_a.id})
        )
        self.assertEqual(teacher_response.status_code, status.HTTP_403_FORBIDDEN)
