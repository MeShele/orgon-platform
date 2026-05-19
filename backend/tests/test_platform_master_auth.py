"""Platform master-key auth middleware contract.

The middleware gates `/platform/*` behind a bearer token compared
against `ORGON_PLATFORM_MASTER_KEY`. Failure modes are deliberate:
- env missing → 503 (visible deploy-config issue, not 500)
- header missing/malformed → 401
- token mismatch → 401 with no hint about which side is wrong

These tests exercise `PlatformMasterAuthMiddleware.dispatch` directly
with a stub Request + capture call_next — no Starlette TestClient
needed, so the suite runs anywhere `starlette` is importable as a
dependency of `fastapi` (no extra dev-dep, no live HTTP).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Optional

import pytest

from backend.api.middleware_platform_master import PlatformMasterAuthMiddleware


def _make_request(*, path: str, headers: Optional[dict] = None):
    """Construct a minimal Request-like object the middleware reads.

    The middleware only touches `.url.path`, `.headers.get(...)`, and
    `.state` — so a SimpleNamespace covers it. Avoids importing
    Starlette's full Request which would require app context.
    """
    return SimpleNamespace(
        url=SimpleNamespace(path=path),
        headers=_HeadersDict(headers or {}),
        state=SimpleNamespace(),
    )


class _HeadersDict:
    """Case-insensitive header dict matching Starlette's contract."""

    def __init__(self, src: dict):
        self._d = {k.lower(): v for k, v in src.items()}

    def get(self, key: str, default=None):
        return self._d.get(key.lower(), default)


async def _dummy_call_next(request):
    """Pretend handler — returns a marker payload so tests can verify
    pass-through. Sets a 'reached=true' attr we read later."""
    from starlette.responses import Response
    body = json.dumps({
        "reached": True,
        "master_flag": getattr(request.state, "platform_master", False),
    })
    return Response(body, status_code=200, media_type="application/json")


async def _invoke(middleware, request):
    """Run middleware.dispatch and return (status, body_dict)."""
    resp = await middleware.dispatch(request, _dummy_call_next)
    # Response.body is bytes for sync Response, async for streaming.
    raw = resp.body if hasattr(resp, "body") else b""
    try:
        body = json.loads(raw.decode()) if raw else {}
    except Exception:
        body = {}
    return resp.status_code, body


@pytest.fixture
def middleware():
    # Starlette middleware init signature requires `app` — pass a noop.
    return PlatformMasterAuthMiddleware(app=lambda *a, **k: None)


@pytest.mark.asyncio
async def test_env_unset_returns_503(monkeypatch, middleware):
    monkeypatch.delenv("ORGON_PLATFORM_MASTER_KEY", raising=False)
    status, body = await _invoke(middleware, _make_request(path="/platform/echo"))
    assert status == 503
    assert "ORGON_PLATFORM_MASTER_KEY" in body["error"]


@pytest.mark.asyncio
async def test_no_bearer_header_returns_401(monkeypatch, middleware):
    monkeypatch.setenv("ORGON_PLATFORM_MASTER_KEY", "correct-secret")
    status, body = await _invoke(middleware, _make_request(path="/platform/echo"))
    assert status == 401
    assert "Bearer token required" in body["error"]


@pytest.mark.asyncio
async def test_malformed_bearer_returns_401(monkeypatch, middleware):
    monkeypatch.setenv("ORGON_PLATFORM_MASTER_KEY", "correct-secret")
    status, body = await _invoke(
        middleware,
        _make_request(path="/platform/echo", headers={"Authorization": "Basic abc:def"}),
    )
    assert status == 401


@pytest.mark.asyncio
async def test_empty_bearer_returns_401(monkeypatch, middleware):
    monkeypatch.setenv("ORGON_PLATFORM_MASTER_KEY", "correct-secret")
    status, _ = await _invoke(
        middleware,
        _make_request(path="/platform/echo", headers={"Authorization": "Bearer "}),
    )
    assert status == 401


@pytest.mark.asyncio
async def test_wrong_token_returns_401_no_hint(monkeypatch, middleware):
    """The 401 message must not say 'wrong token' vs 'wrong env' — that
    would let an attacker probe which side is misconfigured."""
    monkeypatch.setenv("ORGON_PLATFORM_MASTER_KEY", "correct-secret")
    status, body = await _invoke(
        middleware,
        _make_request(path="/platform/echo", headers={"Authorization": "Bearer wrong-token"}),
    )
    assert status == 401
    assert body["error"] == "Unauthorized"


@pytest.mark.asyncio
async def test_correct_token_passes_through_and_sets_state(monkeypatch, middleware):
    monkeypatch.setenv("ORGON_PLATFORM_MASTER_KEY", "correct-secret")
    status, body = await _invoke(
        middleware,
        _make_request(path="/platform/echo", headers={"Authorization": "Bearer correct-secret"}),
    )
    assert status == 200
    assert body["reached"] is True
    assert body["master_flag"] is True


@pytest.mark.asyncio
async def test_non_platform_prefix_is_passthrough(monkeypatch, middleware):
    """Middleware MUST NOT gate /api/* or /v1/* — those have their own auth.
    No env set, no bearer header — and yet both must pass through cleanly."""
    monkeypatch.delenv("ORGON_PLATFORM_MASTER_KEY", raising=False)
    for path in ("/api/echo", "/v1/echo", "/health", "/"):
        status, body = await _invoke(middleware, _make_request(path=path))
        assert status == 200, f"path {path} should be passthrough, got {status}"
        assert body["reached"] is True


@pytest.mark.asyncio
async def test_constant_time_compare_no_length_leak(monkeypatch, middleware):
    """Two wrong tokens of vastly different lengths must produce
    identical error responses — no early-exit length information leak."""
    monkeypatch.setenv("ORGON_PLATFORM_MASTER_KEY", "correct-secret")
    s_short, b_short = await _invoke(
        middleware,
        _make_request(path="/platform/echo", headers={"Authorization": "Bearer x"}),
    )
    s_long, b_long = await _invoke(
        middleware,
        _make_request(path="/platform/echo", headers={"Authorization": "Bearer " + "x" * 200}),
    )
    assert s_short == s_long == 401
    assert b_short == b_long
