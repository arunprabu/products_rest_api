"""RFC 7807 HTTP error helpers."""

from fastapi import Request
from fastapi.responses import JSONResponse


class NotFoundError(Exception):
    """Requested resource does not exist."""


def problem_response(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str,
) -> JSONResponse:
    """Construct a problem detail response correlated with the request."""
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.url.path,
            "request_id": request_id,
        },
    )
