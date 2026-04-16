"""
Email notification service with SMTP support and file fallback.

Required env vars for SMTP:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, FROM_EMAIL

If SMTP is not configured, emails are logged to /root/ORGON/backend/email_logs/
"""

import smtplib
import os
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

logger = logging.getLogger("orgon.email")

EMAIL_TEMPLATES = {
    "welcome": {
        "subject": "Welcome to ORGON",
        "body": """
<html><body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #2563eb;">Welcome to ORGON! 🎉</h2>
  <p>Hi {full_name},</p>
  <p>Your account has been created successfully.</p>
  <p><strong>Email:</strong> {email}<br/>
  <strong>Role:</strong> {role}<br/>
  <strong>Organization:</strong> {organization}</p>
  <p>You can now log in and start managing your crypto treasury.</p>
  <p style="color: #666; font-size: 12px;">— The ORGON Team</p>
</div></body></html>"""
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
</div></body></html>"""
    },
    "transaction_signed": {
        "subject": "Transaction Signed — {tx_id}",
        "body": """
<html><body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #16a34a;">Transaction Signed ✅</h2>
  <p>Transaction <strong>{tx_id}</strong> has been signed by <strong>{signer}</strong>.</p>
  <p><strong>Status:</strong> {status}<br/>
  <strong>Signatures:</strong> {signatures_count}/{signatures_required}</p>
  <p style="color: #666; font-size: 12px;">— ORGON Notifications</p>
</div></body></html>"""
    },
    "transaction_completed": {
        "subject": "Transaction Completed — {tx_id}",
        "body": """
<html><body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #16a34a;">Transaction Completed ✅</h2>
  <p>Transaction <strong>{tx_id}</strong> has been fully signed and submitted.</p>
  <p><strong>Amount:</strong> {amount} {currency}<br/>
  <strong>TX Hash:</strong> {tx_hash}</p>
  <p style="color: #666; font-size: 12px;">— ORGON Notifications</p>
</div></body></html>"""
    },
    "password_reset": {
        "subject": "Password Reset — ORGON",
        "body": """
<html><body style="font-family: Arial, sans-serif; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #2563eb;">Password Reset</h2>
  <p>You requested a password reset. Use this code:</p>
  <p style="font-size: 24px; font-weight: bold; text-align: center; padding: 20px; background: #f3f4f6; border-radius: 8px;">{reset_code}</p>
  <p>This code expires in 1 hour.</p>
  <p style="color: #666; font-size: 12px;">If you didn't request this, ignore this email.</p>
</div></body></html>"""
    },
}


class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@orgon.asystem.ai")
        self.log_dir = os.getenv("EMAIL_LOG_DIR", "/root/ORGON/backend/email_logs")
        self._smtp_configured = bool(self.smtp_host)

    async def send_email(self, to: str, subject: str, body: str, html: bool = True) -> bool:
        """Send email via SMTP or log to file as fallback."""
        # Always log
        self._log_email(to, subject, body)

        if not self._smtp_configured:
            logger.warning("SMTP not configured — email logged to file: %s -> %s", subject, to)
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to
        msg.attach(MIMEText(body, "html" if html else "plain"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.from_email, to, msg.as_string())
            logger.info("Email sent: %s -> %s", subject, to)
            return True
        except Exception as e:
            logger.error("Email send failed: %s", e)
            return False

    async def send_template(self, to: str, template_name: str, **kwargs) -> bool:
        """Send email using a named template."""
        tpl = EMAIL_TEMPLATES.get(template_name)
        if not tpl:
            logger.error("Unknown email template: %s", template_name)
            return False
        subject = tpl["subject"].format(**kwargs)
        body = tpl["body"].format(**kwargs)
        return await self.send_email(to, subject, body)

    def _log_email(self, to: str, subject: str, body: str):
        """Log email to file for debugging / fallback."""
        os.makedirs(self.log_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "to": to,
            "subject": subject,
            "body": body,
        }
        filepath = os.path.join(self.log_dir, f"{ts}_{to.replace('@','_at_')}.json")
        try:
            with open(filepath, "w") as f:
                json.dump(log_entry, f, indent=2)
        except Exception as e:
            logger.error("Failed to log email: %s", e)


# Global instance
email_service = EmailService()
