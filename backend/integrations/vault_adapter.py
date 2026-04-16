"""ASAGENT CredentialVault adapter for ORGON."""

import logging
import sys
from pathlib import Path

logger = logging.getLogger("orgon.integrations.vault")

# Add ASAGENT to path
ASAGENT_ROOT = Path(__file__).parent.parent.parent.parent / "asagent"
if str(ASAGENT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ASAGENT_ROOT.parent))


class VaultAdapter:
    """Wrapper around ASAGENT CredentialVault for Safina credentials."""

    SCOPE = "safina"
    KEY_NAME = "safina_ec_private_key"

    def __init__(self):
        self._vault = None

    def _get_vault(self):
        if self._vault is None:
            try:
                from asagent.security.vault.vault import CredentialVault
                self._vault = CredentialVault()
                logger.info("Connected to ASAGENT CredentialVault")
            except Exception as e:
                logger.warning("ASAGENT Vault not available: %s", e)
                return None
        return self._vault

    def store_ec_key(self, private_key_hex: str) -> bool:
        """Store Safina EC private key in vault."""
        vault = self._get_vault()
        if not vault:
            return False
        try:
            vault.store(
                name=self.KEY_NAME,
                value=private_key_hex,
                scope=self.SCOPE,
                metadata={"description": "Safina Pay EC private key"},
            )
            logger.info("EC private key stored in vault")
            return True
        except Exception as e:
            logger.error("Failed to store EC key: %s", e)
            return False

    def get_ec_key(self, agent_id: str = "orchestrator") -> str | None:
        """Retrieve Safina EC private key from vault."""
        vault = self._get_vault()
        if not vault:
            return None
        try:
            return vault.get(self.KEY_NAME, agent_id=agent_id)
        except Exception as e:
            logger.error("Failed to retrieve EC key: %s", e)
            return None
