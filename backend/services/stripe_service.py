"""Stripe Checkout adapter — closes the pricing → payment funnel.

Responsibilities:
  * Create a Checkout Session for a given plan + organization.
  * Verify webhook signatures + dispatch events to the billing service.
  * Cancel a subscription on Stripe's side when the org cancels locally.

Configuration (env, see .env.example):
  STRIPE_API_KEY                    sk_test_… or sk_live_…
  STRIPE_WEBHOOK_SECRET             whsec_…
  STRIPE_PRICE_STARTER              price_… (monthly)
  STRIPE_PRICE_BASIC                price_…
  STRIPE_PRICE_PRO                  price_…
  STRIPE_PRICE_<SLUG>_YEARLY        optional yearly counterpart
  ORGON_PUBLIC_URL                  used to build success / cancel URLs

When `STRIPE_API_KEY` is unset the service is in *disabled* mode — every
public method raises `StripeNotConfigured` so the API can return a clean
503 instead of crashing on `stripe.error.AuthenticationError`. Demo
deployments ship without keys; production sets them in Coolify env.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import stripe

logger = logging.getLogger("orgon.services.stripe")


class StripeNotConfigured(RuntimeError):
    """Raised when STRIPE_API_KEY is missing — surfaced as 503 by the API."""


# ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StripeConfig:
    api_key: str
    webhook_secret: Optional[str]
    public_base_url: str
    # plan_slug → (monthly_price_id, yearly_price_id_or_None)
    price_map: dict[str, tuple[str, Optional[str]]]

    @classmethod
    def from_env(cls) -> Optional["StripeConfig"]:
        key = os.getenv("STRIPE_API_KEY", "").strip()
        if not key:
            return None
        price_map: dict[str, tuple[str, Optional[str]]] = {}
        for slug in ("starter", "basic", "pro"):
            monthly = os.getenv(f"STRIPE_PRICE_{slug.upper()}", "").strip()
            yearly = os.getenv(f"STRIPE_PRICE_{slug.upper()}_YEARLY", "").strip() or None
            if monthly:
                price_map[slug] = (monthly, yearly)
        return cls(
            api_key=key,
            webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", "").strip() or None,
            public_base_url=os.getenv("ORGON_PUBLIC_URL", "https://orgon-preview.asystem.kg"),
            price_map=price_map,
        )


# ────────────────────────────────────────────────────────────────────


class StripeService:
    def __init__(self, cfg: Optional[StripeConfig] = None):
        self.cfg = cfg or StripeConfig.from_env()
        if self.cfg:
            stripe.api_key = self.cfg.api_key
            logger.info(
                "StripeService active — %d price IDs mapped", len(self.cfg.price_map)
            )
        else:
            logger.warning("StripeService disabled (no STRIPE_API_KEY)")

    @property
    def configured(self) -> bool:
        return self.cfg is not None

    def _require(self) -> StripeConfig:
        if not self.cfg:
            raise StripeNotConfigured("Stripe is not configured on this deployment")
        return self.cfg

    # ─── checkout ──────────────────────────────────────────────────

    def create_checkout_session(
        self,
        *,
        organization_id: UUID,
        plan_slug: str,
        billing_cycle: str = "monthly",
        customer_email: Optional[str] = None,
    ) -> dict:
        """Create a Stripe Checkout Session and return {url, session_id}.

        Caller is the API endpoint — should redirect the browser to `url`.
        Stripe → success_url → frontend `/billing/success?session_id=…`.
        Webhook will activate the subscription server-side; the frontend
        page just shows confirmation.
        """
        cfg = self._require()
        price_pair = cfg.price_map.get(plan_slug)
        if not price_pair:
            raise ValueError(f"No Stripe price ID mapped for plan '{plan_slug}'")

        monthly, yearly = price_pair
        price_id = (yearly if billing_cycle == "yearly" and yearly else monthly)

        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{cfg.public_base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{cfg.public_base_url}/billing/cancel",
            customer_email=customer_email,
            client_reference_id=str(organization_id),
            metadata={
                "organization_id": str(organization_id),
                "plan_slug": plan_slug,
                "billing_cycle": billing_cycle,
            },
            subscription_data={
                "metadata": {
                    "organization_id": str(organization_id),
                    "plan_slug": plan_slug,
                },
            },
        )
        logger.info(
            "Stripe Checkout session %s created for org=%s plan=%s",
            session.id, organization_id, plan_slug,
        )
        return {"url": session.url, "session_id": session.id}

    # ─── webhook handling ──────────────────────────────────────────

    def verify_webhook(self, payload: bytes, signature_header: str) -> stripe.Event:
        """Verify webhook signature and return the parsed event.

        Called from the FastAPI handler. Lets `SignatureVerificationError`
        bubble up — caller maps it to 400.
        """
        cfg = self._require()
        if not cfg.webhook_secret:
            raise StripeNotConfigured("STRIPE_WEBHOOK_SECRET not set — refusing to accept webhook")
        return stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature_header,
            secret=cfg.webhook_secret,
        )


# ────────────────────────────────────────────────────────────────────


_service: Optional[StripeService] = None


def get_stripe_service() -> StripeService:
    global _service
    if _service is None:
        _service = StripeService()
    return _service
