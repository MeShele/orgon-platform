"""Email delivery for ORGON — password reset, invites, transactional alerts.

Two backends:

* `SMTPBackend`  — used when `SMTP_HOST` env is set. SSL/TLS support.
* `FileBackend`  — fallback for local dev / preview without SMTP creds.
                   Writes the formatted message to /tmp/orgon_emails.log
                   so QA / dev can grab the reset token without standing
                   up an SMTP server.

Two delivery paths:

* `send_password_reset / send_email_verification / send_invite` —
  typed entry points for plain-text user-flow emails.
* `send_template(template_name, ...)` — HTML templated emails for
  transaction notifications (welcome / transaction_created / signed /
  completed / password_reset). Used by `NotificationService`.

This module replaces the pre-Wave-11 `backend/email_service.py` which
covered only the templated path; the two were merged here so there is
one canonical email service.

The public methods are async — backends do their I/O in a thread pool
because Python's stdlib `smtplib` is sync. This keeps the event loop
happy without dragging in `aiosmtplib`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

logger = logging.getLogger("orgon.services.email")


# ────────────────────────────────────────────────────────────────────
# HTML templates (for transactional notifications)
# ────────────────────────────────────────────────────────────────────

EMAIL_TEMPLATES: dict[str, dict[str, str]] = {
    "welcome": {
        "subject": "Welcome to ORGON",
        "body": """
<html><body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #2563eb;">Welcome to ORGON</h2>
  <p>Hi {full_name},</p>
  <p>Your account has been created successfully.</p>
  <p><strong>Email:</strong> {email}<br/>
  <strong>Role:</strong> {role}<br/>
  <strong>Organization:</strong> {organization}</p>
  <p>You can now log in and start managing your crypto treasury.</p>
  <p style="color: #666; font-size: 12px;">— The ORGON Team</p>
</div></body></html>""",
    },
    "transaction_created": {
        "subject": "New Transaction Created — {tx_id}",
        "body": """
<html><body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #2563eb;">New Transaction</h2>
  <p>A new transaction has been created:</p>
  <table style="border-collapse: collapse; width: 100%;">
    <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>ID:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{tx_id}</td></tr>
    <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Amount:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{amount} {currency}</td></tr>
    <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>To:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{to_address}</td></tr>
    <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Created by:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{created_by}</td></tr>
  </table>
  <p>Please review and sign if required.</p>
  <p style="color: #666; font-size: 12px;">— ORGON Notifications</p>
</div></body></html>""",
    },
    "transaction_signed": {
        "subject": "Transaction Signed — {tx_id}",
        "body": """
<html><body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #16a34a;">Transaction Signed</h2>
  <p>Transaction <strong>{tx_id}</strong> has been signed by <strong>{signer}</strong>.</p>
  <p><strong>Status:</strong> {status}<br/>
  <strong>Signatures:</strong> {signatures_count}/{signatures_required}</p>
  <p style="color: #666; font-size: 12px;">— ORGON Notifications</p>
</div></body></html>""",
    },
    "transaction_completed": {
        "subject": "Transaction Completed — {tx_id}",
        "body": """
<html><body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #16a34a;">Transaction Completed</h2>
  <p>Transaction <strong>{tx_id}</strong> has been fully signed and submitted.</p>
  <p><strong>Amount:</strong> {amount} {currency}<br/>
  <strong>TX Hash:</strong> {tx_hash}</p>
  <p style="color: #666; font-size: 12px;">— ORGON Notifications</p>
</div></body></html>""",
    },
    "password_reset_html": {
        "subject": "Password Reset — ORGON",
        "body": """
<html><body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #2563eb;">Password Reset</h2>
  <p>You requested a password reset. Use this code:</p>
  <p style="font-size: 24px; font-weight: bold; text-align: center; padding: 20px; background: #f3f4f6; border-radius: 8px;">{reset_code}</p>
  <p>This code expires in 1 hour.</p>
  <p style="color: #666; font-size: 12px;">If you didn't request this, ignore this email.</p>
</div></body></html>""",
    },
}


# ────────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SMTPConfig:
    host: str
    port: int = 587
    user: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True   # STARTTLS on submission port 587
    use_ssl: bool = False  # implicit TLS on port 465

    @classmethod
    def from_env(cls) -> Optional["SMTPConfig"]:
        host = os.getenv("SMTP_HOST", "").strip()
        if not host:
            return None
        return cls(
            host=host,
            port=int(os.getenv("SMTP_PORT", "587")),
            user=os.getenv("SMTP_USER") or None,
            password=os.getenv("SMTP_PASSWORD") or None,
            use_tls=os.getenv("SMTP_USE_TLS", "1").lower() in {"1", "true", "yes"},
            use_ssl=os.getenv("SMTP_USE_SSL", "0").lower() in {"1", "true", "yes"},
        )


# ────────────────────────────────────────────────────────────────────
# Backends
# ────────────────────────────────────────────────────────────────────

class FileBackend:
    """Dev/preview fallback. Appends each message to a log file.

    Reset tokens etc. are visible to anyone with disk access, so this
    backend is unsafe for production — it must only run when SMTP is
    not configured.
    """

    def __init__(self, path: str = "/tmp/orgon_emails.log"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def deliver(self, msg: EmailMessage) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write("─" * 70 + "\n")
            f.write(f"To: {msg['To']}\nFrom: {msg['From']}\nSubject: {msg['Subject']}\n\n")
            f.write(msg.get_content())
            f.write("\n")
        logger.info("Email written to %s for %s (%s)", self.path, msg["To"], msg["Subject"])


class SMTPBackend:
    """Real outbound SMTP. Synchronous; called via run_in_executor()."""

    def __init__(self, cfg: SMTPConfig):
        self.cfg = cfg

    def deliver(self, msg: EmailMessage) -> None:
        cfg = self.cfg
        if cfg.use_ssl:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg.host, cfg.port, context=ctx, timeout=15) as s:
                if cfg.user and cfg.password:
                    s.login(cfg.user, cfg.password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(cfg.host, cfg.port, timeout=15) as s:
                s.ehlo()
                if cfg.use_tls:
                    s.starttls(context=ssl.create_default_context())
                    s.ehlo()
                if cfg.user and cfg.password:
                    s.login(cfg.user, cfg.password)
                s.send_message(msg)
        logger.info("Email sent via SMTP to %s (%s)", msg["To"], msg["Subject"])


# ────────────────────────────────────────────────────────────────────
# Service
# ────────────────────────────────────────────────────────────────────

class EmailService:
    def __init__(
        self,
        from_address: str = "noreply@orgon.asystem.kg",
        backend: Optional[object] = None,
        public_base_url: Optional[str] = None,
    ):
        self.from_address = from_address
        # Frontend URL embedded in links sent to users. /reset-password,
        # /verify-email, /invite all live there.
        self.public_base_url = public_base_url or os.getenv(
            "ORGON_PUBLIC_URL", "https://orgon-preview.asystem.kg"
        )

        if backend is not None:
            self.backend = backend
        else:
            cfg = SMTPConfig.from_env()
            if cfg:
                self.backend = SMTPBackend(cfg)
                logger.info("EmailService → SMTP at %s:%s", cfg.host, cfg.port)
            else:
                self.backend = FileBackend()
                logger.warning("EmailService → FileBackend (SMTP_HOST not set) — never use in prod")

    # ─── public sends ───────────────────────────────────────────────

    async def send_password_reset(self, email: str, token: str) -> None:
        link = f"{self.public_base_url}/reset-password?token={token}"
        msg = self._build(
            to=email,
            subject="ORGON · восстановление пароля",
            body=(
                "Здравствуйте,\n\n"
                "Вы (или кто-то от вашего имени) запросили восстановление пароля для\n"
                f"учётной записи {email} в ORGON.\n\n"
                "Ссылка действует один час:\n"
                f"  {link}\n\n"
                "Если вы не запрашивали восстановление, просто проигнорируйте это письмо —\n"
                "пароль не изменится.\n\n"
                "—\n"
                "ORGON · custody platform · support@orgon.asystem.kg\n"
            ),
        )
        await self._deliver(msg)

    async def send_email_verification(self, email: str, token: str, full_name: str = "") -> None:
        link = f"{self.public_base_url}/verify-email?token={token}"
        greeting = f"Здравствуйте, {full_name}" if full_name else "Здравствуйте"
        msg = self._build(
            to=email,
            subject="ORGON · подтверждение почты",
            body=(
                f"{greeting},\n\n"
                "Подтвердите, пожалуйста, что эта почта действительно ваша:\n"
                f"  {link}\n\n"
                "Без подтверждения часть функций будет недоступна (приглашение в команду,\n"
                "восстановление пароля, выпуск API-ключей).\n\n"
                "—\n"
                "ORGON · custody platform · support@orgon.asystem.kg\n"
            ),
        )
        await self._deliver(msg)

    async def send_invite(
        self,
        email: str,
        org_name: str,
        invite_token: str,
        inviter_name: str = "",
        role: str = "viewer",
    ) -> None:
        link = f"{self.public_base_url}/register?invite={invite_token}"
        from_label = inviter_name or "Администратор организации"
        msg = self._build(
            to=email,
            subject=f"ORGON · приглашение в {org_name}",
            body=(
                "Здравствуйте,\n\n"
                f"{from_label} приглашает вас присоединиться к организации\n"
                f"«{org_name}» в ORGON в роли {role}.\n\n"
                "Ссылка для регистрации (действует 7 дней):\n"
                f"  {link}\n\n"
                "После завершения регистрации вы автоматически получите доступ к\n"
                "кошелькам и транзакциям организации в рамках вашей роли.\n\n"
                "—\n"
                "ORGON · custody platform · support@orgon.asystem.kg\n"
            ),
        )
        await self._deliver(msg)

    # ─── general-purpose / templated sends (for NotificationService) ────

    async def send_email(
        self, to: str, subject: str, body: str, html: bool = False
    ) -> bool:
        """Send an arbitrary email. Returns True on success, False on swallow.

        Used by NotificationService when sending transactional templates.
        Plain-text by default; pass `html=True` for HTML body.
        """
        msg = self._build(to=to, subject=subject, body=body, html=html)
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.backend.deliver, msg)
            return True
        except Exception:
            logger.exception("Email delivery failed for %s (%s)", to, subject)
            return False

    async def send_template(self, to: str, template_name: str, **kwargs) -> bool:
        """Render `EMAIL_TEMPLATES[template_name]` with kwargs and send."""
        tpl = EMAIL_TEMPLATES.get(template_name)
        if not tpl:
            logger.error("Unknown email template: %s", template_name)
            return False
        try:
            subject = tpl["subject"].format(**kwargs)
            body = tpl["body"].format(**kwargs)
        except KeyError as e:
            logger.error("Email template '%s' missing placeholder: %s",
                         template_name, e)
            return False
        return await self.send_email(to, subject, body, html=True)

    # ─── internals ──────────────────────────────────────────────────

    def _build(
        self, to: str, subject: str, body: str, html: bool = False
    ) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = self.from_address
        msg["To"] = to
        msg["Subject"] = subject
        if html:
            msg.set_content("Plain-text fallback unavailable — please view in HTML.")
            msg.add_alternative(body, subtype="html")
        else:
            msg.set_content(body)
        return msg

    async def _deliver(self, msg: EmailMessage) -> None:
        # smtplib is sync — bounce to the default executor.
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.backend.deliver, msg)
        except Exception:
            # Don't fail the calling endpoint just because email failed —
            # password reset and invite are best-effort. Log and swallow.
            logger.exception("Email delivery failed for %s", msg["To"])


# ────────────────────────────────────────────────────────────────────
# Module-level singleton
# ────────────────────────────────────────────────────────────────────

_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    global _service
    if _service is None:
        _service = EmailService()
    return _service


# Legacy import compatibility: NotificationService and a few other call
# sites still do `from backend.services.email_service import email_service`.
# Lazy-init via __getattr__ so the module-level reference doesn't fire
# SMTP env reads at import time (matters for unit tests that monkeypatch
# env after the import).
def __getattr__(name: str):
    if name == "email_service":
        return get_email_service()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
