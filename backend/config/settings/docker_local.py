"""Local Docker Compose profile. Not a production deployment profile."""

from config.settings.production import *  # noqa: F403

# The local Compose stack terminates plain HTTP on Nginx; production deployments must
# use config.settings.production behind a TLS-terminating reverse proxy or load balancer.
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
