"""Request-ID and standardized error-shape middleware for /v1/*.

Every public response carries:
    X-Request-Id: <uuid>
so a merchant pasting it into support gets one-shot traceability —
we grep this id across application logs and trace the entire path.

Errors from the /v1/* surface are reshaped into a single envelope:

    {
      "error":   "<machine-readable code>",
      "message": "<human-readable description>",
      "request_id": "<uuid>"
    }

This is what the SDK already expects (see OrgonError) and what
integrators learn from /developers — by going through a single
middleware we keep the contract consistent across every handler,
including pydantic 422s and FastAPI default 404s.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("orgon.middleware.request_id")

PUBLIC_PREFIX = "/v1/"

# Map FastAPI/Starlette status codes to canonical machine-readable
# codes. Keep this list narrow — new codes go in the catalogue at
# /developers#errors so integrators don't have to grep our source.
_STATUS_TO_CODE = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    501: "not_implemented",
    502: "upstream_error",
    503: "service_unavailable",
    504: "upstream_timeout",
}


class RequestIdAndErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        response.headers["X-Request-Id"] = request_id

        # Only reshape errors for /v1/* — internal/UI routes have
        # their own legacy shapes we shouldn't disrupt.
        if (
            request.url.path.startswith(PUBLIC_PREFIX)
            and response.status_code >= 400
        ):
            response = await _rewrap_error(response, request_id)

        # Structured log line + Prometheus metrics for every /v1/* hit.
        if request.url.path.startswith(PUBLIC_PREFIX):
            logger.info(
                "public_api method=%s path=%s status=%s ms=%s req_id=%s",
                request.method, request.url.path, response.status_code,
                elapsed_ms, request_id,
            )
            try:
                from backend.services.metrics_service import (
                    b2b_requests_total,
                    b2b_request_duration_seconds,
                )
                # Use route template, not actual path with ids, so
                # cardinality stays bounded. Fall back to method+prefix
                # when no route matched (e.g. 404).
                tmpl = _route_template(request) or request.url.path
                merchant_label = getattr(request.state, "merchant_id", None) or "unauthenticated"
                b2b_requests_total.labels(
                    merchant_id=merchant_label,
                    endpoint=tmpl,
                    status=str(response.status_code),
                ).inc()
                b2b_request_duration_seconds.labels(endpoint=tmpl).observe(elapsed_ms / 1000.0)
            except Exception:
                # Metrics are best-effort — never fail the request.
                pass

        return response


def _route_template(request: Request) -> str | None:
    """Return /v1/wallets/{wallet_id} rather than /v1/wallets/abcdef…
    so Prometheus cardinality stays bounded."""
    route = getattr(request.scope.get("route"), "path", None) if request.scope else None
    return route


async def _rewrap_error(resp: Response, request_id: str) -> Response:
    body = b""
    # StreamingResponse via BaseHTTPMiddleware exposes its content
    # through body_iterator; collect it once.
    async for chunk in resp.body_iterator:  # type: ignore[attr-defined]
        body += chunk

    try:
        original = json.loads(body) if body else {}
    except Exception:
        original = {"message": body.decode("utf-8", errors="replace")[:500]}

    code = _STATUS_TO_CODE.get(resp.status_code, "error")
    message = _extract_message(original)

    # If the handler already shaped the body as {error, message},
    # respect it — keeps the existing custom 401 "Bad signature" etc.
    if isinstance(original, dict) and "error" in original and "message" in original:
        envelope = {
            "error": original["error"],
            "message": original["message"],
            "request_id": request_id,
        }
    else:
        envelope = {
            "error": code,
            "message": message,
            "request_id": request_id,
        }
        # FastAPI validation: keep field-level detail under `details`
        # so SDKs can render it precisely.
        if resp.status_code == 422 and isinstance(original, dict) and "detail" in original:
            envelope["details"] = original["detail"]

    new_body = json.dumps(envelope).encode()
    return Response(
        content=new_body,
        status_code=resp.status_code,
        headers={
            **{k: v for k, v in resp.headers.items() if k.lower() not in ("content-length", "content-type")},
            "X-Request-Id": request_id,
        },
        media_type="application/json",
    )


def _extract_message(payload) -> str:
    if isinstance(payload, dict):
        for key in ("message", "detail", "error"):
            v = payload.get(key)
            if isinstance(v, str) and v:
                return v
            if isinstance(v, list) and v:
                # Pydantic 422 case — surface the first message.
                first = v[0]
                if isinstance(first, dict):
                    return first.get("msg") or "validation error"
                return str(first)
    return "request failed"
