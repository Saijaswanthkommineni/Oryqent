"""Consistent API error envelopes for all clients."""

from typing import Any

from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

from config.request_context import get_request_id


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    details: Any = None
    if isinstance(data, dict) and "detail" in data:
        message = str(data["detail"])
    elif isinstance(data, dict):
        message = "Request validation failed."
        details = data
    elif isinstance(data, list):
        message = "Request validation failed."
        details = data
    else:
        message = str(data)

    code = getattr(exc, "default_code", "error")
    if isinstance(exc, APIException):
        code = exc.default_code
        detail_code = getattr(exc.detail, "code", None)
        if detail_code:
            code = detail_code

    response.data = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "request_id": get_request_id(),
    }
    request_id = get_request_id()
    if request_id:
        response["X-Request-ID"] = request_id
    return response
