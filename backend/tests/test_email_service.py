"""Unit tests for EmailService — reset / verify / invite flows."""

from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.services.email_service import (
    EmailService,
    FileBackend,
    SMTPConfig,
    SMTPBackend,
)


# ────────────────────────────────────────────────────────────────────


class CapturingBackend:
    """Backend that records every message instead of delivering."""

    def __init__(self):
        self.sent: list[EmailMessage] = []

    def deliver(self, msg: EmailMessage) -> None:
        self.sent.append(msg)


@pytest.fixture
def captured() -> CapturingBackend:
    return CapturingBackend()


@pytest.fixture
def service(captured) -> EmailService:
    return EmailService(
        from_address="noreply@orgon.test",
        backend=captured,
        public_base_url="https://example.test",
    )


# ────────────────────────────────────────────────────────────────────
# Public sends
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_password_reset_link_uses_token(service, captured):
    await service.send_password_reset("user@example.test", "abc123")
    assert len(captured.sent) == 1
    msg = captured.sent[0]
    body = msg.get_content()
    assert "https://example.test/reset-password?token=abc123" in body
    assert msg["To"] == "user@example.test"
    assert "восстановление" in msg["Subject"].lower()


@pytest.mark.asyncio
async def test_email_verification_carries_full_name_when_present(service, captured):
    await service.send_email_verification("u@example.test", "tok", full_name="Алексей")
    body = captured.sent[0].get_content()
    assert "Алексей" in body
    assert "https://example.test/verify-email?token=tok" in body


@pytest.mark.asyncio
async def test_invite_includes_org_and_role(service, captured):
    await service.send_invite(
        email="x@example.test", org_name="ACME", invite_token="inv123",
        inviter_name="Bob", role="admin",
    )
    body = captured.sent[0].get_content()
    assert "ACME" in body
    assert "admin" in body
    assert "Bob" in body
    assert "https://example.test/register?invite=inv123" in body


@pytest.mark.asyncio
async def test_delivery_failure_does_not_raise(service, captured):
    # Replace backend with one that raises — the call should be swallowed
    # so password-reset endpoints don't 500 because of SMTP outage.
    class BoomBackend:
        def deliver(self, msg):
            raise RuntimeError("smtp down")

    service.backend = BoomBackend()
    # Must NOT raise:
    await service.send_password_reset("u@example.test", "tok")


# ────────────────────────────────────────────────────────────────────
# Backend selection from env
# ────────────────────────────────────────────────────────────────────


def test_smtp_config_returns_none_when_host_unset(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    assert SMTPConfig.from_env() is None


def test_smtp_config_reads_full_env(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_USER", "u")
    monkeypatch.setenv("SMTP_PASSWORD", "p")
    monkeypatch.setenv("SMTP_USE_TLS", "0")
    monkeypatch.setenv("SMTP_USE_SSL", "1")
    cfg = SMTPConfig.from_env()
    assert cfg is not None
    assert cfg.host == "smtp.test"
    assert cfg.port == 2525
    assert cfg.user == "u"
    assert cfg.password == "p"
    assert cfg.use_tls is False
    assert cfg.use_ssl is True


def test_default_constructor_falls_back_to_filebackend(monkeypatch, tmp_path):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    # Avoid touching the shared /tmp file.
    monkeypatch.setattr("backend.services.email_service.FileBackend",
                        lambda: FileBackend(str(tmp_path / "emails.log")))
    s = EmailService()
    assert isinstance(s.backend, FileBackend)


def test_filebackend_writes_to_disk(tmp_path):
    p = tmp_path / "out.log"
    fb = FileBackend(str(p))
    msg = EmailMessage()
    msg["From"] = "n@n"
    msg["To"] = "u@u"
    msg["Subject"] = "hi"
    msg.set_content("body line")
    fb.deliver(msg)
    text = p.read_text()
    assert "hi" in text
    assert "body line" in text
    assert "u@u" in text
