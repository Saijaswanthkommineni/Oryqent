"""Request correlation middleware."""

import logging
import re
import time
import uuid

from django.http import HttpRequest, HttpResponse

from config.request_context import set_request_id

logger = logging.getLogger("config.request")

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestIDMiddleware:
    """Attach a trusted or generated request identifier to every response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied if _REQUEST_ID_PATTERN.fullmatch(supplied) else uuid.uuid4().hex
        request.request_id = request_id
        set_request_id(request_id)
        started_at = time.perf_counter()
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            logger.info(
                "Request completed",
                extra={
                    "event": "http.request.completed",
                    "status_code": response.status_code,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                },
            )
            return response
        finally:
            set_request_id(None)
