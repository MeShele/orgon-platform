"""End-to-end test for the Safina canonical-variant discovery CLI
(Wave 22, Story 2.7). We run it as a subprocess against synthetic
samples — exits 0 + prints the variant name on a match, exits 1 on no
match, exits 2 on bad input.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from eth_keys import keys as eth_keys

from backend.safina import signature_verifier as sv

CLI = Path(__file__).resolve().parent.parent / "scripts" / "safina_discover_canonical.py"


def _build_sample(variant_name: str) -> dict:
    """Sign a synthetic tx with the named variant — round-trip should match."""
    pk = eth_keys.PrivateKey(bytes.fromhex("44" * 32))
    addr = pk.public_key.to_checksum_address()
    tx_data = {
        "tx_unid": "cli_test_unid",
        "network": 1,
        "value": "999",
        "to_address": "0x" + "ee" * 20,
    }
    spec = sv.list_canonical_variants()[variant_name]
    digest = sv._digest_for_variant(spec, tx_data)
    raw = pk.sign_msg_hash(digest).to_bytes()
    sig_hex = "0x" + raw[:64].hex() + bytes([raw[64] + 27]).hex()
    return {
        **tx_data,
        "signature_hex": sig_hex,
        "expected_signer": addr,
    }


def _run(args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        input=stdin,
        capture_output=True,
        text=True,
    )


def test_self_test_succeeds():
    res = _run(["--self-test"])
    assert res.returncode == 0
    assert "v1_pipe_unid_to_value" in res.stdout


def test_cli_finds_v2_variant(tmp_path):
    sample = _build_sample("v2_pipe_unid_value_to_network")
    p = tmp_path / "sample.json"
    p.write_text(json.dumps(sample))
    res = _run(["--sample", str(p)])
    assert res.returncode == 0
    assert "Confirmed variant: v2_pipe_unid_value_to_network" in res.stdout


def test_cli_finds_v6_pre_hashed(tmp_path):
    sample = _build_sample("v6_keccak_pre_hashed")
    p = tmp_path / "sample.json"
    p.write_text(json.dumps(sample))
    res = _run(["--sample", str(p)])
    assert res.returncode == 0
    assert "Confirmed variant: v6_keccak_pre_hashed" in res.stdout


def test_cli_no_match_returns_1(tmp_path):
    sample = {
        "tx_unid": "abc",
        "network": 1,
        "value": "1",
        "to_address": "0x" + "ab" * 20,
        # Random invalid signature.
        "signature_hex": "0x" + "00" * 65,
        "expected_signer": "0x" + "ff" * 20,
    }
    p = tmp_path / "sample.json"
    p.write_text(json.dumps(sample))
    res = _run(["--sample", str(p)])
    assert res.returncode == 1
    assert "no variant matched" in res.stdout


def test_cli_missing_field_returns_2(tmp_path):
    p = tmp_path / "sample.json"
    p.write_text(json.dumps({"tx_unid": "x"}))  # missing other keys
    res = _run(["--sample", str(p)])
    assert res.returncode == 2
    assert "missing keys" in res.stderr


def test_cli_stdin_input(tmp_path):
    sample = _build_sample("v3_json_sorted")
    res = _run([], stdin=json.dumps(sample))
    assert res.returncode == 0
    assert "v3_json_sorted" in res.stdout
