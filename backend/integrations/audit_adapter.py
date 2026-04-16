"""ASAGENT AuditLogger adapter for ORGON operations."""

import logging
import sys
from pathlib import Path

logger = logging.getLogger("orgon.integrations.audit")

ASAGENT_ROOT = Path(__file__).parent.parent.parent.parent / "asagent"
if str(ASAGENT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ASAGENT_ROOT.parent))


class AuditAdapter:
    """Wrapper around ASAGENT AuditLogger for ORGON operations."""

    def __init__(self):
        self._audit = None

    def _get_audit(self):
        if self._audit is None:
            try:
                from asagent.security.audit import AuditLogger
                self._audit = AuditLogger()
                logger.info("Connected to ASAGENT AuditLogger")
            except Exception as e:
                logger.warning("ASAGENT AuditLogger not available: %s", e)
        return self._audit

    def log_wallet_created(self, unid: str, network: str):
        audit = self._get_audit()
        if audit:
            audit.log_quick("ORGON_EVENT", {
                "action": "wallet_created",
                "unid": unid,
                "network": network,
            })

    def log_transaction_sent(self, tx_unid: str, to_addr: str, value: str, token: str):
        audit = self._get_audit()
        if audit:
            audit.log_quick("ORGON_EVENT", {
                "action": "transaction_sent",
                "tx_unid": tx_unid,
                "to_addr": to_addr,
                "value": value,
                "token": token,
            })

    def log_transaction_signed(self, tx_unid: str):
        audit = self._get_audit()
        if audit:
            audit.log_quick("ORGON_EVENT", {
                "action": "transaction_signed",
                "tx_unid": tx_unid,
            })

    def log_transaction_rejected(self, tx_unid: str, reason: str):
        audit = self._get_audit()
        if audit:
            audit.log_quick("ORGON_EVENT", {
                "action": "transaction_rejected",
                "tx_unid": tx_unid,
                "reason": reason,
            })
