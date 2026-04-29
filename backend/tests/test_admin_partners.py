"""Unit tests for routes_admin_partners — direct handler invocation.

We don't spin up the full FastAPI app; we call the async handlers with
a fake request whose app.state carries a mocked PartnerService, and we
patch backend.main.get_database for the org-scope helper.

These tests cover only the route logic — the underlying PartnerService
already has its own coverage. The interesting bits are RBAC scoping
and one-time-secret leakage paths.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from backend.api import routes_admin_partners as ap


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────


def _request(svc) -> SimpleNamespace:
    """Minimal stand-in for FastAPI's Request — only fields the handler reads."""
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(partner_service=svc)))


def _user(role: str = "super_admin", user_id: int = 1) -> dict:
    return {"id": user_id, "email": "test@example", "role": role, "is_active": True}


@pytest.fixture
def svc():
    """Mock PartnerService with the methods the routes call."""
    s = AsyncMock()
    s.create_partner = AsyncMock(return_value={
        "partner_id": "11111111-1111-1111-1111-111111111111",
        "name": "Test", "tier": "starter",
        "ec_address": "0x" + "a" * 40,
        "api_key": "pk_test_abc", "api_secret": "secret_xyz",
        "rate_limit_per_minute": 300,
        "webhook_url": None,
        "created_at": "2026-04-29T12:00:00+00:00",
    })
    s.list_partners = AsyncMock(return_value=[
        {"id": uuid4(), "name": "P1", "tier": "starter", "status": "active",
         "ec_address": "0x" + "1" * 40, "organization_id": UUID("123e4567-e89b-12d3-a456-426614174000"),
         "rate_limit_per_minute": 300, "api_key": "pk_test_aaa",
         "webhook_url": None, "created_at": _ts(), "updated_at": _ts()},
        {"id": uuid4(), "name": "P2", "tier": "free", "status": "active",
         "ec_address": "0x" + "2" * 40, "organization_id": UUID("234e5678-e89b-12d3-a456-426614174111"),
         "rate_limit_per_minute": 60, "api_key": "pk_test_bbb",
         "webhook_url": None, "created_at": _ts(), "updated_at": _ts()},
    ])
    s.get_partner = AsyncMock(return_value={
        "id": UUID("11111111-1111-1111-1111-111111111111"),
        "name": "P1", "tier": "starter", "status": "active",
        "ec_address": "0x" + "1" * 40,
        "organization_id": UUID("123e4567-e89b-12d3-a456-426614174000"),
        "rate_limit_per_minute": 300, "api_key": "pk_test_aaa",
        "webhook_url": None, "created_at": _ts(), "updated_at": _ts(),
    })
    s.rotate_api_key = AsyncMock(return_value={
        "api_key": "pk_test_NEW", "api_secret": "secret_NEW",
        "rotated_at": "2026-04-29T13:00:00+00:00",
    })
    s.suspend_partner = AsyncMock(return_value=None)
    return s


def _ts():
    """Datetime stand-in with isoformat()."""
    from datetime import datetime, timezone
    return datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)


# ────────────────────────────────────────────────────────────────────
# create
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_super_admin_no_org_id_ok(svc):
    """super_admin can create without specifying organization_id."""
    payload = ap.PartnerCreate(name="Test", ec_address="0x" + "a" * 40, tier="starter")
    result = await ap.create_partner(_request(svc), payload, user=_user("super_admin"))
    assert result.api_key == "pk_test_abc"
    assert result.api_secret == "secret_xyz"
    svc.create_partner.assert_called_once()


@pytest.mark.asyncio
async def test_create_company_admin_requires_org_id(svc):
    """company_admin must pass organization_id."""
    payload = ap.PartnerCreate(name="Test Partner", ec_address="0x" + "b" * 40, tier="free")
    with pytest.raises(HTTPException) as exc:
        await ap.create_partner(_request(svc), payload, user=_user("company_admin"))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_company_admin_outside_own_org_forbidden(svc):
    """company_admin cannot bind a partner to an org they don't belong to."""
    org_their = UUID("99999999-9999-9999-9999-999999999999")
    payload = ap.PartnerCreate(
        name="Test Partner", ec_address="0x" + "c" * 40, tier="free",
        organization_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    )
    fake_db = AsyncMock()
    fake_db.fetch = AsyncMock(return_value=[{"organization_id": org_their}])
    with patch("backend.main.get_database", return_value=fake_db):
        with pytest.raises(HTTPException) as exc:
            await ap.create_partner(_request(svc), payload, user=_user("company_admin"))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_create_value_error_becomes_400(svc):
    """Service-side validation errors surface as 400, not 500."""
    svc.create_partner.side_effect = ValueError("Invalid tier")
    payload = ap.PartnerCreate(name="Test Partner", ec_address="0x" + "d" * 40, tier="starter")
    with pytest.raises(HTTPException) as exc:
        await ap.create_partner(_request(svc), payload, user=_user("super_admin"))
    assert exc.value.status_code == 400


# ────────────────────────────────────────────────────────────────────
# list
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_super_admin_sees_all(svc):
    rows = await ap.list_partners(_request(svc), user=_user("super_admin"))
    assert len(rows) == 2
    svc.list_partners.assert_called_once()


@pytest.mark.asyncio
async def test_list_company_admin_filtered_to_own_org(svc):
    """company_admin only sees partners with matching organization_id."""
    fake_db = AsyncMock()
    fake_db.fetch = AsyncMock(return_value=[
        {"organization_id": UUID("123e4567-e89b-12d3-a456-426614174000")}
    ])
    with patch("backend.main.get_database", return_value=fake_db):
        rows = await ap.list_partners(_request(svc), user=_user("company_admin"))
    assert len(rows) == 1
    assert rows[0].name == "P1"


# ────────────────────────────────────────────────────────────────────
# get single
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_404_when_not_found(svc):
    svc.get_partner.return_value = None
    with pytest.raises(HTTPException) as exc:
        await ap.get_partner(uuid4(), _request(svc), user=_user("super_admin"))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_returns_404_cross_tenant(svc):
    """company_admin requesting a partner in a different org gets 404, not 403.
    Don't leak existence across tenants."""
    fake_db = AsyncMock()
    fake_db.fetch = AsyncMock(return_value=[
        {"organization_id": UUID("99999999-9999-9999-9999-999999999999")}
    ])
    with patch("backend.main.get_database", return_value=fake_db):
        with pytest.raises(HTTPException) as exc:
            await ap.get_partner(uuid4(), _request(svc), user=_user("company_admin"))
    assert exc.value.status_code == 404


# ────────────────────────────────────────────────────────────────────
# rotate
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rotate_returns_new_credentials(svc):
    out = await ap.rotate_partner_key(uuid4(), _request(svc), user=_user("super_admin"))
    assert out.api_key == "pk_test_NEW"
    assert out.api_secret == "secret_NEW"
    svc.rotate_api_key.assert_called_once()


@pytest.mark.asyncio
async def test_rotate_404_when_partner_missing(svc):
    svc.get_partner.return_value = None
    with pytest.raises(HTTPException) as exc:
        await ap.rotate_partner_key(uuid4(), _request(svc), user=_user("super_admin"))
    assert exc.value.status_code == 404
    svc.rotate_api_key.assert_not_called()


# ────────────────────────────────────────────────────────────────────
# revoke
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_calls_suspend_with_reason(svc):
    pid = uuid4()
    await ap.revoke_partner(pid, _request(svc), reason="Key leaked",
                            user=_user("super_admin"))
    svc.suspend_partner.assert_called_once_with(str(pid), "Key leaked")


@pytest.mark.asyncio
async def test_revoke_default_reason_when_omitted(svc):
    pid = uuid4()
    await ap.revoke_partner(pid, _request(svc), reason=None,
                            user=_user("super_admin"))
    args = svc.suspend_partner.call_args.args
    assert args[0] == str(pid)
    assert "admin" in args[1].lower()


@pytest.mark.asyncio
async def test_revoke_404_when_missing(svc):
    svc.get_partner.return_value = None
    with pytest.raises(HTTPException) as exc:
        await ap.revoke_partner(uuid4(), _request(svc), user=_user("super_admin"))
    assert exc.value.status_code == 404


# ────────────────────────────────────────────────────────────────────
# Service unavailable
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_503_when_partner_service_not_initialised():
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    payload = ap.PartnerCreate(name="Test Partner", ec_address="0x" + "e" * 40, tier="free")
    with pytest.raises(HTTPException) as exc:
        await ap.create_partner(req, payload, user=_user("super_admin"))
    assert exc.value.status_code == 503
