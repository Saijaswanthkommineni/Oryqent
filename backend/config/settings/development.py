"""Local development settings: SQLite, ephemeral secret, verbose errors."""

import os

os.environ.setdefault("DJANGO_DEBUG", "true")

from config.settings.base import *  # noqa: E402,F403
from config.settings.base import env_list  # noqa: E402

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "[::1]"])
