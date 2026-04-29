"""Unit tests for StripeService — disabled mode + checkout shape."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from backend.services.stripe_service import (
    StripeConfig,
    StripeNotConfigured,
    StripeService,
)


# ────────────────────────────────────────────────────────────────────
# Disabled mode (no STRIPE_API_KEY)
# ────────────────────────────────────────────────────────────────────


def test_disabled_when_no_api_key(monkeypatch):
    monkeypatch.delenv("STRIPE_API_KEY", raising=False)
    s = StripeService()
    assert s.configured is False


def test_create_session_raises_when_disabled(monkeypatch):
    monkeypatch.delenv("STRIPE_API_KEY", raising=False)
    s = StripeService()
    with pytest.raises(StripeNotConfigured):
        s.create_checkout_session(
            organization_id=uuid4(), plan_slug="basic",
        )


def test_verify_webhook_raises_without_secret(monkeypatch):
    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_dummy")
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    s = StripeService()
    assert s.configured is True
    with pytest.raises(StripeNotConfigured):
        s.verify_webhook(b"{}", "whatever")


# ────────────────────────────────────────────────────────────────────
# Configured mode — assert we hit the right Stripe API and metadata
# ────────────────────────────────────────────────────────────────────


def _patched_cfg() -> StripeConfig:
    """Fully-loaded config without touching env."""
    return StripeConfig(
        api_key="sk_test_unit",
        webhook_secret="whsec_unit",
        public_base_url="https://example.test",
        price_map={
            "starter": ("price_starter_monthly", "price_starter_yearly"),
            "basic":   ("price_basic_monthly",   None),
            "pro":     ("price_pro_monthly",     "price_pro_yearly"),
        },
    )


def test_create_session_picks_monthly_price_id():
    cfg = _patched_cfg()
    s = StripeService(cfg)
    org = uuid4()

    fake_session = type("S", (), {"id": "cs_unit_1", "url": "https://stripe/cs_unit_1"})()
    with patch("backend.services.stripe_service.stripe.checkout.Session.create",
               return_value=fake_session) as create:
        out = s.create_checkout_session(
            organization_id=org, plan_slug="basic", billing_cycle="monthly",
            customer_email="u@example.test",
        )

    assert out == {"url": "https://stripe/cs_unit_1", "session_id": "cs_unit_1"}
    create.assert_called_once()
    kwargs = create.call_args.kwargs
    assert kwargs["mode"] == "subscription"
    assert kwargs["line_items"] == [{"price": "price_basic_monthly", "quantity": 1}]
    assert kwargs["customer_email"] == "u@example.test"
    assert kwargs["client_reference_id"] == str(org)
    assert kwargs["metadata"]["organization_id"] == str(org)
    assert kwargs["metadata"]["plan_slug"] == "basic"
    assert kwargs["success_url"].startswith("https://example.test/billing/success")
    assert kwargs["cancel_url"] == "https://example.test/billing/cancel"


def test_create_session_picks_yearly_when_available():
    cfg = _patched_cfg()
    s = StripeService(cfg)

    fake_session = type("S", (), {"id": "cs_y", "url": "https://stripe/y"})()
    with patch("backend.services.stripe_service.stripe.checkout.Session.create",
               return_value=fake_session) as create:
        s.create_checkout_session(
            organization_id=uuid4(), plan_slug="pro", billing_cycle="yearly",
        )
    kwargs = create.call_args.kwargs
    assert kwargs["line_items"] == [{"price": "price_pro_yearly", "quantity": 1}]


def test_create_session_falls_back_to_monthly_when_no_yearly():
    cfg = _patched_cfg()
    s = StripeService(cfg)

    fake_session = type("S", (), {"id": "cs_b", "url": "https://stripe/b"})()
    with patch("backend.services.stripe_service.stripe.checkout.Session.create",
               return_value=fake_session) as create:
        s.create_checkout_session(
            organization_id=uuid4(), plan_slug="basic", billing_cycle="yearly",
        )
    # basic has no yearly price ID → falls back to monthly.
    assert create.call_args.kwargs["line_items"] == [{"price": "price_basic_monthly", "quantity": 1}]


def test_create_session_unknown_plan_raises_value_error():
    cfg = _patched_cfg()
    s = StripeService(cfg)
    with pytest.raises(ValueError):
        s.create_checkout_session(organization_id=uuid4(), plan_slug="enterprise")
