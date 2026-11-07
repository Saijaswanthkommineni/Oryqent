import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

BACKEND_DIR = Path(__file__).resolve().parents[2]
STRONG_SECRET = "A-strong-production-secret-with-more-than-fifty-characters-123456789"


class ProductionSettingsTests(SimpleTestCase):
    def _load_production_settings(self, **overrides: str) -> subprocess.CompletedProcess:
        environment = {
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "DJANGO_SECRET_KEY": STRONG_SECRET,
            "DJANGO_ALLOWED_HOSTS": "example.com",
            "DB_ENGINE": "postgresql",
            "POSTGRES_DB": "oryqent",
            "POSTGRES_USER": "oryqent",
            "POSTGRES_PASSWORD": "strong-database-password",
            "REDIS_URL": "redis://localhost:6379/1",
            "CORS_ALLOWED_ORIGINS": "https://app.example.com",
            "CSRF_TRUSTED_ORIGINS": "https://app.example.com",
        }
        environment.update(overrides)
        return subprocess.run(
            [sys.executable, "-c", "import django; django.setup()"],
            cwd=BACKEND_DIR,
            env={**os.environ, **environment},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def test_valid_configuration_loads(self):
        result = self._load_production_settings()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_placeholder_secret_is_rejected(self):
        result = self._load_production_settings(
            DJANGO_SECRET_KEY="replace-with-at-least-50-random-characters"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_short_secret_is_rejected(self):
        result = self._load_production_settings(DJANGO_SECRET_KEY="too-short")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("at least 50 characters", result.stderr)

    def test_wildcard_allowed_hosts_are_rejected(self):
        result = self._load_production_settings(DJANGO_ALLOWED_HOSTS="*")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("wildcard DJANGO_ALLOWED_HOSTS", result.stderr)

    def test_placeholder_database_password_is_rejected(self):
        result = self._load_production_settings(
            POSTGRES_PASSWORD="replace-with-a-strong-database-password"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("POSTGRES_PASSWORD", result.stderr)

    def test_wildcard_cors_origin_is_rejected(self):
        result = self._load_production_settings(CORS_ALLOWED_ORIGINS="*")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("wildcard CORS", result.stderr)
