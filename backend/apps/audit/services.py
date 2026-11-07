import ipaddress
import logging
from typing import Any

from django.http import HttpRequest

from apps.audit.models import AuditLog
from config.request_context import get_request_id

logger = logging.getLogger("apps.audit")


def _client_ip(request: HttpRequest | None) -> str | None:
    if request is None:
        return None
    raw_address = request.META.get("REMOTE_ADDR")
    if not raw_address:
        return None
    try:
        return str(ipaddress.ip_address(raw_address))
    except ValueError:
        return None


def record_event(
    *,
    action: str,
    actor,
    institution=None,
    target_type: str,
    target_id: str,
    metadata: dict[str, Any] | None = None,
    request: HttpRequest | None = None,
) -> AuditLog:
    """Persist a security-relevant administrative event. Never pass secrets here."""

    event = AuditLog.objects.create(
        action=action,
        actor=actor,
        institution=institution,
        target_type=target_type,
        target_id=str(target_id),
        metadata=metadata or {},
        ip_address=_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:512] if request else ""),
        request_id=(getattr(request, "request_id", "") if request else "")
        or (get_request_id() or ""),
    )
    logger.info(
        "Administrative audit event recorded",
        extra={
            "event": action,
            "actor_id": str(actor.pk) if actor else None,
            "institution_id": str(institution.pk) if institution else None,
        },
    )
    return event
