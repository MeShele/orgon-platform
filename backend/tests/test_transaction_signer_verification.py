"""Wire-up tests for `_verify_safina_signers` (Wave 22, Story 2.7).

We instantiate `TransactionService` against a fake `AsyncDatabase`
that records every `execute` call, then drive `_verify_safina_signers`
directly with synthetic Safina-Transaction objects. The verifier
itself is exercised by `test_safina_canonical.py`; here we only check
the wire-up: env-gating, alert insertion, status-override in enforce.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from eth_keys import keys as eth_keys

from backend.safina import signature_verifier as sv
from backend.services.transaction_service import TransactionService


# ────────────────────────────────────────────────────────────────────
# Test doubles
# ────────────────────────────────────────────────────────────────────


class _FakeAsyncDB:
    """Minimal AsyncDatabase stand-in — records `execute` calls."""

    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self.fail_on: str | None = None

    async def execute(self, sql: str, params=None):
        self.calls.append((sql, tuple(params) if params else ()))
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError(f"injected failure in {self.fail_on}")
        return "OK"


def _make_service() -> tuple[TransactionService, _FakeAsyncDB]:
    db = _FakeAsyncDB()
    # Pass `client=None`; _verify_safina_signers does not touch it.
    svc = TransactionService(client=None, db=db)
    return svc, db


def _tx(*, unid="tx_abc", value="1000", to_addr="0x" + "ab" * 20,
        token="1###wallet1", signed=None, organization_id=None):
    """Synthetic Safina Transaction-like object."""
    obj = SimpleNamespace(
        id=1, tx=None, token=token, token_name=None,
        to_addr=to_addr, value=value, value_hex=None, unid=unid,
        init_ts=1700000000, min_sign=1, wait=None, signed=signed or [],
        info=None, organization_id=organization_id, network=None,
    )
    return obj


# ────────────────────────────────────────────────────────────────────
# Env gating
# ────────────────────────────────────────────────────────────────────


@pytest.fixture
def env_isolated(monkeypatch):
    for k in ("SAFINA_CANONICAL_VARIANT", "ORGON_SAFINA_VERIFY_MODE",
              "ORGON_VERIFY_SAFINA_SIGS"):
        monkeypatch.delenv(k, raising=False)
    yield monkeypatch


@pytest.fixture
def keypair():
    pk = eth_keys.PrivateKey(bytes.fromhex("22" * 32))
    return pk, pk.public_key.to_checksum_address()


def _signed_entry(pk, addr, tx_dict, variant_name):
    spec = sv.list_canonical_variants()[variant_name]
    digest = sv._digest_for_variant(spec, tx_dict)
    sig = pk.sign_msg_hash(digest)
    raw = sig.to_bytes()
    sig_hex = "0x" + raw[:64].hex() + bytes([raw[64] + 27]).hex()
    return {"ecaddress": addr, "ecsign": sig_hex}


@pytest.mark.asyncio
async def test_off_mode_no_verification_no_db_writes(env_isolated, keypair):
    """When mode is off, `_verify_safina_signers` is a no-op."""
    pk, addr = keypair
    svc, db = _make_service()
    tx = _tx(signed=[{"ecaddress": addr, "ecsign": "0x" + "00" * 65}])
    await svc._verify_safina_signers(tx, current_status="signed")
    assert db.calls == []


@pytest.mark.asyncio
async def test_no_signed_list_is_noop(env_isolated, keypair):
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "shadow")
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v1_pipe_unid_to_value")
    svc, db = _make_service()
    tx = _tx(signed=None)
    await svc._verify_safina_signers(tx, current_status="pending")
    assert db.calls == []


@pytest.mark.asyncio
async def test_shadow_match_no_alert_no_status_change(env_isolated, keypair):
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "shadow")
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v1_pipe_unid_to_value")
    pk, addr = keypair
    tx_dict = {
        "tx_unid": "tx_abc", "network": 1, "value": "1000",
        "to_address": "0x" + "ab" * 20,
    }
    svc, db = _make_service()
    tx = _tx(signed=[_signed_entry(pk, addr, tx_dict, "v1_pipe_unid_to_value")])
    await svc._verify_safina_signers(tx, current_status="signed")
    # No execute calls — match → nothing to do.
    assert db.calls == []


@pytest.mark.asyncio
async def test_shadow_mismatch_creates_alert_keeps_status(env_isolated, keypair):
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "shadow")
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v1_pipe_unid_to_value")
    pk, _addr = keypair
    tx_dict = {
        "tx_unid": "tx_abc", "network": 1, "value": "1000",
        "to_address": "0x" + "ab" * 20,
    }
    svc, db = _make_service()
    # Sign with v1, claim a different signer address — mismatch.
    sig_entry = _signed_entry(pk, "0x" + "ff" * 20, tx_dict, "v1_pipe_unid_to_value")
    tx = _tx(signed=[sig_entry], organization_id="org-uuid-1")
    await svc._verify_safina_signers(tx, current_status="signed")
    # One alert insert, no status UPDATE.
    inserts = [s for s, _ in db.calls if "INSERT INTO aml_alerts" in s]
    updates = [s for s, _ in db.calls if "UPDATE transactions SET status" in s]
    assert len(inserts) == 1
    assert updates == []


@pytest.mark.asyncio
async def test_enforce_mismatch_overrides_status_and_alerts(env_isolated, keypair):
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "enforce")
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v1_pipe_unid_to_value")
    pk, _addr = keypair
    tx_dict = {
        "tx_unid": "tx_abc", "network": 1, "value": "1000",
        "to_address": "0x" + "ab" * 20,
    }
    svc, db = _make_service()
    sig_entry = _signed_entry(pk, "0x" + "ff" * 20, tx_dict, "v1_pipe_unid_to_value")
    tx = _tx(signed=[sig_entry], organization_id="org-uuid-1")
    await svc._verify_safina_signers(tx, current_status="signed")
    inserts = [s for s, _ in db.calls if "INSERT INTO aml_alerts" in s]
    updates = [(s, p) for s, p in db.calls if "UPDATE transactions SET status" in s]
    assert len(inserts) == 1
    assert len(updates) == 1
    # The status payload is `rejected_signer_mismatch`.
    sql, params = updates[0]
    assert params[0] == "rejected_signer_mismatch"


@pytest.mark.asyncio
async def test_enforce_match_no_status_change(env_isolated, keypair):
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "enforce")
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v1_pipe_unid_to_value")
    pk, addr = keypair
    tx_dict = {
        "tx_unid": "tx_abc", "network": 1, "value": "1000",
        "to_address": "0x" + "ab" * 20,
    }
    svc, db = _make_service()
    tx = _tx(signed=[_signed_entry(pk, addr, tx_dict, "v1_pipe_unid_to_value")])
    await svc._verify_safina_signers(tx, current_status="signed")
    assert db.calls == []


@pytest.mark.asyncio
async def test_alert_write_failure_does_not_block_status_override(env_isolated, keypair):
    """Even if the AML alert insert blows up, enforce-mode must still
    flip the tx status — the tx-row is the source of truth, the alert
    is a notification (ADR-8)."""
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "enforce")
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v1_pipe_unid_to_value")
    pk, _addr = keypair
    tx_dict = {
        "tx_unid": "tx_abc", "network": 1, "value": "1000",
        "to_address": "0x" + "ab" * 20,
    }
    svc, db = _make_service()
    db.fail_on = "INSERT INTO aml_alerts"
    sig_entry = _signed_entry(pk, "0x" + "ff" * 20, tx_dict, "v1_pipe_unid_to_value")
    tx = _tx(signed=[sig_entry], organization_id="org-uuid-1")
    await svc._verify_safina_signers(tx, current_status="signed")
    updates = [(s, p) for s, p in db.calls if "UPDATE transactions SET status" in s]
    assert len(updates) == 1
    assert updates[0][1][0] == "rejected_signer_mismatch"


@pytest.mark.asyncio
async def test_unknown_variant_skips_verification_does_not_crash(env_isolated, keypair):
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "enforce")
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v99_does_not_exist")
    pk, addr = keypair
    svc, db = _make_service()
    tx = _tx(signed=[{"ecaddress": addr, "ecsign": "0x" + "00" * 65}])
    # Must not raise.
    await svc._verify_safina_signers(tx, current_status="signed")
    # No DB writes — verification effectively disabled.
    inserts = [s for s, _ in db.calls if "INSERT INTO aml_alerts" in s]
    assert inserts == []


@pytest.mark.asyncio
async def test_extract_network_from_token_prefix():
    """Service extracts numeric network from `<int>###<wallet>` token."""
    tx = _tx(token="195###wallet1")
    tx.network = None
    assert TransactionService._extract_network(tx) == 195


@pytest.mark.asyncio
async def test_extract_network_explicit_attr_wins():
    tx = _tx(token="bad###format")
    tx.network = 1
    assert TransactionService._extract_network(tx) == 1


@pytest.mark.asyncio
async def test_skip_when_network_unknown(env_isolated, keypair):
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "enforce")
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v1_pipe_unid_to_value")
    pk, addr = keypair
    svc, db = _make_service()
    tx = _tx(signed=[{"ecaddress": addr, "ecsign": "0x" + "00" * 65}],
             token="garbage_no_separator")
    tx.network = None
    await svc._verify_safina_signers(tx, current_status="signed")
    assert db.calls == []
