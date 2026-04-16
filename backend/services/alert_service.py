"""
Alert Service — monitors critical events and triggers notifications.

Alerts:
- Suspicious transactions (large amount, unusual pattern)
- Failed login attempts (brute force detection)
- Service health degradation
- KYC/KYB submission backlog
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger("orgon.alerts")


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    SUSPICIOUS_TRANSACTION = "suspicious_transaction"
    BRUTE_FORCE = "brute_force"
    SERVICE_DEGRADED = "service_degraded"
    KYC_BACKLOG = "kyc_backlog"
    LARGE_TRANSACTION = "large_transaction"


class AlertService:
    """Monitors events and triggers alerts via NotificationService."""

    # Thresholds
    LARGE_TX_THRESHOLD = 50000  # USD equivalent
    SUSPICIOUS_TX_THRESHOLD = 100000
    MAX_FAILED_LOGINS = 5
    FAILED_LOGIN_WINDOW_MINUTES = 10
    KYC_BACKLOG_THRESHOLD = 20

    def __init__(self, db_pool, notification_service=None):
        self.db = db_pool
        self.notification = notification_service
        self._failed_logins: Dict[str, List[datetime]] = {}  # ip -> [timestamps]

    # ---- Transaction Alerts ----

    async def check_transaction(self, transaction: dict, org_id: int):
        """Check transaction for suspicious patterns."""
        amount = float(transaction.get("amount", 0))
        currency = transaction.get("currency", "")

        alerts = []

        if amount >= self.SUSPICIOUS_TX_THRESHOLD:
            alerts.append(await self._create_alert(
                AlertType.SUSPICIOUS_TRANSACTION,
                AlertSeverity.CRITICAL,
                f"Suspicious transaction: {amount} {currency} (org {org_id})",
                {"transaction_id": transaction.get("id"), "amount": amount, "org_id": org_id},
            ))
        elif amount >= self.LARGE_TX_THRESHOLD:
            alerts.append(await self._create_alert(
                AlertType.LARGE_TRANSACTION,
                AlertSeverity.WARNING,
                f"Large transaction: {amount} {currency} (org {org_id})",
                {"transaction_id": transaction.get("id"), "amount": amount, "org_id": org_id},
            ))

        # Check frequency — multiple large txs in short time
        if amount >= self.LARGE_TX_THRESHOLD:
            try:
                async with self.db.acquire() as conn:
                    recent = await conn.fetchval(
                        """SELECT COUNT(*) FROM transactions 
                           WHERE organization_id = $1 
                           AND created_at > NOW() - INTERVAL 1 hour
                           AND CAST(amount AS NUMERIC) >= $2""",
                        org_id, self.LARGE_TX_THRESHOLD
                    )
                    if recent and recent >= 5:
                        alerts.append(await self._create_alert(
                            AlertType.SUSPICIOUS_TRANSACTION,
                            AlertSeverity.CRITICAL,
                            f"Unusual frequency: {recent} large transactions in 1h (org {org_id})",
                            {"org_id": org_id, "count": recent},
                        ))
            except Exception as e:
                logger.error(f"Failed to check tx frequency: {e}")

        for alert in alerts:
            await self._dispatch(alert, org_id)

    # ---- Brute Force Detection ----

    async def record_failed_login(self, ip: str, email: str):
        """Record failed login and check for brute force."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=self.FAILED_LOGIN_WINDOW_MINUTES)

        if ip not in self._failed_logins:
            self._failed_logins[ip] = []

        self._failed_logins[ip] = [t for t in self._failed_logins[ip] if t > cutoff]
        self._failed_logins[ip].append(now)

        if len(self._failed_logins[ip]) >= self.MAX_FAILED_LOGINS:
            alert = await self._create_alert(
                AlertType.BRUTE_FORCE,
                AlertSeverity.CRITICAL,
                f"Brute force detected: {len(self._failed_logins[ip])} failed logins from {ip} in {self.FAILED_LOGIN_WINDOW_MINUTES}min (last email: {email})",
                {"ip": ip, "email": email, "attempts": len(self._failed_logins[ip])},
            )
            await self._dispatch(alert)
            self._failed_logins[ip] = []  # Reset after alert

    # ---- Service Health ----

    async def check_services_health(self):
        """Check external service health and alert on degradation."""
        import httpx

        services = {
            "docling": "https://docling.asystem.ai/health",
            "onlyoffice": "https://office.asystem.ai/healthcheck",
        }

        for name, url in services.items():
            try:
                async with httpx.AsyncClient(timeout=10, verify=False) as client:
                    r = await client.get(url)
                    if r.status_code >= 400:
                        alert = await self._create_alert(
                            AlertType.SERVICE_DEGRADED,
                            AlertSeverity.WARNING,
                            f"Service degraded: {name} returned {r.status_code}",
                            {"service": name, "status_code": r.status_code},
                        )
                        await self._dispatch(alert)
            except Exception as e:
                alert = await self._create_alert(
                    AlertType.SERVICE_DEGRADED,
                    AlertSeverity.CRITICAL,
                    f"Service unreachable: {name} — {str(e)[:100]}",
                    {"service": name, "error": str(e)[:200]},
                )
                await self._dispatch(alert)

    # ---- KYC/KYB Backlog ----

    async def check_kyc_backlog(self):
        """Check for KYC/KYB submission backlog."""
        try:
            async with self.db.acquire() as conn:
                pending = await conn.fetchval(
                    "SELECT COUNT(*) FROM users WHERE kyc_status = pending"
                )
                if pending and pending >= self.KYC_BACKLOG_THRESHOLD:
                    alert = await self._create_alert(
                        AlertType.KYC_BACKLOG,
                        AlertSeverity.WARNING,
                        f"KYC backlog: {pending} pending submissions",
                        {"pending_count": pending},
                    )
                    await self._dispatch(alert)
        except Exception as e:
            logger.warning(f"KYC backlog check failed: {e}")

    # ---- Internal ----

    async def _create_alert(self, alert_type: AlertType, severity: AlertSeverity, message: str, data: dict = None) -> dict:
        """Create alert record."""
        alert = {
            "type": alert_type.value,
            "severity": severity.value,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.warning(f"ALERT [{severity.value}] {alert_type.value}: {message}")

        # Persist to DB
        try:
            async with self.db.acquire() as conn:
                await conn.execute(
                    """INSERT INTO alerts (type, severity, message, data, created_at)
                       VALUES ($1, $2, $3, $4::jsonb, NOW())
                       ON CONFLICT DO NOTHING""",
                    alert_type.value, severity.value, message,
                    __import__("json").dumps(data or {}),
                )
        except Exception as e:
            logger.debug(f"Alert persistence failed (table may not exist): {e}")

        return alert

    async def _dispatch(self, alert: dict, org_id: int = None):
        """Send alert via notification service."""
        if not self.notification:
            return

        try:
            # Send to platform admins via WebSocket
            from backend.websocket_manager import ws_manager
            await ws_manager.broadcast_to_role("platform_admin", {
                "type": "alert",
                "alert": alert,
            })
        except Exception as e:
            logger.debug(f"WS dispatch failed: {e}")

        # Future: Telegram integration
        if self.notification and hasattr(self.notification, "telegram") and self.notification.telegram:
            try:
                await self.notification.telegram.send_alert(
                    f"🚨 [{alert[severity].upper()}] {alert[message]}"
                )
            except Exception:
                pass
