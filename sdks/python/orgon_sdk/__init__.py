"""orgon-sdk — Python client for the ORGON B2B API.

Surface mirrors the TypeScript SDK 1:1:

    OrgonClient(api_key=..., secret=...)
      .users
      .wallets
      .transactions
      .deposits
      .webhooks
      .invoices

    verify_webhook(secret, timestamp, signature, raw_body) -> bool
"""

from .client import OrgonClient, OrgonError
from .webhooks import verify_webhook

__all__ = ["OrgonClient", "OrgonError", "verify_webhook"]
__version__ = "0.1.0"
