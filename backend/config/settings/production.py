"""Production settings. Fail closed when required security configuration is absent."""

from django.core.exceptions import ImproperlyConfigured

from config.env import env, env_list
from config.settings.base import *  # noqa: F403
from config.settings.base import DATABASES, REDIS_URL

DEBUG = False

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production requires DB_ENGINE=postgresql.")
if not REDIS_URL:
    raise ImproperlyConfigured("Production requires REDIS_URL for shared throttling/cache state.")
if not env("DJANGO_SECRET_KEY"):
    raise ImproperlyConfigured("Production requires DJANGO_SECRET_KEY.")
if not env_list("DJANGO_ALLOWED_HOSTS"):
    raise ImproperlyConfigured("Production requires DJANGO_ALLOWED_HOSTS.")

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
