import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.institutions.models import Institution, InstitutionMembership

INITIAL_PASSWORD = "Initial-Password-2026!"
NEW_PASSWORD = "New-Password-2026!Secure"


def create_user(
    email: str,
    *,
    password: str = INITIAL_PASSWORD,
    full_name: str = "Test User",
    **extra,
) -> User:
    return User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name,
        **extra,
    )


class UserModelTests(TestCase):
    def test_email_is_case_insensitive_and_password_is_hashed(self):
        user = create_user("Mixed.Case@Example.COM")
        user.refresh_from_db()
        self.assertEqual(user.email, "mixed.case@example.com")
        self.assertNotEqual(user.password, INITIAL_PASSWORD)
        self.assertTrue(user.check_password(INITIAL_PASSWORD))

    def test_superuser_creation_sets_explicit_platform_admin_flag(self):
        user = User.objects.create_superuser(
            email="root@example.com",
            password=INITIAL_PASSWORD,
            full_name="Root Admin",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_platform_admin)


class PlatformAdminCommandTests(TestCase):
    def test_command_creates_platform_superuser_without_password_argument(self):
        output = StringIO()
        with patch.dict(os.environ, {"ORYQENT_PLATFORM_ADMIN_PASSWORD": NEW_PASSWORD}):
            call_command(
                "create_platform_admin",
                "--email",
                "Root@Example.com",
                "--full-name",
                "Root Admin",
                stdout=output,
            )
        user = User.objects.get(email="root@example.com")
        self.assertTrue(user.is_platform_admin)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password(NEW_PASSWORD))
        self.assertIn("Created platform administrator", output.getvalue())

    def test_command_rejects_duplicate_email_case_insensitively(self):
        create_user("root@example.com")
        with patch.dict(os.environ, {"ORYQENT_PLATFORM_ADMIN_PASSWORD": NEW_PASSWORD}):
            with self.assertRaises(CommandError):
                call_command(
                    "create_platform_admin",
                    "--email",
                    "ROOT@example.com",
                    "--full-name",
                    "Duplicate Root",
                )


class AuthenticationAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user("student@example.com", full_name="Student One")
        self.institution = Institution.objects.create(name="North College", slug="north")
        InstitutionMembership.objects.create(
            institution=self.institution,
            user=self.user,
            role=InstitutionMembership.Role.STUDENT,
        )

    def login(self, email="student@example.com", password=INITIAL_PASSWORD):
        response = self.client.post(
            reverse("auth-login"),
            {"email": email, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    def test_login_returns_tokens_user_and_active_memberships(self):
        response = self.login()
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "student@example.com")
        self.assertEqual(len(response.data["memberships"]), 1)
        membership = response.data["memberships"][0]
        self.assertEqual(membership["role"], InstitutionMembership.Role.STUDENT)
        self.assertEqual(membership["institution"]["slug"], "north")

    def test_login_excludes_suspended_institution_and_inactive_membership(self):
        suspended = Institution.objects.create(
            name="Suspended Institute",
            slug="suspended",
            status=Institution.Status.SUSPENDED,
        )
        InstitutionMembership.objects.create(
            institution=suspended,
            user=self.user,
            role=InstitutionMembership.Role.STUDENT,
        )
        inactive = Institution.objects.create(name="Inactive Institute", slug="inactive")
        InstitutionMembership.objects.create(
            institution=inactive,
            user=self.user,
            role=InstitutionMembership.Role.TEACHER,
            is_active=False,
        )

        response = self.login()
        self.assertEqual(
            [item["institution"]["slug"] for item in response.data["memberships"]],
            ["north"],
        )

    def test_wrong_password_is_generic_and_does_not_disclose_account_existence(self):
        wrong = self.client.post(
            reverse("auth-login"),
            {"email": "student@example.com", "password": "wrong-password"},
            format="json",
        )
        unknown = self.client.post(
            reverse("auth-login"),
            {"email": "nobody@example.com", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(wrong.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(unknown.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            wrong.data["error"]["message"],
            unknown.data["error"]["message"],
        )
        self.assertNotIn("student@example.com", str(wrong.data))

    def test_inactive_account_cannot_log_in(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(
            reverse("auth-login"),
            {"email": "student@example.com", "password": INITIAL_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication_and_returns_memberships(self):
        unauthenticated = self.client.get(reverse("auth-me"))
        self.assertEqual(unauthenticated.status_code, status.HTTP_401_UNAUTHORIZED)

        self.login()
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Student One")
        self.assertEqual(response.data["memberships"][0]["institution"]["slug"], "north")

    def test_me_patch_only_changes_allowed_profile_field(self):
        self.login()
        response = self.client.patch(
            reverse("auth-me"),
            {"full_name": "Updated Name", "email": "attacker@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Name")
        self.assertEqual(self.user.email, "student@example.com")

    def test_refresh_rotates_and_blacklists_the_old_token(self):
        login = self.login()
        old_refresh = login.data["refresh"]
        rotated = self.client.post(
            reverse("auth-refresh"),
            {"refresh": old_refresh},
            format="json",
        )
        self.assertEqual(rotated.status_code, status.HTTP_200_OK)
        self.assertNotEqual(rotated.data["refresh"], old_refresh)

        reused = self.client.post(
            reverse("auth-refresh"),
            {"refresh": old_refresh},
            format="json",
        )
        self.assertEqual(reused.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_but_rejects_another_users_token(self):
        login = self.login()
        other = create_user("other@example.com")
        other_login = self.client.post(
            reverse("auth-login"),
            {"email": other.email, "password": INITIAL_PASSWORD},
            format="json",
        )
        other_refresh = other_login.data["refresh"]

        mismatch = self.client.post(
            reverse("auth-logout"),
            {"refresh": other_refresh},
            format="json",
        )
        self.assertEqual(mismatch.status_code, status.HTTP_400_BAD_REQUEST)

        logout = self.client.post(
            reverse("auth-logout"),
            {"refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)

        refresh = self.client.post(
            reverse("auth-refresh"),
            {"refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_change_revokes_all_existing_tokens(self):
        login = self.login()
        old_access = login.data["access"]
        old_refresh = login.data["refresh"]

        changed = self.client.post(
            reverse("auth-password-change"),
            {"current_password": INITIAL_PASSWORD, "new_password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(changed.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertEqual(self.user.auth_version, 1)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")
        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(me.data["error"]["code"], "token_revoked")

        self.client.credentials()
        refresh = self.client.post(
            reverse("auth-refresh"),
            {"refresh": old_refresh},
            format="json",
        )
        self.assertEqual(refresh.status_code, status.HTTP_401_UNAUTHORIZED)

        relogin = self.client.post(
            reverse("auth-login"),
            {"email": "student@example.com", "password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(relogin.status_code, status.HTTP_200_OK)

    def test_weak_new_password_is_rejected_without_changing_credentials(self):
        self.login()
        response = self.client.post(
            reverse("auth-password-change"),
            {"current_password": INITIAL_PASSWORD, "new_password": "password12345"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(INITIAL_PASSWORD))
        self.assertEqual(self.user.auth_version, 0)

    def test_health_endpoint_reports_database_and_cache(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["checks"], {"database": "ok", "cache": "ok"})
        self.assertIn("X-Request-ID", response)
