"""Sumsub KYC integration — backend service wrapper.

Sumsub is our institutional-pilot KYC/AML provider. This module wraps
the four API operations we actually need:

  1. `create_or_get_applicant` — idempotent applicant creation. If we
     already have an applicant for this user, returns the existing one
     (Sumsub returns 409 with the existing applicantId).
  2. `generate_access_token` — short-lived (default 30 min) WebSDK
     token. The frontend embeds it in the Sumsub iframe.
  3. `get_applicant_status` — read current review state.
  4. `verify_webhook_signature` — HMAC-SHA-256 verification on the
     raw bytes of an incoming webhook payload.

Auth model (per Sumsub docs):

  Every API request is signed with three headers:

      X-App-Token:        <SUMSUB_APP_TOKEN>
      X-App-Access-Sig:   HMAC-SHA-256(secret, ts + method + path + body) hex
      X-App-Access-Ts:    <unix-timestamp>

  The webhook secret is a SEPARATE shared secret (different env var):
  Sumsub puts the digest in `X-Payload-Digest`.

Graceful degradation:

  When the application starts without `SUMSUB_APP_TOKEN` set, we
  refuse to construct a `SumsubService` at all (raises ValueError).
  The factory in main.py catches that and stores `None` in app state;
  endpoints raise HTTP 503 cleanly instead of 5xx-ing on missing creds.
  Pilot setup is then: paste env vars → redeploy backend → KYC works.

Reference: https://developers.sumsub.com/api-reference/
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger("orgon.sumsub")


class SumsubError(Exception):
    """Wraps any Sumsub-side error (network, 4xx, 5xx) for caller handling."""

    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class SumsubService:
    """Thin async client over the Sumsub REST API.

    Construct via the `build_sumsub_service()` factory rather than
    directly — the factory enforces the graceful-degradation contract
    described in the module docstring.
    """

    DEFAULT_BASE_URL = "https://api.sumsub.com"
    DEFAULT_LEVEL = "basic-kyc-level"
    DEFAULT_TOKEN_TTL = 1800  # 30 minutes — Sumsub-recommended default

    def __init__(
        self,
        app_token: str,
        secret_key: str,
        webhook_secret: str,
        level_name: str | None = None,
        base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ):
        if not app_token:
            raise ValueError("SumsubService requires non-empty app_token")
        if not secret_key:
            raise ValueError("SumsubService requires non-empty secret_key")
        if not webhook_secret:
            raise ValueError("SumsubService requires non-empty webhook_secret")

        self._app_token = app_token
        self._secret_key = secret_key.encode("utf-8")
        self._webhook_secret = webhook_secret.encode("utf-8")
        self._level_name = level_name or self.DEFAULT_LEVEL
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        # Keep the client injectable for tests; default to a lazily-built one.
        self._client = http_client

    @property
    def level_name(self) -> str:
        return self._level_name

    # ────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────

    async def create_or_get_applicant(
        self,
        external_user_id: str,
        level_name: str | None = None,
    ) -> dict[str, Any]:
        """Create a Sumsub applicant or return the existing one.

        Sumsub uses `externalUserId` as our caller-supplied de-dup key.
        Calling create twice with the same externalUserId returns
        409 with the existing applicantId — we treat that as success
        and look up via `GET /applicants/-;externalUserId={id}`.

        Args:
            external_user_id: stable identifier we control. Recommended
                form: f"orgon-user-{user.id}".
            level_name: override the default level (e.g. for KYB later).
                Defaults to instance's `level_name`.

        Returns:
            Sumsub applicant dict — at minimum {`id`, `externalUserId`,
            `review.reviewStatus`}.

        Raises:
            SumsubError on any non-conflict failure.
        """
        target_level = level_name or self._level_name
        body = {
            "externalUserId": external_user_id,
            "type": "individual",
        }
        path = f"/resources/applicants?levelName={target_level}"
        try:
            return await self._request("POST", path, body=body)
        except SumsubError as exc:
            if exc.status_code == 409:
                # Existing applicant — fetch and return.
                logger.info(
                    "Sumsub applicant for externalUserId=%s already exists, fetching",
                    external_user_id,
                )
                return await self.get_applicant_by_external_id(external_user_id)
            raise

    async def get_applicant_by_external_id(self, external_user_id: str) -> dict[str, Any]:
        """Sumsub's `GET /resources/applicants/-;externalUserId={id}` lookup."""
        path = f"/resources/applicants/-;externalUserId={external_user_id}/one"
        return await self._request("GET", path)

    async def get_applicant_status(self, applicant_id: str) -> dict[str, Any]:
        """Read full applicant status object."""
        path = f"/resources/applicants/{applicant_id}/status"
        return await self._request("GET", path)

    async def generate_access_token(
        self,
        external_user_id: str,
        level_name: str | None = None,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Short-lived WebSDK token. Frontend embeds it into the iframe.

        Sumsub's API takes externalUserId, NOT applicantId, so the same
        endpoint can also do first-time applicant creation under the
        hood when needed. We always create-or-get separately first
        (so our DB has the applicantId) and then call this to mint the
        SDK token.

        Returns:
            {"token": "_act-...", "userId": externalUserId}
        """
        target_level = level_name or self._level_name
        ttl = ttl_seconds or self.DEFAULT_TOKEN_TTL
        path = (
            f"/resources/accessTokens?userId={external_user_id}"
            f"&levelName={target_level}&ttlInSecs={ttl}"
        )
        # Sumsub doc says POST, with empty body, signed.
        return await self._request("POST", path, body=None)

    def verify_webhook_signature(self, raw_body: bytes, signature_hex: str) -> bool:
        """HMAC-SHA-256 of raw bytes with webhook_secret matches header?

        Use a constant-time comparison to avoid timing-side-channel
        leakage of the expected signature.
        """
        if not signature_hex:
            return False
        expected = hmac.new(self._webhook_secret, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_hex.lower())

    # ────────────────────────────────────────────────────────────────
    # Internals
    # ────────────────────────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sign + send a single request to Sumsub.

        Returns the parsed JSON body on 2xx. Raises `SumsubError` on
        4xx (except 409 which the caller decides what to do with) and
        5xx.
        """
        ts = str(int(time.time()))
        # body bytes for signature MUST be the exact bytes we send.
        if body is None:
            body_bytes = b""
        else:
            import json
            # Compact form to match what httpx sends. We could also use
            # json.dumps(body, separators=(",", ":")) — but httpx also
            # uses compact JSON, so consistency is fine.
            body_bytes = json.dumps(body, separators=(",", ":")).encode("utf-8")

        signature = self._sign_request(method, path, ts, body_bytes)

        headers = {
            "X-App-Token": self._app_token,
            "X-App-Access-Sig": signature,
            "X-App-Access-Ts": ts,
            "Accept": "application/json",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"

        url = f"{self._base_url}{path}"

        client = self._client or httpx.AsyncClient(timeout=10.0)
        owned_client = self._client is None
        try:
            response = await client.request(
                method,
                url,
                content=body_bytes if body is not None else None,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise SumsubError(f"Sumsub HTTP transport error: {exc}") from exc
        finally:
            if owned_client:
                await client.aclose()

        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise SumsubError(
                f"Sumsub {method} {path} → {response.status_code}",
                status_code=response.status_code,
                body=detail,
            )

        try:
            return response.json()
        except Exception as exc:
            raise SumsubError(
                f"Sumsub {method} {path} returned non-JSON body"
            ) from exc

    def _sign_request(
        self,
        method: str,
        path: str,
        ts: str,
        body_bytes: bytes,
    ) -> str:
        """HMAC-SHA-256(secret, ts + method + path + body) hex."""
        message = ts.encode("utf-8") + method.upper().encode("utf-8") + path.encode("utf-8") + body_bytes
        return hmac.new(self._secret_key, message, hashlib.sha256).hexdigest()


# ────────────────────────────────────────────────────────────────────
# Factory + dependency
# ────────────────────────────────────────────────────────────────────


def build_sumsub_service(
    app_token: str | None,
    secret_key: str | None,
    webhook_secret: str | None,
    level_name: str | None = None,
    base_url: str | None = None,
) -> SumsubService | None:
    """Construct a `SumsubService` if all three secrets are present.

    Returns None when any of the three is empty/missing, so the rest
    of the application can detect "Sumsub not configured" without
    hard-failing on startup. Endpoints depending on the service then
    raise HTTPException(503) — the documented disabled-mode behavior
    matching how Stripe wires up.
    """
    if not (app_token and secret_key and webhook_secret):
        logger.info(
            "Sumsub disabled: %s",
            ", ".join(
                name
                for name, val in (
                    ("SUMSUB_APP_TOKEN", app_token),
                    ("SUMSUB_SECRET_KEY", secret_key),
                    ("SUMSUB_WEBHOOK_SECRET", webhook_secret),
                )
                if not val
            ),
        )
        return None

    service = SumsubService(
        app_token=app_token,
        secret_key=secret_key,
        webhook_secret=webhook_secret,
        level_name=level_name,
        base_url=base_url,
    )
    logger.info(
        "Sumsub enabled: level=%s base=%s",
        service.level_name,
        service._base_url,
    )
    return service
