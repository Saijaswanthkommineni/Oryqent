"""Deterministic test settings. No external services are required."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-key-never-used-outside-tests")
os.environ.setdefault("DJANGO_DEBUG", "false")
os.environ.setdefault("DB_ENGINE", "sqlite")
os.environ.setdefault("SQLITE_PATH", ":memory:")

from config.settings.base import *  # noqa: E402,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "login": "10000/min",
    "token_refresh": "10000/min",
    "password_change": "10000/min",
}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
