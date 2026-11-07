"""Production settings. Fail closed when required security configuration is absent."""

from django.core.exceptions import ImproperlyConfigured

from config.env import env, env_list
from config.settings.base import *  # noqa: F403
from config.settings.base import (
    CORS_ALLOWED_ORIGINS,
    CSRF_TRUSTED_ORIGINS,
    DATABASES,
    REDIS_URL,
)

DEBUG = False

_PLACEHOLDER_MARKERS = ("replace-with", "change-me", "changeme")


def _contains_placeholder(value: str) -> bool:
    normalized = value.casefold()
    return any(marker in normalized for marker in _PLACEHOLDER_MARKERS)


if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production requires DB_ENGINE=postgresql.")
if not REDIS_URL:
    raise ImproperlyConfigured("Production requires REDIS_URL for shared throttling/cache state.")

secret_key = env("DJANGO_SECRET_KEY") or ""
if (
    len(secret_key) < 50
    or len(set(secret_key)) < 5
    or secret_key.casefold().startswith("django-insecure-")
    or _contains_placeholder(secret_key)
):
    raise ImproperlyConfigured(
        "Production requires DJANGO_SECRET_KEY to be a random value of at least 50 characters."
    )

configured_hosts = env_list("DJANGO_ALLOWED_HOSTS")
if not configured_hosts:
    raise ImproperlyConfigured("Production requires DJANGO_ALLOWED_HOSTS.")
if "*" in configured_hosts:
    raise ImproperlyConfigured("Production does not allow a wildcard DJANGO_ALLOWED_HOSTS entry.")

database_password = DATABASES["default"]["PASSWORD"] or ""
if _contains_placeholder(database_password):
    raise ImproperlyConfigured(
        "Production requires a real POSTGRES_PASSWORD, not a template value."
    )

if "*" in CORS_ALLOWED_ORIGINS or "*" in CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured("Production does not allow wildcard CORS or CSRF origins.")

# The reverse proxy must strip untrusted forwarding headers and set these itself.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
