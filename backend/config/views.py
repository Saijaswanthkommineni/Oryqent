"""Unversioned operational endpoints."""

import logging

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger("apps.health")


def health(request):
    checks: dict[str, str] = {}
    healthy = True

    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception:
        healthy = False
        checks["database"] = "error"
        logger.exception("Health check database failure")

    try:
        cache.set("health:probe", "ok", timeout=5)
        if cache.get("health:probe") != "ok":
            raise RuntimeError("Cache probe returned an unexpected value.")
        checks["cache"] = "ok"
    except Exception:
        healthy = False
        checks["cache"] = "error"
        logger.exception("Health check cache failure")

    return JsonResponse(
        {"status": "ok" if healthy else "unhealthy", "checks": checks},
        status=200 if healthy else 503,
    )
