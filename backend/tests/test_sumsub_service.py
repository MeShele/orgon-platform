"""Unit tests for `SumsubService`.

We mock `httpx.AsyncClient` directly via a small in-memory fake so
tests don't depend on external network and don't need a real Sumsub
sandbox account. Approach mirrors the in-process fake-KMS pattern
from Wave 18 — exact emulation, deterministic, no extra deps.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx
import pytest

from backend.services.sumsub_service import (
    SumsubError,
    SumsubService,
    build_sumsub_service,
)


# ────────────────────────────────────────────────────────────────────
# Fake httpx client
# ────────────────────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, status_code: int, body: dict | str = ""):
        self.status_code = status_code
        self._body = body
        self.text = body if isinstance(body, str) else json.dumps(body)

    def json(self) -> Any:
        if isinstance(self._body, dict):
            return self._body
        raise ValueError("non-JSON body")


class _FakeAsyncClient:
    """Captures the last request and returns a queued response.

    Set `next_response` before each operation. Inspect `last_request`
    after to assert headers / body / path.
    """

    def __init__(self, default_response: _FakeResponse | None = None):
        self.next_response: _FakeResponse = default_response or _FakeResponse(
            200, {}
        )
        self.last_request: dict[str, Any] | None = None
        self.requests: list[dict[str, Any]] = []

    async def request(
        self,
        method: str,
        url: str,
        content: bytes | None = None,
        headers: dict | None = None,
    ) -> _FakeResponse:
        record = {
            "method": method,
            "url": url,
            "content": content,
            "headers": dict(headers) if headers else {},
        }
        self.last_request = record
        self.requests.append(record)
        return self.next_response

    async def aclose(self) -> None:  # pragma: no cover — we own the lifecycle
        pass


# ────────────────────────────────────────────────────────────────────
# build_sumsub_service factory — graceful degradation
# ────────────────────────────────────────────────────────────────────


def test_factory_returns_none_when_app_token_missing():
    assert build_sumsub_service(None, "sec", "ws") is None


def test_factory_returns_none_when_secret_key_missing():
    assert build_sumsub_service("tok", None, "ws") is None


def test_factory_returns_none_when_webhook_secret_missing():
    assert build_sumsub_service("tok", "sec", None) is None


def test_factory_returns_none_when_all_empty_strings():
    assert build_sumsub_service("", "", "") is None


def test_factory_constructs_service_when_all_set():
    svc = build_sumsub_service("tok", "sec", "ws")
    assert svc is not None
    assert isinstance(svc, SumsubService)
    assert svc.level_name == SumsubService.DEFAULT_LEVEL


def test_factory_honours_custom_level():
    svc = build_sumsub_service("tok", "sec", "ws", level_name="kyb-level")
    assert svc is not None
    assert svc.level_name == "kyb-level"


def test_constructor_rejects_empty_app_token():
    with pytest.raises(ValueError, match="non-empty app_token"):
        SumsubService("", "sec", "ws")


def test_constructor_rejects_empty_secret():
    with pytest.raises(ValueError, match="non-empty secret_key"):
        SumsubService("tok", "", "ws")


def test_constructor_rejects_empty_webhook_secret():
    with pytest.raises(ValueError, match="non-empty webhook_secret"):
        SumsubService("tok", "sec", "")


# ────────────────────────────────────────────────────────────────────
# Webhook signature verification
# ────────────────────────────────────────────────────────────────────


def test_verify_webhook_signature_accepts_valid():
    svc = SumsubService("tok", "sec", "wsecret")
    body = b'{"applicant":"123"}'
    sig = hmac.new(b"wsecret", body, hashlib.sha256).hexdigest()
    assert svc.verify_webhook_signature(body, sig) is True


def test_verify_webhook_signature_rejects_tampered_body():
    svc = SumsubService("tok", "sec", "wsecret")
    body = b'{"applicant":"123"}'
    sig = hmac.new(b"wsecret", body, hashlib.sha256).hexdigest()
    assert svc.verify_webhook_signature(body + b"X", sig) is False


def test_verify_webhook_signature_rejects_wrong_secret():
    svc = SumsubService("tok", "sec", "wsecret")
    body = b'{"applicant":"123"}'
    bad_sig = hmac.new(b"different-secret", body, hashlib.sha256).hexdigest()
    assert svc.verify_webhook_signature(body, bad_sig) is False


def test_verify_webhook_signature_rejects_empty_signature():
    svc = SumsubService("tok", "sec", "wsecret")
    assert svc.verify_webhook_signature(b"anything", "") is False


def test_verify_webhook_signature_case_insensitive_hex():
    """Sumsub may emit upper-case hex; HMAC verify must accept it."""
    svc = SumsubService("tok", "sec", "wsecret")
    body = b'{"applicant":"123"}'
    sig = hmac.new(b"wsecret", body, hashlib.sha256).hexdigest().upper()
    assert svc.verify_webhook_signature(body, sig) is True


# ────────────────────────────────────────────────────────────────────
# Request signing — header layout per Sumsub doc
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_request_includes_required_headers():
    fake = _FakeAsyncClient(_FakeResponse(200, {"ok": True}))
    svc = SumsubService("tok", "sec", "ws", http_client=fake)
    await svc._request("GET", "/resources/applicants/abc/status")
    headers = fake.last_request["headers"]
    assert headers["X-App-Token"] == "tok"
    assert "X-App-Access-Sig" in headers
    assert "X-App-Access-Ts" in headers
    assert len(headers["X-App-Access-Sig"]) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_request_signature_matches_doc_formula():
    """Signature == HMAC-SHA-256(secret, ts + method + path + body)."""
    fake = _FakeAsyncClient(_FakeResponse(200, {}))
    svc = SumsubService("tok", "secret-key", "ws", http_client=fake)
    await svc._request("POST", "/resources/foo", body={"a": 1})
    headers = fake.last_request["headers"]
    ts = headers["X-App-Access-Ts"]
    sig = headers["X-App-Access-Sig"]
    body_bytes = json.dumps({"a": 1}, separators=(",", ":")).encode("utf-8")
    expected = hmac.new(
        b"secret-key",
        ts.encode("utf-8") + b"POST" + b"/resources/foo" + body_bytes,
        hashlib.sha256,
    ).hexdigest()
    assert sig == expected


# ────────────────────────────────────────────────────────────────────
# create_or_get_applicant
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_or_get_applicant_returns_new_on_201():
    fake = _FakeAsyncClient(
        _FakeResponse(201, {"id": "applicant-abc", "externalUserId": "orgon-user-1"})
    )
    svc = SumsubService("tok", "sec", "ws", http_client=fake)
    result = await svc.create_or_get_applicant("orgon-user-1")
    assert result["id"] == "applicant-abc"
    # Right method + path with default level
    assert fake.last_request["method"] == "POST"
    assert "levelName=basic-kyc-level" in fake.last_request["url"]


@pytest.mark.asyncio
async def test_create_or_get_applicant_falls_back_to_lookup_on_409():
    """Sumsub 409 means applicant exists → service does follow-up GET."""

    class _Sequenced(_FakeAsyncClient):
        def __init__(self):
            super().__init__()
            self.responses = [
                _FakeResponse(409, {"description": "Applicant already exists"}),
                _FakeResponse(200, {"id": "existing-id", "externalUserId": "orgon-user-1"}),
            ]
            self.idx = 0

        async def request(self, method, url, content=None, headers=None):
            await super().request(method, url, content=content, headers=headers)
            resp = self.responses[self.idx]
            self.idx += 1
            return resp

    fake = _Sequenced()
    svc = SumsubService("tok", "sec", "ws", http_client=fake)
    result = await svc.create_or_get_applicant("orgon-user-1")
    assert result["id"] == "existing-id"
    # Two requests: POST then GET
    assert fake.idx == 2
    assert fake.requests[0]["method"] == "POST"
    assert fake.requests[1]["method"] == "GET"
    assert "externalUserId=orgon-user-1" in fake.requests[1]["url"]


@pytest.mark.asyncio
async def test_create_or_get_applicant_propagates_other_errors():
    fake = _FakeAsyncClient(_FakeResponse(500, {"description": "internal"}))
    svc = SumsubService("tok", "sec", "ws", http_client=fake)
    with pytest.raises(SumsubError) as exc:
        await svc.create_or_get_applicant("orgon-user-1")
    assert exc.value.status_code == 500


# ────────────────────────────────────────────────────────────────────
# generate_access_token
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_access_token_calls_correct_endpoint():
    fake = _FakeAsyncClient(_FakeResponse(200, {"token": "_act-abc"}))
    svc = SumsubService("tok", "sec", "ws", http_client=fake)
    result = await svc.generate_access_token("orgon-user-1")
    assert result["token"] == "_act-abc"
    url = fake.last_request["url"]
    assert "/resources/accessTokens" in url
    assert "userId=orgon-user-1" in url
    assert "levelName=basic-kyc-level" in url
    assert "ttlInSecs=1800" in url
    assert fake.last_request["method"] == "POST"


@pytest.mark.asyncio
async def test_generate_access_token_with_custom_ttl():
    fake = _FakeAsyncClient(_FakeResponse(200, {"token": "_act-abc"}))
    svc = SumsubService("tok", "sec", "ws", http_client=fake)
    await svc.generate_access_token("orgon-user-1", ttl_seconds=300)
    assert "ttlInSecs=300" in fake.last_request["url"]


# ────────────────────────────────────────────────────────────────────
# get_applicant_status
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_applicant_status_calls_status_endpoint():
    fake = _FakeAsyncClient(
        _FakeResponse(200, {"reviewStatus": "completed", "reviewResult": {"reviewAnswer": "GREEN"}})
    )
    svc = SumsubService("tok", "sec", "ws", http_client=fake)
    result = await svc.get_applicant_status("applicant-xyz")
    assert result["reviewStatus"] == "completed"
    assert "/resources/applicants/applicant-xyz/status" in fake.last_request["url"]
    assert fake.last_request["method"] == "GET"


# ────────────────────────────────────────────────────────────────────
# Transport error handling
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transport_error_wrapped_as_sumsub_error():
    class _FailingClient(_FakeAsyncClient):
        async def request(self, *a, **kw):
            raise httpx.ConnectError("connection refused")

    fake = _FailingClient()
    svc = SumsubService("tok", "sec", "ws", http_client=fake)
    with pytest.raises(SumsubError, match="HTTP transport error"):
        await svc.get_applicant_status("any-id")


@pytest.mark.asyncio
async def test_non_json_body_raises_sumsub_error():
    fake = _FakeAsyncClient(_FakeResponse(200, "<html>hi</html>"))
    svc = SumsubService("tok", "sec", "ws", http_client=fake)
    with pytest.raises(SumsubError, match="non-JSON"):
        await svc.get_applicant_status("any-id")
