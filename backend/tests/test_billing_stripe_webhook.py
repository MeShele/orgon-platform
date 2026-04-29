"""Unit tests for the Stripe webhook dispatcher and BillingService glue.

We exercise routes_billing.stripe_webhook directly with a fake Request +
a mocked BillingService, matching the pattern in test_admin_partners.py.
The signature verification is patched so we don't need a live secret —
we're testing the *dispatch* logic, not stripe.Webhook itself.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from backend.api import routes_billing as rb


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────


def _request(body: bytes = b"{}", sig: str = "t=1,v1=x") -> SimpleNamespace:
    """Minimal stand-in for FastAPI's Request — just .body() + headers."""
    async def _body():
        return body
    return SimpleNamespace(
        body=_body,
        headers={"stripe-signature": sig},
        app=SimpleNamespace(state=SimpleNamespace()),
    )


def _stripe_svc(configured: bool = True):
    """Mock get_stripe_service() return."""
    s = SimpleNamespace(configured=configured)
    s.verify_webhook = lambda payload, sig: getattr(_stripe_svc, "_event", {})
    return s


def _billing(method_returns: dict | None = None):
    """Build an AsyncMock BillingService with the methods the route calls."""
    svc = SimpleNamespace()
    method_returns = method_returns or {}
    svc.upsert_subscription_from_checkout = AsyncMock(
        return_value=method_returns.get("upsert", {"id": "ok"})
    )
    svc.update_subscription_status_by_stripe_id = AsyncMock(
        return_value=method_returns.get("update", {"id": "ok"})
    )
    svc.mark_invoice_past_due_by_stripe_id = AsyncMock(
        return_value=method_returns.get("past_due", {"id": "ok"})
    )
    return svc


# ────────────────────────────────────────────────────────────────────
# checkout.session.completed
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_checkout_completed_activates_subscription():
    org = str(uuid4())
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_test_1",
            "subscription": "sub_test_1",
            "customer": "cus_test_1",
            "client_reference_id": org,
            "metadata": {
                "organization_id": org,
                "plan_slug": "basic",
                "billing_cycle": "monthly",
            },
        }},
    }
    svc = _stripe_svc(); svc.verify_webhook = lambda *_: event
    bsvc = _billing()
    with patch.object(rb, "get_stripe_service", return_value=svc):
        out = await rb.stripe_webhook(_request(), billing_service=bsvc)
    assert out["handled"] is True
    bsvc.upsert_subscription_from_checkout.assert_called_once()
    kwargs = bsvc.upsert_subscription_from_checkout.call_args.kwargs
    assert str(kwargs["organization_id"]) == org
    assert kwargs["plan_slug"] == "basic"
    assert kwargs["billing_cycle"] == "monthly"
    assert kwargs["stripe_subscription_id"] == "sub_test_1"
    assert kwargs["stripe_customer_id"] == "cus_test_1"


@pytest.mark.asyncio
async def test_checkout_completed_skips_when_subscription_missing():
    """Some Stripe modes don't carry a subscription — don't crash, just no-op."""
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_x", "metadata": {"organization_id": str(uuid4())}}},
    }
    svc = _stripe_svc(); svc.verify_webhook = lambda *_: event
    bsvc = _billing()
    with patch.object(rb, "get_stripe_service", return_value=svc):
        out = await rb.stripe_webhook(_request(), billing_service=bsvc)
    assert out["handled"] is False
    bsvc.upsert_subscription_from_checkout.assert_not_called()


@pytest.mark.asyncio
async def test_checkout_completed_unknown_plan_slug_returns_unhandled():
    org = str(uuid4())
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_x", "subscription": "sub_x", "customer": "cus_x",
            "metadata": {"organization_id": org, "plan_slug": "nope", "billing_cycle": "monthly"},
        }},
    }
    svc = _stripe_svc(); svc.verify_webhook = lambda *_: event
    bsvc = _billing(method_returns={"upsert": None})  # service can't resolve plan
    with patch.object(rb, "get_stripe_service", return_value=svc):
        out = await rb.stripe_webhook(_request(), billing_service=bsvc)
    assert out["handled"] is False


# ────────────────────────────────────────────────────────────────────
# customer.subscription.updated / .deleted
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_subscription_updated_mirrors_status():
    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_u", "status": "past_due"}},
    }
    svc = _stripe_svc(); svc.verify_webhook = lambda *_: event
    bsvc = _billing()
    with patch.object(rb, "get_stripe_service", return_value=svc):
        out = await rb.stripe_webhook(_request(), billing_service=bsvc)
    assert out["handled"] is True
    bsvc.update_subscription_status_by_stripe_id.assert_called_once_with(
        stripe_subscription_id="sub_u", stripe_status="past_due",
    )


@pytest.mark.asyncio
async def test_subscription_deleted_forces_cancelled():
    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_d", "status": "active"}},  # status irrelevant
    }
    svc = _stripe_svc(); svc.verify_webhook = lambda *_: event
    bsvc = _billing()
    with patch.object(rb, "get_stripe_service", return_value=svc):
        await rb.stripe_webhook(_request(), billing_service=bsvc)
    bsvc.update_subscription_status_by_stripe_id.assert_called_once_with(
        stripe_subscription_id="sub_d", stripe_status="canceled",
    )


# ────────────────────────────────────────────────────────────────────
# invoice.payment_failed
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invoice_payment_failed_marks_past_due():
    event = {
        "type": "invoice.payment_failed",
        "data": {"object": {"id": "in_x", "subscription": "sub_pf"}},
    }
    svc = _stripe_svc(); svc.verify_webhook = lambda *_: event
    bsvc = _billing()
    with patch.object(rb, "get_stripe_service", return_value=svc):
        out = await rb.stripe_webhook(_request(), billing_service=bsvc)
    assert out["handled"] is True
    bsvc.mark_invoice_past_due_by_stripe_id.assert_called_once_with(
        stripe_subscription_id="sub_pf",
    )


# ────────────────────────────────────────────────────────────────────
# Failure modes — never 5xx
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handler_exception_swallowed_returns_received():
    """If a handler raises, we still ack so Stripe doesn't retry-storm."""
    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_boom", "status": "active"}},
    }
    svc = _stripe_svc(); svc.verify_webhook = lambda *_: event
    bsvc = _billing()
    bsvc.update_subscription_status_by_stripe_id.side_effect = RuntimeError("DB down")
    with patch.object(rb, "get_stripe_service", return_value=svc):
        out = await rb.stripe_webhook(_request(), billing_service=bsvc)
    assert out["received"] is True
    assert out["handled"] is False  # never flipped to True after exception


@pytest.mark.asyncio
async def test_unknown_event_type_acknowledged_no_dispatch():
    event = {"type": "ping.pong", "data": {"object": {}}}
    svc = _stripe_svc(); svc.verify_webhook = lambda *_: event
    bsvc = _billing()
    with patch.object(rb, "get_stripe_service", return_value=svc):
        out = await rb.stripe_webhook(_request(), billing_service=bsvc)
    assert out == {"received": True, "type": "ping.pong", "handled": False}
    bsvc.upsert_subscription_from_checkout.assert_not_called()
    bsvc.update_subscription_status_by_stripe_id.assert_not_called()
    bsvc.mark_invoice_past_due_by_stripe_id.assert_not_called()
