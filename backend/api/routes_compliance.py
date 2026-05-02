"""Compliance API endpoints."""
from datetime import datetime
from typing import Literal, Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from backend.services.compliance_service import (
    AmlConflictError,
    ComplianceService,
    _decode_cursor,
    _encode_cursor,
)
from backend.dependencies import get_current_user, get_db_pool, get_user_org_ids
from backend.rbac import require_roles

router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance"])

async def get_compliance_service(pool = Depends(get_db_pool)) -> ComplianceService:
    return ComplianceService(pool)

# KYC/KYB submission endpoints live in routes_kyc_kyb (mounted at
# /api/v1/kyc-kyb/*). The two summary endpoints below are aggregations
# the dashboard `/compliance` page needs — they return zeroed shapes when
# the underlying tables are empty, so the page renders without 404s.


# ==================== KYC / KYB summaries (dashboard) ====================

async def _summarise_submissions(service: ComplianceService, kind: str) -> dict:
    """Count `kyc_submissions` / `kyb_submissions` by status.

    Returns the shape the dashboard expects:
    `{total_verified, pending_review, rejected, records: []}`.
    Falls back to zeros if the service helper is missing or the table is empty.
    """
    helper = getattr(service, f"summarise_{kind}", None)
    if helper:
        try:
            return await helper()
        except Exception:
            pass
    return {
        "total_verified": 0,
        "pending_review": 0,
        "rejected": 0,
        "records": [],
    }


@router.get("/kyc")
async def get_kyc_summary(
    user: dict = Depends(get_current_user),
    service: ComplianceService = Depends(get_compliance_service),
):
    """KYC submission counts for the compliance dashboard."""
    return await _summarise_submissions(service, "kyc")


@router.get("/kyb")
async def get_kyb_summary(
    user: dict = Depends(get_current_user),
    service: ComplianceService = Depends(get_compliance_service),
):
    """KYB submission counts for the compliance dashboard."""
    return await _summarise_submissions(service, "kyb")


# ==================== Reports ====================

@router.post("/reports/generate")
async def generate_monthly_report(
    org_id: UUID, year: int, month: int,
    user: dict = Depends(require_roles("company_admin", "platform_admin", "company_auditor")),
    service: ComplianceService = Depends(get_compliance_service)
):
    """Generate monthly compliance report."""
    report = await service.generate_monthly_report(org_id, year, month, UUID(str(user['id'])))
    return report

@router.get("/reports")
async def get_reports(
    org_id: UUID = Query(None),
    limit: int = Query(50, le=100),
    user: dict = Depends(require_roles("company_admin", "platform_admin", "company_auditor")),
    service: ComplianceService = Depends(get_compliance_service)
):
    """Get compliance reports."""
    reports = await service.get_reports(org_id, limit)
    return reports


# ==================== AML Triage (Wave 21, Story 2.6) ====================
#
# Powers the AML tab on /compliance. Authoring write-side (alerts come
# from the Sumsub webhook handler + transaction rule engine) lives
# elsewhere; these routes are read + state-transition only.
#
# RBAC dependencies are listed explicitly per route so a future reader
# can audit "who can do what" without cross-referencing ROLE_HIERARCHY.

# Roles that may triage AML alerts. company_operator is intentionally
# excluded — separation of duties (the operator initiates transactions,
# AML reviews them).
_AML_TRIAGE_ROLES = ("company_admin", "company_auditor", "platform_admin")


class AmlAlertListItem(BaseModel):
    id: UUID
    organization_id: UUID
    alert_type: str
    severity: str
    status: str
    description: str
    transaction_id: Optional[UUID] = None
    assigned_to: Optional[int] = None
    assigned_to_email: Optional[str] = None
    assigned_to_name: Optional[str] = None
    created_at: datetime


class AmlAlertList(BaseModel):
    items: List[AmlAlertListItem]
    next_cursor: Optional[str] = None


class AmlAlertDetail(AmlAlertListItem):
    details: dict = Field(default_factory=dict)
    investigation_notes: Optional[str] = None
    resolution: Optional[str] = None
    investigated_by: Optional[int] = None
    investigated_by_email: Optional[str] = None
    investigated_by_name: Optional[str] = None
    investigated_at: Optional[datetime] = None
    reported_to_regulator: bool = False
    report_reference: Optional[str] = None
    related_transaction: Optional[dict] = None
    updated_at: Optional[datetime] = None


class AmlResolveRequest(BaseModel):
    decision: Literal["false_positive", "resolved", "reported"]
    resolution: str = Field(..., min_length=1, max_length=2000)
    report_reference: Optional[str] = Field(default=None, max_length=100)


class AmlNoteRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=4000)


class AmlAlertStats(BaseModel):
    open: int
    investigating: int
    resolved_30d: int
    by_severity: dict


def _conflict_response(exc: AmlConflictError) -> HTTPException:
    """Translate AmlConflictError into a 409 with a helpful body."""
    payload: dict = {"detail": exc.reason}
    if exc.current is not None:
        # Pydantic-friendly serialisation of the current row (UUID/datetime become strings).
        payload["current"] = {
            k: (str(v) if isinstance(v, (UUID, datetime)) else v)
            for k, v in exc.current.items()
        }
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=payload)


@router.get("/aml/alerts", response_model=AmlAlertList)
async def list_aml_alerts(
    status_filter: Optional[str] = Query(None, alias="status",
        pattern="^(open|investigating|resolved|false_positive|reported)$"),
    severity: Optional[str] = Query(None, pattern="^(low|medium|high|critical)$"),
    alert_type: Optional[str] = Query(None, max_length=50),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    cursor: Optional[str] = Query(None, max_length=512),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(require_roles(*_AML_TRIAGE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    """List AML alerts with filters + keyset pagination.

    `cursor` is opaque base64; passing the value of `next_cursor` from a
    previous response continues that pagination. RBAC scope is reapplied
    on every call — a leaked cursor cannot widen visibility.
    """
    decoded_cursor = None
    if cursor:
        try:
            decoded_cursor = _decode_cursor(cursor)
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed cursor")

    items, next_cursor_tuple = await service.list_aml_alerts(
        org_ids=org_ids,
        status=status_filter,
        severity=severity,
        alert_type=alert_type,
        date_from=date_from,
        date_to=date_to,
        cursor=decoded_cursor,
        limit=limit,
    )
    next_cursor = (
        _encode_cursor(*next_cursor_tuple) if next_cursor_tuple else None
    )
    return AmlAlertList(items=items, next_cursor=next_cursor)


@router.get("/aml/alerts/stats", response_model=AmlAlertStats)
async def aml_alert_stats(
    user: dict = Depends(require_roles(*_AML_TRIAGE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    """KPI counts for the /compliance AML tab top cards."""
    return await service.aml_alert_stats(org_ids=org_ids)


@router.get("/aml/alerts/{alert_id}", response_model=AmlAlertDetail)
async def get_aml_alert(
    alert_id: UUID,
    user: dict = Depends(require_roles(*_AML_TRIAGE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    """Single-alert drill-down. Includes related transaction (if any).

    Returns 404 both when the alert doesn't exist AND when it's outside
    the caller's RBAC scope, so we don't leak existence to non-members.
    """
    row = await service.get_aml_alert(alert_id, org_ids=org_ids)
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AmlAlertDetail(**row)


@router.post("/aml/alerts/{alert_id}/claim", response_model=AmlAlertDetail)
async def claim_aml_alert(
    alert_id: UUID,
    user: dict = Depends(require_roles(*_AML_TRIAGE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    """Assign the alert to the calling user and move it to `investigating`.

    Returns 409 with `{detail, current}` body if the alert is already
    claimed by someone else or in a terminal state. Idempotent for
    re-claims by the same user.
    """
    try:
        row = await service.claim_aml_alert(
            alert_id=alert_id,
            user_id=int(user["id"]),
            org_ids=org_ids,
        )
    except AmlConflictError as exc:
        if exc.reason == "not_found":
            raise HTTPException(status_code=404, detail="Alert not found")
        raise _conflict_response(exc)
    # Refetch via get_aml_alert to populate denormalised JOIN fields.
    full = await service.get_aml_alert(alert_id, org_ids=org_ids)
    return AmlAlertDetail(**(full or row))


@router.post("/aml/alerts/{alert_id}/resolve", response_model=AmlAlertDetail)
async def resolve_aml_alert(
    alert_id: UUID,
    body: AmlResolveRequest,
    user: dict = Depends(require_roles(*_AML_TRIAGE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    """Terminal-state transition. `reported` requires `report_reference`
    so SAR submissions stay regulator-traceable."""
    if body.decision == "reported" and not body.report_reference:
        raise HTTPException(
            status_code=422,
            detail="report_reference is required for 'reported' decision",
        )
    try:
        row = await service.resolve_aml_alert(
            alert_id=alert_id,
            user_id=int(user["id"]),
            decision=body.decision,
            resolution=body.resolution,
            report_reference=body.report_reference,
            org_ids=org_ids,
        )
    except AmlConflictError as exc:
        if exc.reason == "not_found":
            raise HTTPException(status_code=404, detail="Alert not found")
        raise _conflict_response(exc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    full = await service.get_aml_alert(alert_id, org_ids=org_ids)
    return AmlAlertDetail(**(full or row))


@router.post("/aml/alerts/{alert_id}/notes", response_model=AmlAlertDetail)
async def append_aml_note(
    alert_id: UUID,
    body: AmlNoteRequest,
    user: dict = Depends(require_roles(*_AML_TRIAGE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    """Append an investigation note. Reported alerts are immutable."""
    try:
        row = await service.append_aml_note(
            alert_id=alert_id,
            user_id=int(user["id"]),
            note=body.note,
            org_ids=org_ids,
        )
    except AmlConflictError as exc:
        if exc.reason == "not_found":
            raise HTTPException(status_code=404, detail="Alert not found")
        raise _conflict_response(exc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    full = await service.get_aml_alert(alert_id, org_ids=org_ids)
    return AmlAlertDetail(**(full or row))


# ==================== Release-from-hold (Wave 26, Story 2.11) ====================


class AmlReleaseHoldRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


class AmlReleaseHoldResponse(BaseModel):
    alert_id: UUID
    tx_id: UUID
    tx_unid: Optional[str] = None
    tx_status: str


@router.post(
    "/aml/alerts/{alert_id}/release-hold",
    response_model=AmlReleaseHoldResponse,
)
async def release_held_transaction(
    alert_id: UUID,
    body: AmlReleaseHoldRequest,
    user: dict = Depends(require_roles(*_AML_TRIAGE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    """Lift `transactions.status = on_hold` for the alert's linked tx.

    Body must include `reason` so the audit-log captures the operator's
    justification. Returns 409 with a `current` payload when the tx is
    already in another state (released earlier, signed, etc.) — the UI
    re-fetches in that branch.
    """
    try:
        return await service.release_held_transaction(
            alert_id=alert_id,
            user_id=int(user["id"]),
            reason=body.reason,
            org_ids=org_ids,
        )
    except AmlConflictError as exc:
        if exc.reason == "not_found":
            raise HTTPException(status_code=404, detail="Alert not found")
        if exc.reason == "no_transaction":
            raise HTTPException(
                status_code=422,
                detail="Alert has no linked transaction",
            )
        raise _conflict_response(exc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ==================== SAR submissions (Wave 24, Story 2.9) ====================
#
# Three endpoints under /aml/alerts/{id}/sar:
#   - POST  → generate + persist + (optionally) deliver. Idempotent.
#   - GET (.json) → return the persisted JSON payload as a downloadable file.
#   - GET (.md)   → return the rendered Markdown as a downloadable file.
#
# All three reuse the same RBAC scope as the AML triage endpoints — only
# triage-eligible roles can read or generate SAR.


from fastapi.responses import PlainTextResponse, Response  # noqa: E402


class SarSubmitRequest(BaseModel):
    backend: Optional[str] = Field(
        default=None,
        max_length=50,
        description="One of manual_export | email | api_v1 | dryrun. "
                    "Defaults to FINSUPERVISORY_SAR_BACKEND env (or manual_export).",
    )
    officer_phone: Optional[str] = Field(default=None, max_length=64)


class SarSubmissionResponse(BaseModel):
    id: UUID
    alert_id: UUID
    submission_backend: str
    status: str
    external_reference: Optional[str] = None
    response_body: Optional[str] = None
    payload_json: dict
    rendered_markdown: str
    submitted_at: datetime
    acknowledged_at: Optional[datetime] = None


@router.post(
    "/aml/alerts/{alert_id}/sar",
    response_model=SarSubmissionResponse,
    status_code=201,
)
async def submit_sar(
    alert_id: UUID,
    body: SarSubmitRequest,
    user: dict = Depends(require_roles(*_AML_TRIAGE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    """Generate + persist (and optionally deliver) a SAR for one alert.

    Idempotent — re-POSTing returns 200 with the existing row.
    `backend` selects the submission channel; absent → env default.
    """
    officer = {
        "id": int(user["id"]),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "phone": body.officer_phone,
    }
    try:
        row = await service.submit_sar(
            alert_id=alert_id,
            officer=officer,
            backend_name=body.backend,
            org_ids=org_ids,
        )
    except ValueError as exc:
        # "alert not found" → 404; everything else (unknown backend,
        # NotImplementedError) → 422 with the reason verbatim.
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=422, detail=msg)
    return _serialize_sar_row(row)


@router.get(
    "/aml/alerts/{alert_id}/sar",
    response_model=SarSubmissionResponse,
)
async def get_sar(
    alert_id: UUID,
    user: dict = Depends(require_roles(*_AML_TRIAGE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    """Read the SAR submission for this alert (RBAC-scoped)."""
    row = await service.get_sar_submission(alert_id, org_ids=org_ids)
    if row is None:
        raise HTTPException(status_code=404, detail="SAR not found for this alert")
    return _serialize_sar_row(row)


@router.get("/aml/alerts/{alert_id}/sar.json")
async def get_sar_json(
    alert_id: UUID,
    user: dict = Depends(require_roles(*_AML_TRIAGE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    """Download the SAR payload as JSON. Browser-friendly Content-Disposition."""
    row = await service.get_sar_submission(alert_id, org_ids=org_ids)
    if row is None:
        raise HTTPException(status_code=404, detail="SAR not found for this alert")
    payload = row.get("payload_json")
    if isinstance(payload, str):
        # asyncpg sometimes returns jsonb as str depending on type-codec setup.
        import json as _json
        payload = _json.loads(payload)
    import json as _json
    body = _json.dumps(payload, indent=2, default=str)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="sar-{alert_id}.json"'},
    )


@router.get("/aml/alerts/{alert_id}/sar.md")
async def get_sar_markdown(
    alert_id: UUID,
    user: dict = Depends(require_roles(*_AML_TRIAGE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    """Download the SAR payload as Markdown."""
    row = await service.get_sar_submission(alert_id, org_ids=org_ids)
    if row is None:
        raise HTTPException(status_code=404, detail="SAR not found for this alert")
    return PlainTextResponse(
        content=row.get("rendered_markdown") or "",
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="sar-{alert_id}.md"'},
    )


# ==================== Monitoring rules CRUD (Wave 25, Story 2.10) ====================
#
# CRUD over `transaction_monitoring_rules`. Validation of the
# `rule_config` shape is done here per `rule_type` so the service
# layer treats it as opaque jsonb.
#
# RBAC:
#   - read: any triage-eligible role (auditors need to see what fired)
#   - write: super_admin / company_admin / platform_admin only
#   - global rules (organization_id IS NULL) — only super_admin/platform_admin
#     can create/edit/delete; everyone else sees them read-only.

_RULE_READ_ROLES = ("company_admin", "company_auditor", "platform_admin")
_RULE_WRITE_ROLES = ("company_admin", "platform_admin")  # super_admin always allowed by RBAC

_SUPPORTED_RULE_TYPES = ("threshold", "velocity", "blacklist_address")
_SUPPORTED_ACTIONS = ("alert", "hold", "block")
_SUPPORTED_SEVERITIES = ("low", "medium", "high", "critical")


def _validate_rule_config(rule_type: str, config: dict) -> None:
    """Per-type schema check. Raise HTTPException(422) on mismatch."""
    if rule_type == "threshold":
        if "threshold_usd" not in config and "threshold" not in config:
            raise HTTPException(
                status_code=422,
                detail="threshold rules require rule_config.threshold_usd",
            )
        try:
            float(str(config.get("threshold_usd", config.get("threshold"))))
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=422,
                detail="threshold_usd must be a number",
            )
    elif rule_type == "velocity":
        for k in ("count", "window_hours"):
            if k not in config:
                raise HTTPException(
                    status_code=422,
                    detail=f"velocity rules require rule_config.{k}",
                )
            if not isinstance(config[k], int) or config[k] <= 0:
                raise HTTPException(
                    status_code=422,
                    detail=f"velocity rule_config.{k} must be a positive integer",
                )
    elif rule_type == "blacklist_address":
        addrs = config.get("addresses")
        if not isinstance(addrs, list) or not addrs:
            raise HTTPException(
                status_code=422,
                detail="blacklist_address rules require non-empty rule_config.addresses[]",
            )
        for a in addrs:
            if not isinstance(a, str):
                raise HTTPException(
                    status_code=422,
                    detail="blacklist_address rule_config.addresses must contain strings",
                )


class MonitoringRule(BaseModel):
    id: UUID
    organization_id: Optional[UUID] = None
    rule_name: str
    rule_type: str
    description: Optional[str] = None
    rule_config: dict
    action: str
    severity: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None


class MonitoringRuleCreate(BaseModel):
    organization_id: Optional[UUID] = Field(
        default=None,
        description="Org owning the rule. Null = global (super_admin only).",
    )
    rule_name: str = Field(..., min_length=1, max_length=255)
    rule_type: Literal["threshold", "velocity", "blacklist_address"]
    description: Optional[str] = Field(default=None, max_length=2000)
    rule_config: dict
    action: Literal["alert", "hold", "block"] = "alert"
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    is_active: bool = True


class MonitoringRuleUpdate(BaseModel):
    rule_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    rule_type: Optional[Literal["threshold", "velocity", "blacklist_address"]] = None
    description: Optional[str] = Field(default=None, max_length=2000)
    rule_config: Optional[dict] = None
    action: Optional[Literal["alert", "hold", "block"]] = None
    severity: Optional[Literal["low", "medium", "high", "critical"]] = None
    is_active: Optional[bool] = None


def _can_manage_global_rules(user: dict) -> bool:
    role = (user.get("role") or "").lower()
    return role in ("super_admin", "platform_admin", "admin")


@router.get("/rules", response_model=List[MonitoringRule])
async def list_monitoring_rules(
    user: dict = Depends(require_roles(*_RULE_READ_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    """List monitoring rules visible to the caller (own-org + global)."""
    rows = await service.list_monitoring_rules(org_ids=org_ids)
    return [MonitoringRule(**r) for r in rows]


@router.get("/rules/{rule_id}", response_model=MonitoringRule)
async def get_monitoring_rule(
    rule_id: UUID,
    user: dict = Depends(require_roles(*_RULE_READ_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    row = await service.get_monitoring_rule(rule_id, org_ids=org_ids)
    if row is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return MonitoringRule(**row)


@router.post("/rules", response_model=MonitoringRule, status_code=201)
async def create_monitoring_rule(
    body: MonitoringRuleCreate,
    user: dict = Depends(require_roles(*_RULE_WRITE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    _validate_rule_config(body.rule_type, body.rule_config)

    target_org = body.organization_id
    # Non-super_admin trying to make a global rule → 403.
    if target_org is None and not _can_manage_global_rules(user):
        raise HTTPException(
            status_code=403,
            detail="Only super_admin can create global rules",
        )
    # Non-super_admin trying to write outside their orgs → 403.
    if (
        target_org is not None
        and org_ids is not None
        and target_org not in org_ids
    ):
        raise HTTPException(
            status_code=403,
            detail="Cannot create rule for another organization",
        )

    row = await service.create_monitoring_rule(
        organization_id=target_org,
        rule_name=body.rule_name,
        rule_type=body.rule_type,
        description=body.description,
        rule_config=body.rule_config,
        action=body.action,
        severity=body.severity,
        is_active=body.is_active,
        actor_user_id=int(user["id"]),
    )
    return MonitoringRule(**row)


@router.patch("/rules/{rule_id}", response_model=MonitoringRule)
async def update_monitoring_rule(
    rule_id: UUID,
    body: MonitoringRuleUpdate,
    user: dict = Depends(require_roles(*_RULE_WRITE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    # Refuse global-rule edits from non-super_admin upfront — even if
    # the row's RBAC scope let them GET it.
    existing = await service.get_monitoring_rule(rule_id, org_ids=org_ids)
    if existing is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    if existing.get("organization_id") is None and not _can_manage_global_rules(user):
        raise HTTPException(
            status_code=403,
            detail="Only super_admin can edit global rules",
        )

    if body.rule_type is not None and body.rule_config is not None:
        _validate_rule_config(body.rule_type, body.rule_config)
    elif body.rule_config is not None:
        _validate_rule_config(existing["rule_type"], body.rule_config)

    row = await service.update_monitoring_rule(
        rule_id,
        org_ids=org_ids,
        actor_user_id=int(user["id"]),
        rule_name=body.rule_name,
        rule_type=body.rule_type,
        description=body.description,
        rule_config=body.rule_config,
        action=body.action,
        severity=body.severity,
        is_active=body.is_active,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return MonitoringRule(**row)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_monitoring_rule(
    rule_id: UUID,
    user: dict = Depends(require_roles(*_RULE_WRITE_ROLES)),
    org_ids: Optional[List[UUID]] = Depends(get_user_org_ids),
    service: ComplianceService = Depends(get_compliance_service),
):
    existing = await service.get_monitoring_rule(rule_id, org_ids=org_ids)
    if existing is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    if existing.get("organization_id") is None and not _can_manage_global_rules(user):
        raise HTTPException(
            status_code=403,
            detail="Only super_admin can delete global rules",
        )
    deleted = await service.delete_monitoring_rule(
        rule_id, org_ids=org_ids, actor_user_id=int(user["id"]),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return Response(status_code=204)


def _serialize_sar_row(row: dict) -> SarSubmissionResponse:
    """Coerce a raw asyncpg row dict into the API response shape."""
    payload = row.get("payload_json")
    if isinstance(payload, str):
        import json as _json
        payload = _json.loads(payload)
    return SarSubmissionResponse(
        id=row["id"],
        alert_id=row["alert_id"],
        submission_backend=row["submission_backend"],
        status=row["status"],
        external_reference=row.get("external_reference"),
        response_body=row.get("response_body"),
        payload_json=payload or {},
        rendered_markdown=row.get("rendered_markdown") or "",
        submitted_at=row["submitted_at"],
        acknowledged_at=row.get("acknowledged_at"),
    )
