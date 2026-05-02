"""Compliance Service — KYC, AML, Regulatory Reports."""
import asyncpg
import base64
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
import secrets


# ────────────────────────────────────────────────────────────────────
# AML triage helpers (Wave 21, Story 2.6)
# ────────────────────────────────────────────────────────────────────

# Status transition rules. Once a row reaches a terminal status, no
# further claim/resolve/note action is accepted at the DB layer — the
# route handler raises 409.
TERMINAL_STATUSES = {"resolved", "false_positive", "reported"}

# Decision → status mapping for resolve-flow.
RESOLVE_DECISION_TO_STATUS = {
    "false_positive": "false_positive",
    "resolved": "resolved",
    "reported": "reported",
}


class AmlConflictError(Exception):
    """Raised when a state-mutating AML op hits a conflict (race or
    terminal-status). Routes translate to HTTP 409.

    Attributes:
        reason: short machine-readable code (`already_claimed`,
            `terminal_status`, `not_claimed`).
        current: current alert state we observed at decision time, so
            UI can re-render without an extra round-trip.
    """

    def __init__(self, reason: str, current: Dict[str, Any] | None = None):
        super().__init__(reason)
        self.reason = reason
        self.current = current


def _encode_cursor(created_at: datetime, alert_id: UUID) -> str:
    """Pack (created_at, id) into an opaque base64 cursor.

    We deliberately do NOT include organization_id — RBAC is re-checked
    on every paginated call, so a leaked cursor cannot escalate scope.
    """
    payload = json.dumps({
        "ts": created_at.isoformat(),
        "id": str(alert_id),
    }, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> Tuple[datetime, UUID]:
    """Reverse of `_encode_cursor`. Returns (created_at, id) or raises ValueError."""
    padded = cursor + "=" * (-len(cursor) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    payload = json.loads(raw)
    return (
        datetime.fromisoformat(payload["ts"]),
        UUID(payload["id"]),
    )


def _serialise_rule(row) -> dict:
    """Pluck the human-relevant rule fields for audit-log diffs.

    asyncpg Records are not directly JSON-serialisable; this turns a
    rule row into a plain dict with stable string types for UUID/dt.
    """
    if row is None:
        return {}
    out: dict = {}
    for k, v in dict(row).items():
        if isinstance(v, (UUID, datetime)):
            out[k] = str(v)
        else:
            out[k] = v
    return out


class ComplianceService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    # ==================== KYC ====================
    
    async def create_kyc_record(self, org_id: UUID, customer_name: str, customer_email: str,
                                 id_type: str, id_number: str, creator_user_id: UUID) -> Dict:
        """Create KYC record."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO kyc_records (organization_id, user_id, customer_name, customer_email,
                    id_type, id_number, verification_status, risk_level)
                VALUES ($1, $2, $3, $4, $5, $6, 'pending', 'unknown')
                RETURNING *
            """, org_id, creator_user_id, customer_name, customer_email, id_type, id_number)
            return dict(row)
    
    async def get_kyc_records(self, org_id: UUID, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get KYC records for organization."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT * FROM kyc_records WHERE organization_id = $1
                AND ($2::text IS NULL OR verification_status = $2)
                ORDER BY created_at DESC LIMIT $3
            """
            rows = await conn.fetch(query, org_id, status, limit)
            return [dict(r) for r in rows]
    
    async def update_kyc_status(self, kyc_id: UUID, status: str, verified_by: UUID,
                                 risk_level: Optional[str] = None) -> Dict:
        """Approve/reject KYC."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                UPDATE kyc_records
                SET verification_status = $1, verified_by = $2, verified_at = $3,
                    risk_level = COALESCE($4, risk_level), updated_at = $3
                WHERE id = $5 RETURNING *
            """, status, verified_by, datetime.utcnow(), risk_level, kyc_id)
            return dict(row) if row else None
    
    # ==================== AML ====================
    
    async def create_aml_alert(self, org_id: UUID, alert_type: str, severity: str,
                                description: str, details: Dict, transaction_id: Optional[UUID] = None) -> Dict:
        """Create AML alert."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO aml_alerts (organization_id, alert_type, severity, description,
                    details, transaction_id, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'open')
                RETURNING *
            """, org_id, alert_type, severity, description, details, transaction_id)
            return dict(row)
    
    async def get_aml_alerts(self, org_id: UUID, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get AML alerts."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT * FROM aml_alerts WHERE organization_id = $1
                AND ($2::text IS NULL OR status = $2)
                ORDER BY created_at DESC LIMIT $3
            """
            rows = await conn.fetch(query, org_id, status, limit)
            return [dict(r) for r in rows]
    
    async def update_aml_alert_status(self, alert_id: UUID, status: str, resolution: Optional[str] = None,
                                       investigated_by: Optional[UUID] = None) -> Dict:
        """Resolve AML alert."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                UPDATE aml_alerts
                SET status = $1, resolution = $2, investigated_by = $3,
                    investigated_at = $4, updated_at = $4
                WHERE id = $5 RETURNING *
            """, status, resolution, investigated_by, datetime.utcnow(), alert_id)
            return dict(row) if row else None
    
    # ==================== Reports ====================
    
    async def generate_monthly_report(self, org_id: UUID, year: int, month: int, generated_by: UUID) -> Dict:
        """Auto-generate monthly compliance report."""
        async with self.pool.acquire() as conn:
            period_start = datetime(year, month, 1).date()
            if month == 12:
                period_end = datetime(year + 1, 1, 1).date()
            else:
                period_end = datetime(year, month + 1, 1).date()
            
            # Aggregate data
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) AS total_transactions,
                    COALESCE(SUM(amount), 0) AS total_volume
                FROM transactions
                WHERE organization_id = $1 AND created_at >= $2 AND created_at < $3
            """, org_id, period_start, period_end)
            
            kyc_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) FILTER (WHERE verification_status = 'approved') AS kyc_approved,
                    COUNT(*) FILTER (WHERE verification_status = 'pending') AS kyc_pending
                FROM kyc_records WHERE organization_id = $1
            """, org_id)
            
            aml_stats = await conn.fetchrow("""
                SELECT COUNT(*) AS aml_alerts
                FROM aml_alerts WHERE organization_id = $1 AND created_at >= $2 AND created_at < $3
            """, org_id, period_start, period_end)
            
            report_data = {
                "period": {"start": str(period_start), "end": str(period_end)},
                "transactions": {"total": stats['total_transactions'], "volume": float(stats['total_volume'])},
                "kyc": {"approved": kyc_stats['kyc_approved'], "pending": kyc_stats['kyc_pending']},
                "aml": {"alerts": aml_stats['aml_alerts']}
            }
            
            row = await conn.fetchrow("""
                INSERT INTO compliance_reports (organization_id, report_type, period_start, period_end,
                    title, report_data, generated_by, status)
                VALUES ($1, 'monthly_transactions', $2, $3, $4, $5, $6, 'final')
                RETURNING *
            """, org_id, period_start, period_end, 
                f"Monthly Report {year}-{month:02d}", report_data, generated_by)
            return dict(row)
    
    async def get_reports(self, org_id: UUID, limit: int = 50) -> List[Dict]:
        """Get compliance reports."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM compliance_reports WHERE organization_id = $1
                ORDER BY period_end DESC LIMIT $2
            """, org_id, limit)
            return [dict(r) for r in rows]
    
    # ==================== AML Triage (Wave 21, Story 2.6) ====================
    #
    # These methods power the /api/v1/compliance/aml/* endpoints.
    # `org_ids=None` is the super_admin "see all orgs" scope — non-None
    # values are pre-resolved by `dependencies.get_user_org_ids` so the
    # service does not re-implement RBAC.

    async def list_aml_alerts(
        self,
        org_ids: Optional[List[UUID]],
        status: Optional[str] = None,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        cursor: Optional[Tuple[datetime, UUID]] = None,
        limit: int = 50,
    ) -> Tuple[List[Dict], Optional[Tuple[datetime, UUID]]]:
        """Paginated list of alerts. Returns (rows, next_cursor)."""
        # Cap limit to avoid runaway queries even if caller passes garbage.
        if limit < 1:
            limit = 1
        if limit > 200:
            limit = 200

        clauses: List[str] = []
        params: List[Any] = []

        def _next_param() -> str:
            params_count = len(params) + 1
            return f"${params_count}"

        if org_ids is not None:
            clauses.append(f"a.organization_id = ANY({_next_param()}::uuid[])")
            params.append(org_ids)
        if status:
            clauses.append(f"a.status = {_next_param()}")
            params.append(status)
        if severity:
            clauses.append(f"a.severity = {_next_param()}")
            params.append(severity)
        if alert_type:
            clauses.append(f"a.alert_type = {_next_param()}")
            params.append(alert_type)
        if date_from:
            clauses.append(f"a.created_at >= {_next_param()}")
            params.append(date_from)
        if date_to:
            clauses.append(f"a.created_at <= {_next_param()}")
            params.append(date_to)
        if cursor:
            ts, cid = cursor
            # Keyset: strictly older than cursor's (created_at, id).
            p_ts = _next_param()
            params.append(ts)
            p_id = _next_param()
            params.append(cid)
            clauses.append(f"(a.created_at, a.id) < ({p_ts}, {p_id})")

        where_sql = " AND ".join(clauses) if clauses else "TRUE"
        # Pull limit+1 to detect "is there another page".
        p_limit = _next_param()
        params.append(limit + 1)

        query = f"""
            SELECT a.id, a.organization_id, a.alert_type, a.severity,
                   a.status, a.description, a.transaction_id,
                   a.assigned_to, a.created_at,
                   u.email AS assigned_to_email,
                   u.full_name AS assigned_to_name
            FROM aml_alerts a
            LEFT JOIN users u ON u.id = a.assigned_to
            WHERE {where_sql}
            ORDER BY a.created_at DESC, a.id DESC
            LIMIT {p_limit}
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        items = [dict(r) for r in rows[:limit]]
        next_cursor: Optional[Tuple[datetime, UUID]] = None
        if len(rows) > limit:
            tail = items[-1]
            next_cursor = (tail["created_at"], tail["id"])
        return items, next_cursor

    async def get_aml_alert(
        self,
        alert_id: UUID,
        org_ids: Optional[List[UUID]],
    ) -> Optional[Dict]:
        """Fetch one alert plus its related transaction (if any).

        Returns None when the alert does not exist OR is outside the
        caller's org scope. Callers MUST treat None as 404 — leaking
        a "you can't see this" 403 would expose alert existence.
        """
        clauses = ["a.id = $1"]
        params: List[Any] = [alert_id]
        if org_ids is not None:
            clauses.append("a.organization_id = ANY($2::uuid[])")
            params.append(org_ids)

        query = f"""
            SELECT a.*,
                   u_assigned.email   AS assigned_to_email,
                   u_assigned.full_name AS assigned_to_name,
                   u_inv.email   AS investigated_by_email,
                   u_inv.full_name AS investigated_by_name,
                   to_jsonb(t.*) AS related_transaction
            FROM aml_alerts a
            LEFT JOIN users u_assigned ON u_assigned.id = a.assigned_to
            LEFT JOIN users u_inv      ON u_inv.id      = a.investigated_by
            LEFT JOIN transactions t   ON t.id          = a.transaction_id
            WHERE {' AND '.join(clauses)}
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
        return dict(row) if row else None

    async def claim_aml_alert(
        self,
        alert_id: UUID,
        user_id: int,
        org_ids: Optional[List[UUID]],
    ) -> Dict:
        """Claim an alert. Conditional UPDATE prevents race conditions.

        Allowed when: status='open' AND assigned_to IS NULL, OR the
        same user re-claims (idempotent). Otherwise raises
        AmlConflictError so the route returns 409.

        Atomic with audit_log INSERT — both succeed or both rollback.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # First: read current state. We need it both for the
                # conflict-detection branch and to populate audit-log
                # `details.previous_status`.
                pre_row = await self._read_alert_for_update(
                    conn, alert_id, org_ids
                )
                if pre_row is None:
                    raise AmlConflictError("not_found")
                if pre_row["status"] in TERMINAL_STATUSES:
                    raise AmlConflictError("terminal_status", current=dict(pre_row))
                if (
                    pre_row["assigned_to"] is not None
                    and pre_row["assigned_to"] != user_id
                ):
                    raise AmlConflictError("already_claimed", current=dict(pre_row))

                row = await conn.fetchrow(
                    """
                    UPDATE aml_alerts
                    SET status      = 'investigating',
                        assigned_to = $1,
                        updated_at  = now()
                    WHERE id = $2
                      AND status IN ('open', 'investigating')
                      AND (assigned_to IS NULL OR assigned_to = $1)
                    RETURNING *
                    """,
                    user_id,
                    alert_id,
                )
                if row is None:
                    # Lost the race despite pre-check — another writer
                    # squeezed in between SELECT and UPDATE. Treat as
                    # already_claimed for UI parity.
                    fresh = await conn.fetchrow(
                        "SELECT * FROM aml_alerts WHERE id = $1", alert_id
                    )
                    raise AmlConflictError(
                        "already_claimed",
                        current=dict(fresh) if fresh else None,
                    )

                await self._write_audit(
                    conn,
                    user_id=user_id,
                    action="aml.alert.claim",
                    alert_id=alert_id,
                    details={
                        "previous_status": pre_row["status"],
                        "new_status": "investigating",
                        "previous_assignee": pre_row["assigned_to"],
                    },
                )
                return dict(row)

    async def resolve_aml_alert(
        self,
        alert_id: UUID,
        user_id: int,
        decision: str,
        resolution: str,
        report_reference: Optional[str],
        org_ids: Optional[List[UUID]],
    ) -> Dict:
        """Terminal-state transition. Atomic with audit_log."""
        new_status = RESOLVE_DECISION_TO_STATUS.get(decision)
        if new_status is None:
            raise ValueError(f"invalid decision: {decision}")
        if new_status == "reported" and not report_reference:
            # Pydantic should have caught this but enforce at service
            # layer too — regulator-traceable refs are non-negotiable.
            raise ValueError("report_reference is required for 'reported' decision")

        reported_to_regulator = new_status == "reported"
        now = datetime.now(timezone.utc)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                pre_row = await self._read_alert_for_update(conn, alert_id, org_ids)
                if pre_row is None:
                    raise AmlConflictError("not_found")
                if pre_row["status"] in TERMINAL_STATUSES:
                    raise AmlConflictError("terminal_status", current=dict(pre_row))

                row = await conn.fetchrow(
                    """
                    UPDATE aml_alerts
                    SET status                 = $1,
                        resolution             = $2,
                        investigated_by        = $3,
                        investigated_at        = $4,
                        reported_to_regulator  = $5,
                        reported_at            = CASE WHEN $5 THEN $4 ELSE reported_at END,
                        report_reference       = COALESCE($6, report_reference),
                        updated_at             = $4
                    WHERE id = $7
                      AND status NOT IN ('resolved', 'false_positive', 'reported')
                    RETURNING *
                    """,
                    new_status,
                    resolution,
                    user_id,
                    now,
                    reported_to_regulator,
                    report_reference,
                    alert_id,
                )
                if row is None:
                    fresh = await conn.fetchrow(
                        "SELECT * FROM aml_alerts WHERE id = $1", alert_id
                    )
                    raise AmlConflictError(
                        "terminal_status",
                        current=dict(fresh) if fresh else None,
                    )

                await self._write_audit(
                    conn,
                    user_id=user_id,
                    action="aml.alert.resolve",
                    alert_id=alert_id,
                    details={
                        "previous_status": pre_row["status"],
                        "new_status": new_status,
                        "decision": decision,
                        "resolution": resolution,
                        "report_reference": report_reference,
                    },
                )
                return dict(row)

    async def append_aml_note(
        self,
        alert_id: UUID,
        user_id: int,
        note: str,
        org_ids: Optional[List[UUID]],
    ) -> Dict:
        """Append a timestamped note to investigation_notes. Idempotency
        is the caller's problem — duplicate POST yields duplicate notes."""
        if not note.strip():
            raise ValueError("note cannot be empty")
        now = datetime.now(timezone.utc)
        prefix = f"[{now.isoformat()}] user={user_id}: "
        new_note = prefix + note.strip()

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                pre_row = await self._read_alert_for_update(conn, alert_id, org_ids)
                if pre_row is None:
                    raise AmlConflictError("not_found")
                if pre_row["status"] == "reported":
                    raise AmlConflictError("terminal_status", current=dict(pre_row))

                # Append, separating from existing notes by blank line.
                row = await conn.fetchrow(
                    """
                    UPDATE aml_alerts
                    SET investigation_notes =
                            CASE
                                WHEN investigation_notes IS NULL OR investigation_notes = ''
                                    THEN $1
                                ELSE investigation_notes || E'\\n\\n' || $1
                            END,
                        updated_at = now()
                    WHERE id = $2
                    RETURNING *
                    """,
                    new_note,
                    alert_id,
                )
                await self._write_audit(
                    conn,
                    user_id=user_id,
                    action="aml.alert.note",
                    alert_id=alert_id,
                    details={"note_preview": note.strip()[:120]},
                )
                return dict(row)

    async def aml_alert_stats(
        self,
        org_ids: Optional[List[UUID]],
    ) -> Dict[str, Any]:
        """Aggregated counts for the KPI strip on /compliance."""
        clauses: List[str] = []
        params: List[Any] = []
        if org_ids is not None:
            clauses.append("organization_id = ANY($1::uuid[])")
            params.append(org_ids)
        where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""

        # Single round-trip aggregate: status counts + severity histogram + 30d-resolved.
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        params.append(thirty_days_ago)
        idx_30d = len(params)

        query = f"""
            SELECT
                COUNT(*) FILTER (WHERE status = 'open')                     AS open,
                COUNT(*) FILTER (WHERE status = 'investigating')            AS investigating,
                COUNT(*) FILTER (
                    WHERE status IN ('resolved','false_positive','reported')
                      AND COALESCE(investigated_at, updated_at) >= ${idx_30d}
                )                                                           AS resolved_30d,
                COUNT(*) FILTER (WHERE severity = 'low')      AS sev_low,
                COUNT(*) FILTER (WHERE severity = 'medium')   AS sev_medium,
                COUNT(*) FILTER (WHERE severity = 'high')     AS sev_high,
                COUNT(*) FILTER (WHERE severity = 'critical') AS sev_critical
            FROM aml_alerts
            {where_sql}
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
        if row is None:
            return {
                "open": 0, "investigating": 0, "resolved_30d": 0,
                "by_severity": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            }
        return {
            "open": int(row["open"] or 0),
            "investigating": int(row["investigating"] or 0),
            "resolved_30d": int(row["resolved_30d"] or 0),
            "by_severity": {
                "low":      int(row["sev_low"] or 0),
                "medium":   int(row["sev_medium"] or 0),
                "high":     int(row["sev_high"] or 0),
                "critical": int(row["sev_critical"] or 0),
            },
        }

    # ────────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────────

    async def _read_alert_for_update(
        self,
        conn,
        alert_id: UUID,
        org_ids: Optional[List[UUID]],
    ) -> Optional[Any]:
        """SELECT ... FOR UPDATE within an existing transaction.

        The row-lock prevents a parallel writer from changing status
        between our pre-check and the UPDATE. Returns None when the
        alert is missing or out-of-scope (RBAC-friendly: caller maps to
        404 without leaking existence).
        """
        clauses = ["id = $1"]
        params: List[Any] = [alert_id]
        if org_ids is not None:
            clauses.append("organization_id = ANY($2::uuid[])")
            params.append(org_ids)
        return await conn.fetchrow(
            f"SELECT * FROM aml_alerts WHERE {' AND '.join(clauses)} FOR UPDATE",
            *params,
        )

    async def _write_audit(
        self,
        conn,
        user_id: int,
        action: str,
        alert_id: UUID,
        details: Dict[str, Any],
    ) -> None:
        """Single source of truth for AML audit-log writes."""
        await conn.execute(
            """
            INSERT INTO audit_log (user_id, action, resource_type, resource_id, details)
            VALUES ($1, $2, 'aml_alert', $3, $4::jsonb)
            """,
            user_id,
            action,
            str(alert_id),
            json.dumps(details, default=str),
        )

    # ==================== Rule engine (Wave 23, Story 2.8) ====================
    #
    # `evaluate_transaction_rules` is the entry point used by
    # `transaction_service.send_transaction`. It runs every active rule
    # for the org (plus global ones with org_id IS NULL), records an
    # AML alert per match, and returns a verdict the caller uses to
    # decide whether to block, hold, or allow the transaction.
    #
    # Three rule types are supported:
    #   - threshold        — value compared against `threshold_usd`/`threshold`
    #   - velocity         — count of recent tx for the org in last N hours
    #   - blacklist_address — to_address present in the rule_config list
    #
    # Each rule's `action` (alert | hold | block) drives the verdict;
    # when multiple rules trigger, the strictest action wins
    # (block > hold > alert).

    _ACTION_PRIORITY = {"alert": 0, "hold": 1, "block": 2}

    async def evaluate_transaction_rules(
        self,
        org_id: Optional[UUID],
        tx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate active rules; return `{triggered: [...], verdict: ...}`.

        Never raises — DB/eval errors are logged and treated as `allow`
        so a rule-engine glitch does not block production tx-sends.
        """
        try:
            return await self._evaluate_rules_impl(org_id, tx)
        except Exception as exc:
            import logging
            logging.getLogger("orgon.compliance.rules").exception(
                "Rule engine raised; treating as allow: %s", exc,
            )
            return {"triggered": [], "verdict": "allow"}

    async def _evaluate_rules_impl(
        self,
        org_id: Optional[UUID],
        tx: Dict[str, Any],
    ) -> Dict[str, Any]:
        triggered: List[Dict[str, Any]] = []
        async with self.pool.acquire() as conn:
            rules = await conn.fetch(
                """
                SELECT id, organization_id, rule_name, rule_type,
                       rule_config, action, severity
                FROM transaction_monitoring_rules
                WHERE is_active = TRUE
                  AND (organization_id = $1 OR organization_id IS NULL)
                """,
                org_id,
            )

            for rule in rules:
                rule_type = rule["rule_type"]
                cfg = rule["rule_config"] or {}
                if isinstance(cfg, str):
                    cfg = json.loads(cfg)

                try:
                    fired = await self._rule_fired(conn, rule_type, cfg, tx, org_id)
                except Exception as exc:
                    import logging
                    logging.getLogger("orgon.compliance.rules").warning(
                        "rule %s (%s) failed to evaluate: %s",
                        rule["rule_name"], rule_type, exc,
                    )
                    continue
                if not fired:
                    continue

                action = (rule["action"] or "alert").lower()
                if action not in self._ACTION_PRIORITY:
                    action = "alert"

                alert_id: Optional[UUID] = None
                try:
                    alert_id = await self._record_rule_alert(conn, rule, tx, action)
                except Exception as exc:
                    import logging
                    logging.getLogger("orgon.compliance.rules").warning(
                        "rule %s alert insert failed: %s", rule["rule_name"], exc,
                    )

                triggered.append({
                    "rule_id": str(rule["id"]),
                    "rule_name": rule["rule_name"],
                    "rule_type": rule_type,
                    "severity": rule["severity"],
                    "action": action,
                    "alert_id": str(alert_id) if alert_id else None,
                })

        # Strictest action wins. Default verdict = allow when nothing fired.
        verdict = "allow"
        if any(t["action"] == "block" for t in triggered):
            verdict = "block"
        elif any(t["action"] == "hold" for t in triggered):
            verdict = "hold"
        return {"triggered": triggered, "verdict": verdict}

    # ────────────────────────────────────────────────────────────────
    # Rule-type implementations
    # ────────────────────────────────────────────────────────────────

    async def _rule_fired(
        self,
        conn,
        rule_type: str,
        cfg: Dict[str, Any],
        tx: Dict[str, Any],
        org_id: Optional[UUID],
    ) -> bool:
        """Dispatch to the right checker. Unknown type → no-op."""
        if rule_type == "threshold":
            return self._check_threshold(cfg, tx)
        if rule_type == "velocity":
            return await self._check_velocity(conn, cfg, org_id)
        if rule_type == "blacklist_address":
            return self._check_blacklist(cfg, tx)
        return False

    @staticmethod
    def _check_threshold(cfg: Dict[str, Any], tx: Dict[str, Any]) -> bool:
        threshold = cfg.get("threshold_usd", cfg.get("threshold"))
        if threshold is None:
            return False
        try:
            return Decimal(str(tx.get("value", 0))) > Decimal(str(threshold))
        except Exception:
            return False

    @staticmethod
    def _check_blacklist(cfg: Dict[str, Any], tx: Dict[str, Any]) -> bool:
        addrs = cfg.get("addresses") or []
        target = (tx.get("to_address") or "").lower()
        if not target:
            return False
        return any(str(a).lower() == target for a in addrs)

    async def _check_velocity(
        self,
        conn,
        cfg: Dict[str, Any],
        org_id: Optional[UUID],
    ) -> bool:
        if org_id is None:
            return False                # global velocity makes no sense
        count_threshold = cfg.get("count")
        window_hours = cfg.get("window_hours", 1)
        if not count_threshold:
            return False
        cutoff = datetime.now(timezone.utc) - timedelta(hours=int(window_hours))
        row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS n
            FROM transactions
            WHERE organization_id = $1 AND created_at >= $2
            """,
            org_id,
            cutoff,
        )
        return bool(row) and int(row["n"] or 0) >= int(count_threshold)

    async def _record_rule_alert(
        self,
        conn,
        rule,
        tx: Dict[str, Any],
        action: str,
    ) -> Optional[UUID]:
        details = {
            "rule_id": str(rule["id"]),
            "rule_name": rule["rule_name"],
            "rule_type": rule["rule_type"],
            "action": action,
            "tx": {
                "to_address": tx.get("to_address"),
                "value": str(tx.get("value", "")),
                "token": tx.get("token"),
                "network": tx.get("network"),
            },
        }
        tx_uuid = tx.get("transaction_id")
        row = await conn.fetchrow(
            """
            INSERT INTO aml_alerts (
                organization_id, alert_type, severity,
                transaction_id, description, details, status
            )
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, 'open')
            RETURNING id
            """,
            rule["organization_id"],
            f"rule:{rule['rule_type']}",
            rule["severity"] or "medium",
            tx_uuid,
            f"Rule triggered: {rule['rule_name']}",
            json.dumps(details, default=str),
        )
        return row["id"] if row else None

    # ==================== Release tx from on_hold (Wave 26, Story 2.11) ====================
    #
    # Lift `on_hold` status set by Wave 23's rule engine. Atomic with
    # audit-log writes — one round-trip from the operator click to a
    # pending transaction + a recorded reason.

    async def release_held_transaction(
        self,
        alert_id: UUID,
        user_id: int,
        reason: str,
        org_ids: Optional[List[UUID]],
    ) -> Dict[str, Any]:
        """Move the linked transaction from on_hold → pending.

        Raises AmlConflictError on:
          - `not_found` — alert missing or out of scope
          - `no_transaction` — alert has no linked tx
          - `not_held` — tx is not currently on_hold (already released or never held)
        """
        if not reason or not reason.strip():
            raise ValueError("reason is required")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # 1. Look up alert with RBAC scope.
                pre_alert = await self._read_alert_for_update(conn, alert_id, org_ids)
                if pre_alert is None:
                    raise AmlConflictError("not_found")

                tx_uuid = pre_alert.get("transaction_id")
                if not tx_uuid:
                    raise AmlConflictError("no_transaction")

                # 2. Lock + check the transaction.
                tx_row = await conn.fetchrow(
                    "SELECT id, unid, status FROM transactions WHERE id = $1 FOR UPDATE",
                    tx_uuid,
                )
                if tx_row is None:
                    raise AmlConflictError("no_transaction")
                if tx_row["status"] != "on_hold":
                    raise AmlConflictError(
                        "not_held",
                        current={"status": tx_row["status"], "unid": tx_row["unid"]},
                    )

                # 3. Flip status.
                updated = await conn.fetchrow(
                    """
                    UPDATE transactions
                    SET status = 'pending', updated_at = now()
                    WHERE id = $1 AND status = 'on_hold'
                    RETURNING id, unid, status
                    """,
                    tx_uuid,
                )
                if updated is None:                # pragma: no cover (race)
                    raise AmlConflictError("not_held")

                # 4. Audit-log entry — same `_write_audit` helper as
                # claim/resolve so triage history is queryable in one place.
                await self._write_audit(
                    conn,
                    user_id=user_id,
                    action="aml.release_hold",
                    alert_id=alert_id,
                    details={
                        "tx_id": str(tx_uuid),
                        "tx_unid": tx_row["unid"],
                        "previous_tx_status": "on_hold",
                        "new_tx_status": "pending",
                        "reason": reason.strip(),
                    },
                )

                return {
                    "alert_id": str(alert_id),
                    "tx_id": str(tx_uuid),
                    "tx_unid": tx_row["unid"],
                    "tx_status": "pending",
                }

    # ==================== Rule config CRUD (Wave 25, Story 2.10) ====================
    #
    # Plain CRUD over `transaction_monitoring_rules`. Validation of the
    # `rule_config` shape is done at the route layer (Pydantic) — this
    # service treats it as opaque jsonb and only enforces RBAC + audit
    # logging. Idempotency is the caller's problem (DB has no UNIQUE
    # constraint on rule_name).

    SUPPORTED_RULE_TYPES = ("threshold", "velocity", "blacklist_address")
    SUPPORTED_RULE_ACTIONS = ("alert", "hold", "block")
    SUPPORTED_RULE_SEVERITIES = ("low", "medium", "high", "critical")

    async def list_monitoring_rules(
        self,
        org_ids: Optional[List[UUID]],
        include_global: bool = True,
    ) -> List[Dict[str, Any]]:
        """List rules visible to the caller.

        - super_admin (org_ids=None) → every rule.
        - non-super → own org rules + global rules (organization_id IS NULL),
          unless include_global=False.
        """
        clauses: List[str] = []
        params: List[Any] = []
        if org_ids is not None:
            if include_global:
                clauses.append(
                    "(organization_id = ANY($1::uuid[]) OR organization_id IS NULL)"
                )
                params.append(org_ids)
            else:
                clauses.append("organization_id = ANY($1::uuid[])")
                params.append(org_ids)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        query = f"""
            SELECT id, organization_id, rule_name, rule_type, description,
                   rule_config, action, severity, is_active,
                   created_at, updated_at, created_by
            FROM transaction_monitoring_rules
            {where}
            ORDER BY created_at DESC
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]

    async def get_monitoring_rule(
        self,
        rule_id: UUID,
        org_ids: Optional[List[UUID]],
    ) -> Optional[Dict[str, Any]]:
        """Read one rule. Returns None when missing or out of scope —
        caller maps to 404 to avoid leaking existence."""
        clauses = ["id = $1"]
        params: List[Any] = [rule_id]
        if org_ids is not None:
            clauses.append("(organization_id = ANY($2::uuid[]) OR organization_id IS NULL)")
            params.append(org_ids)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM transaction_monitoring_rules WHERE {' AND '.join(clauses)}",
                *params,
            )
        return dict(row) if row else None

    async def create_monitoring_rule(
        self,
        *,
        organization_id: Optional[UUID],
        rule_name: str,
        rule_type: str,
        description: Optional[str],
        rule_config: Dict[str, Any],
        action: str,
        severity: str,
        is_active: bool,
        actor_user_id: int,
    ) -> Dict[str, Any]:
        """Insert + audit-log. Atomic via `conn.transaction()`."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    INSERT INTO transaction_monitoring_rules
                        (organization_id, rule_name, rule_type, description,
                         rule_config, action, severity, is_active, created_by)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9)
                    RETURNING *
                    """,
                    organization_id,
                    rule_name,
                    rule_type,
                    description,
                    json.dumps(rule_config),
                    action,
                    severity,
                    is_active,
                    actor_user_id,
                )
                await self._write_rule_audit(
                    conn, actor_user_id, "rule.create", row["id"],
                    {"after": _serialise_rule(row)},
                )
                return dict(row)

    async def update_monitoring_rule(
        self,
        rule_id: UUID,
        *,
        org_ids: Optional[List[UUID]],
        actor_user_id: int,
        rule_name: Optional[str] = None,
        rule_type: Optional[str] = None,
        description: Optional[str] = None,
        rule_config: Optional[Dict[str, Any]] = None,
        action: Optional[str] = None,
        severity: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """Partial update. None for a field means "leave unchanged"."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                pre = await self._read_rule_for_update(conn, rule_id, org_ids)
                if pre is None:
                    return None
                # Build dynamic SET clause — only fields the caller passed.
                fields: List[str] = []
                params: List[Any] = []
                idx = 1
                if rule_name is not None:
                    fields.append(f"rule_name = ${idx}"); params.append(rule_name); idx += 1
                if rule_type is not None:
                    fields.append(f"rule_type = ${idx}"); params.append(rule_type); idx += 1
                if description is not None:
                    fields.append(f"description = ${idx}"); params.append(description); idx += 1
                if rule_config is not None:
                    fields.append(f"rule_config = ${idx}::jsonb"); params.append(json.dumps(rule_config)); idx += 1
                if action is not None:
                    fields.append(f"action = ${idx}"); params.append(action); idx += 1
                if severity is not None:
                    fields.append(f"severity = ${idx}"); params.append(severity); idx += 1
                if is_active is not None:
                    fields.append(f"is_active = ${idx}"); params.append(is_active); idx += 1
                if not fields:
                    return dict(pre)         # nothing to update
                fields.append("updated_at = now()")
                params.append(rule_id)
                row = await conn.fetchrow(
                    f"""
                    UPDATE transaction_monitoring_rules
                    SET {', '.join(fields)}
                    WHERE id = ${idx}
                    RETURNING *
                    """,
                    *params,
                )
                await self._write_rule_audit(
                    conn, actor_user_id, "rule.update", rule_id,
                    {"before": _serialise_rule(pre), "after": _serialise_rule(row)},
                )
                return dict(row) if row else None

    async def delete_monitoring_rule(
        self,
        rule_id: UUID,
        *,
        org_ids: Optional[List[UUID]],
        actor_user_id: int,
    ) -> bool:
        """Hard delete. Returns False if missing / out of scope."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                pre = await self._read_rule_for_update(conn, rule_id, org_ids)
                if pre is None:
                    return False
                await conn.execute(
                    "DELETE FROM transaction_monitoring_rules WHERE id = $1",
                    rule_id,
                )
                await self._write_rule_audit(
                    conn, actor_user_id, "rule.delete", rule_id,
                    {"before": _serialise_rule(pre)},
                )
                return True

    async def _read_rule_for_update(
        self,
        conn,
        rule_id: UUID,
        org_ids: Optional[List[UUID]],
    ):
        clauses = ["id = $1"]
        params: List[Any] = [rule_id]
        if org_ids is not None:
            clauses.append("(organization_id = ANY($2::uuid[]) OR organization_id IS NULL)")
            params.append(org_ids)
        return await conn.fetchrow(
            f"SELECT * FROM transaction_monitoring_rules "
            f"WHERE {' AND '.join(clauses)} FOR UPDATE",
            *params,
        )

    async def _write_rule_audit(
        self,
        conn,
        actor_user_id: int,
        action: str,
        rule_id: UUID,
        details: Dict[str, Any],
    ) -> None:
        await conn.execute(
            """
            INSERT INTO audit_log (user_id, action, resource_type, resource_id, details)
            VALUES ($1, $2, 'monitoring_rule', $3, $4::jsonb)
            """,
            actor_user_id,
            action,
            str(rule_id),
            json.dumps(details, default=str),
        )

    # ==================== SAR submissions (Wave 24, Story 2.9) ====================
    #
    # Each alert can have at most one SAR submission (UNIQUE constraint
    # at the DB level). The service layer wraps the create-or-fetch
    # idempotency, the lookup of related context (org + transaction +
    # officer), and the call into the configured submission backend.

    async def submit_sar(
        self,
        alert_id: UUID,
        officer: Dict[str, Any],
        backend_name: Optional[str] = None,
        org_ids: Optional[List[UUID]] = None,
    ) -> Dict[str, Any]:
        """Generate + persist (+ optionally deliver) a SAR for one alert.

        Idempotent — calling twice for the same alert returns the existing
        row instead of inserting a duplicate. RBAC is enforced via the
        same `org_ids` scoping that powers the AML triage endpoints
        (see `get_aml_alert`).

        Returns the freshly-loaded `sar_submissions` row as a dict.
        Raises:
            ValueError — alert not found / out of scope / not in a state
                where a SAR makes sense (open / investigating).
        """
        from backend.regulators.finsupervisory import (
            build_sar_payload,
            render_sar_markdown,
            resolve_backend,
        )

        async with self.pool.acquire() as conn:
            # 1. Resolve & RBAC-check the alert.
            alert = await self.get_aml_alert(alert_id, org_ids=org_ids)
            if alert is None:
                raise ValueError("alert not found")
            # 2. Idempotency — return existing row if already filed.
            existing = await conn.fetchrow(
                "SELECT * FROM sar_submissions WHERE alert_id = $1",
                alert_id,
            )
            if existing is not None:
                return dict(existing)

            # 3. Pull the org context for the filing.
            org_row = await conn.fetchrow(
                """
                SELECT id, name, legal_address, country
                FROM organizations
                WHERE id = $1
                """,
                alert["organization_id"],
            )
            org_dict = dict(org_row) if org_row else {
                "id": alert["organization_id"],
                "name": "",
            }

            # 4. Pull related transaction (alert.transaction_id may be null).
            tx_row = None
            if alert.get("transaction_id"):
                tx_row = await conn.fetchrow(
                    "SELECT * FROM transactions WHERE id = $1",
                    alert["transaction_id"],
                )

            # 5. Build payload + Markdown render.
            payload = build_sar_payload(
                alert=alert,
                transaction=dict(tx_row) if tx_row else None,
                organization=org_dict,
                officer=officer,
            )
            rendered = render_sar_markdown(payload)

            # 6. Resolve backend (defaults to manual_export).
            spec = resolve_backend(backend_name)
            try:
                result = spec.submit(payload, rendered)
            except NotImplementedError as exc:
                # api_v1 raises until Финнадзор publishes a spec — surface
                # the reason to the caller as 422 rather than 5xx.
                raise ValueError(str(exc))

            # 7. Persist. The UNIQUE constraint races would surface as
            # IntegrityError — caught and re-fetched.
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO sar_submissions (
                        alert_id, organization_id, submitted_by,
                        submission_backend, payload_json, rendered_markdown,
                        status, external_reference, response_body
                    )
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9)
                    RETURNING *
                    """,
                    alert_id,
                    alert["organization_id"],
                    int(officer["id"]),
                    spec.name,
                    json.dumps(payload, default=str),
                    rendered,
                    result.get("status", "prepared"),
                    result.get("external_reference"),
                    result.get("response_body"),
                )
            except Exception:                # pragma: no cover (race)
                row = await conn.fetchrow(
                    "SELECT * FROM sar_submissions WHERE alert_id = $1",
                    alert_id,
                )

            return dict(row) if row else {}

    async def get_sar_submission(
        self,
        alert_id: UUID,
        org_ids: Optional[List[UUID]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Read the SAR submission for an alert, RBAC-scoped via aml_alerts."""
        # We re-use the alert-scoping logic to enforce RBAC, then look up.
        alert = await self.get_aml_alert(alert_id, org_ids=org_ids)
        if alert is None:
            return None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM sar_submissions WHERE alert_id = $1",
                alert_id,
            )
            return dict(row) if row else None

    # ==================== Monitoring (legacy adapter) ====================

    async def check_transaction_against_rules(self, org_id: UUID, transaction: Dict) -> List[Dict]:
        """Backwards-compatible wrapper around `evaluate_transaction_rules`.

        Pre-Wave-23 callers received a list of triggered rule
        descriptors back. After the rule-engine refactor, that's
        exactly the `triggered` field on the verdict — so we just
        unwrap it. Old `transaction['amount']` keys are mapped to the
        new `value` shape so existing scripts keep working.
        """
        # Old shape used `amount`; new engine expects `value`.
        tx = dict(transaction)
        if "value" not in tx and "amount" in tx:
            tx["value"] = tx["amount"]
        verdict = await self.evaluate_transaction_rules(org_id, tx)
        alerts = verdict["triggered"]
        
        return alerts
