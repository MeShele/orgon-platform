"""E-07 — rule engine extensions: new kinds, scope filter, action
request_approval, policy.triggered webhook.

We exercise the pure checkers and the scope filter directly. The
evaluator loop (`_evaluate_rules_impl`) is covered by the fake-pool
approach used in `test_rule_engine.py` — we only spot-check the
new branches here to keep this file focused on E-07 deltas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from backend.services.compliance_service import ComplianceService
from backend.services import webhook_publisher as wp


# ────────────────────────────────────────────────────────────────────
# New constants — surface freeze
# ────────────────────────────────────────────────────────────────────


def test_new_rule_types_registered():
    types = set(ComplianceService.SUPPORTED_RULE_TYPES)
    # E-07 additions
    assert "velocity_amount_usd" in types
    assert "recipient_whitelist" in types
    assert "time_window" in types
    assert "recipient_geo_block" in types
    # Legacy must NOT be evicted
    assert {"threshold", "velocity", "blacklist_address"} <= types


def test_new_actions_registered():
    actions = set(ComplianceService.SUPPORTED_RULE_ACTIONS)
    assert "request_approval" in actions
    assert {"alert", "hold", "block"} <= actions


def test_request_approval_priority_equals_hold():
    """E-08 (approval workflow) depends on this: request_approval
    must take the same verdict rung as `hold` so the tx-flow puts
    the tx in on_hold without bespoke routing."""
    pri = ComplianceService._ACTION_PRIORITY
    assert pri["request_approval"] == pri["hold"] == 1
    assert pri["alert"] < pri["request_approval"] < pri["block"]


def test_webhook_publisher_exports_policy_triggered():
    assert wp.EV_POLICY_TRIGGERED == "policy.triggered"


# ────────────────────────────────────────────────────────────────────
# recipient_whitelist
# ────────────────────────────────────────────────────────────────────


def test_recipient_whitelist_fires_when_address_not_in_allowlist():
    cfg = {"addresses": ["TXa1...", "TXb2..."]}
    tx = {"to_address": "TXc3..."}
    assert ComplianceService._check_recipient_whitelist(cfg, tx) is True


def test_recipient_whitelist_does_not_fire_when_address_in_allowlist():
    cfg = {"addresses": ["TXa1...", "TXb2..."]}
    tx = {"to_address": "txA1..."}    # case-insensitive
    assert ComplianceService._check_recipient_whitelist(cfg, tx) is False


def test_recipient_whitelist_empty_allowlist_does_not_fire():
    """An empty allowlist is treated as 'not configured' — refusing
    to fire here prevents a half-configured rule from blocking everything."""
    cfg = {"addresses": []}
    tx = {"to_address": "TXc3..."}
    assert ComplianceService._check_recipient_whitelist(cfg, tx) is False


def test_recipient_whitelist_missing_to_address_does_not_fire():
    cfg = {"addresses": ["TXa1..."]}
    tx = {"to_address": ""}
    assert ComplianceService._check_recipient_whitelist(cfg, tx) is False


# ────────────────────────────────────────────────────────────────────
# time_window
# ────────────────────────────────────────────────────────────────────


def test_time_window_fires_during_blocked_hour():
    cfg = {"blocked_hours_utc": [2, 3, 4]}
    fixed = datetime(2026, 5, 19, 3, 30, tzinfo=timezone.utc)
    with patch("backend.services.compliance_service.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        assert ComplianceService._check_time_window(cfg) is True


def test_time_window_does_not_fire_outside_blocked_hours():
    cfg = {"blocked_hours_utc": [2, 3, 4]}
    fixed = datetime(2026, 5, 19, 14, 0, tzinfo=timezone.utc)
    with patch("backend.services.compliance_service.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        assert ComplianceService._check_time_window(cfg) is False


def test_time_window_empty_list_never_fires():
    assert ComplianceService._check_time_window({"blocked_hours_utc": []}) is False
    assert ComplianceService._check_time_window({}) is False


def test_time_window_bad_config_does_not_crash():
    """Bad config should NEVER take down rule evaluation."""
    assert ComplianceService._check_time_window({"blocked_hours_utc": ["a", "b"]}) is False
    assert ComplianceService._check_time_window({"blocked_hours_utc": None}) is False


# ────────────────────────────────────────────────────────────────────
# recipient_geo_block — stub contract
# ────────────────────────────────────────────────────────────────────


def test_recipient_geo_block_stub_never_fires():
    """Stub returns False until E-09 wires a real geo provider."""
    cfg = {"blocked_countries": ["RU", "KP"]}
    tx = {"to_address": "0xabc"}
    assert ComplianceService._check_recipient_geo_block_stub(cfg, tx) is False


# ────────────────────────────────────────────────────────────────────
# Scope filter — pure tx_matches_scope
# ────────────────────────────────────────────────────────────────────


def test_scope_empty_matches_everything():
    assert ComplianceService._tx_matches_scope({}, {"wallet_id": "w-1", "network": 5010})


def test_scope_wallet_id_match():
    scope = {"wallet_ids": ["w-1", "w-2"]}
    assert ComplianceService._tx_matches_scope(scope, {"wallet_id": "w-1"})
    assert not ComplianceService._tx_matches_scope(scope, {"wallet_id": "w-3"})


def test_scope_wallet_id_missing_tx_does_not_match():
    scope = {"wallet_ids": ["w-1"]}
    assert not ComplianceService._tx_matches_scope(scope, {})


def test_scope_networks_match():
    scope = {"networks": [5010, 5000]}
    assert ComplianceService._tx_matches_scope(scope, {"network": 5010})
    assert ComplianceService._tx_matches_scope(scope, {"network": "5000"})  # coerced
    assert not ComplianceService._tx_matches_scope(scope, {"network": 3000})


def test_scope_combination_requires_both():
    """If scope names both wallet_ids AND networks, BOTH must match."""
    scope = {"wallet_ids": ["w-1"], "networks": [5010]}
    assert ComplianceService._tx_matches_scope(scope, {"wallet_id": "w-1", "network": 5010})
    assert not ComplianceService._tx_matches_scope(scope, {"wallet_id": "w-1", "network": 3000})
    assert not ComplianceService._tx_matches_scope(scope, {"wallet_id": "w-2", "network": 5010})


def test_scope_unknown_keys_tolerated():
    """Forward-compat: future scope keys we don't yet evaluate must
    not flip an otherwise-matching tx to 'doesn't match'."""
    scope = {"wallet_ids": ["w-1"], "future_key": "future_value"}
    assert ComplianceService._tx_matches_scope(scope, {"wallet_id": "w-1"})


def test_scope_bad_network_value_excludes():
    """Malformed network field (not int-coercible) keeps the rule
    from firing — fail-closed."""
    scope = {"networks": [5010]}
    assert not ComplianceService._tx_matches_scope(scope, {"network": "abc"})
    assert not ComplianceService._tx_matches_scope(scope, {"network": None})
