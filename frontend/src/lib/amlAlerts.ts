// AML triage fetchers — Wave 21, Story 2.6.
//
// Endpoints (mounted on `/api/v1/compliance/aml/*`):
//   GET    /aml/alerts                 → list with filters + cursor
//   GET    /aml/alerts/stats           → KPI counts
//   GET    /aml/alerts/{id}            → single alert + related transaction
//   POST   /aml/alerts/{id}/claim      → claim (409 on race)
//   POST   /aml/alerts/{id}/resolve    → terminal transition
//   POST   /aml/alerts/{id}/notes      → append investigation note

export type AmlSeverity = "low" | "medium" | "high" | "critical";
export type AmlStatus =
  | "open"
  | "investigating"
  | "resolved"
  | "false_positive"
  | "reported";
export type AmlDecision = "false_positive" | "resolved" | "reported";

export interface AmlAlertListItem {
  id: string;
  organization_id: string;
  alert_type: string;
  severity: AmlSeverity;
  status: AmlStatus;
  description: string;
  transaction_id: string | null;
  assigned_to: number | null;
  assigned_to_email: string | null;
  assigned_to_name: string | null;
  created_at: string;
}

export interface AmlAlertList {
  items: AmlAlertListItem[];
  next_cursor: string | null;
}

export interface AmlAlertDetail extends AmlAlertListItem {
  details: Record<string, unknown>;
  investigation_notes: string | null;
  resolution: string | null;
  investigated_by: number | null;
  investigated_by_email: string | null;
  investigated_by_name: string | null;
  investigated_at: string | null;
  reported_to_regulator: boolean;
  report_reference: string | null;
  related_transaction: Record<string, unknown> | null;
  updated_at: string | null;
}

export interface AmlStats {
  open: number;
  investigating: number;
  resolved_30d: number;
  by_severity: Record<AmlSeverity, number>;
}

export interface AmlConflict {
  detail: string;                            // already_claimed | terminal_status | not_claimed
  current?: Record<string, unknown>;
}

// Sensitive identity fields scrubbed from the `details` blob before
// rendering. Document IDs are not needed for an officer's decision —
// the applicant's name/email are. Sumsub already store the originals.
export const PII_SCRUB_KEYS = new Set([
  "passport_number",
  "national_id",
  "inn",
  "dob",
  "taxId",
  "tax_id",
]);

function authHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("orgon_access_token") : "";
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (res.status === 409) {
    const body = (await res.json()) as { detail: AmlConflict };
    const conflict = body.detail ?? { detail: "conflict" };
    const err = new AmlConflictError(conflict.detail, conflict.current);
    throw err;
  }
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`AML request failed: ${res.status} ${body}`);
  }
  return (await res.json()) as T;
}

export class AmlConflictError extends Error {
  constructor(
    public readonly reason: string,
    public readonly current?: Record<string, unknown>,
  ) {
    super(`AML conflict: ${reason}`);
    this.name = "AmlConflictError";
  }
}

export async function fetchAmlStats(): Promise<AmlStats> {
  const res = await fetch("/api/v1/compliance/aml/alerts/stats", {
    headers: authHeaders(),
  });
  return jsonOrThrow<AmlStats>(res);
}

export interface AmlListFilters {
  status?: AmlStatus;
  severity?: AmlSeverity;
  alert_type?: string;
  cursor?: string;
  limit?: number;
}

export async function fetchAmlAlerts(filters: AmlListFilters = {}): Promise<AmlAlertList> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  const url = `/api/v1/compliance/aml/alerts${qs.toString() ? `?${qs}` : ""}`;
  const res = await fetch(url, { headers: authHeaders() });
  return jsonOrThrow<AmlAlertList>(res);
}

export async function fetchAmlAlert(id: string): Promise<AmlAlertDetail> {
  const res = await fetch(`/api/v1/compliance/aml/alerts/${id}`, {
    headers: authHeaders(),
  });
  return jsonOrThrow<AmlAlertDetail>(res);
}

export async function claimAmlAlert(id: string): Promise<AmlAlertDetail> {
  const res = await fetch(`/api/v1/compliance/aml/alerts/${id}/claim`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
  });
  return jsonOrThrow<AmlAlertDetail>(res);
}

export interface ResolveBody {
  decision: AmlDecision;
  resolution: string;
  report_reference?: string;
}

export async function resolveAmlAlert(
  id: string,
  body: ResolveBody,
): Promise<AmlAlertDetail> {
  const res = await fetch(`/api/v1/compliance/aml/alerts/${id}/resolve`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return jsonOrThrow<AmlAlertDetail>(res);
}

export async function appendAmlNote(id: string, note: string): Promise<AmlAlertDetail> {
  const res = await fetch(`/api/v1/compliance/aml/alerts/${id}/notes`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ note }),
  });
  return jsonOrThrow<AmlAlertDetail>(res);
}


// ────────────────────────────────────────────────────────────────────
// Release-from-hold (Wave 26, Story 2.11)
// ────────────────────────────────────────────────────────────────────

export interface AmlReleaseHoldResponse {
  alert_id: string;
  tx_id: string;
  tx_unid: string | null;
  tx_status: string;
}

export async function releaseHeldTransaction(
  alertId: string,
  reason: string,
): Promise<AmlReleaseHoldResponse> {
  const res = await fetch(
    `/api/v1/compliance/aml/alerts/${alertId}/release-hold`,
    {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    },
  );
  return jsonOrThrow<AmlReleaseHoldResponse>(res);
}


// ────────────────────────────────────────────────────────────────────
// SAR submissions (Wave 24, Story 2.9)
// ────────────────────────────────────────────────────────────────────

export type SarBackend = "manual_export" | "email" | "api_v1" | "dryrun";
export type SarStatus = "prepared" | "sent" | "acknowledged" | "failed";

export interface SarSubmission {
  id: string;
  alert_id: string;
  submission_backend: SarBackend;
  status: SarStatus;
  external_reference: string | null;
  response_body: string | null;
  payload_json: Record<string, unknown>;
  rendered_markdown: string;
  submitted_at: string;
  acknowledged_at: string | null;
}

export async function submitSar(
  alertId: string,
  body: { backend?: SarBackend; officer_phone?: string } = {},
): Promise<SarSubmission> {
  const res = await fetch(`/api/v1/compliance/aml/alerts/${alertId}/sar`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return jsonOrThrow<SarSubmission>(res);
}

export async function fetchSar(alertId: string): Promise<SarSubmission | null> {
  const res = await fetch(`/api/v1/compliance/aml/alerts/${alertId}/sar`, {
    headers: authHeaders(),
  });
  if (res.status === 404) return null;
  return jsonOrThrow<SarSubmission>(res);
}

/** Returns a download URL for the JSON payload. Frontend uses the
 * raw URL with a temporary anchor — token goes through fetch. */
export async function downloadSarFile(
  alertId: string,
  format: "json" | "md",
): Promise<Blob> {
  const res = await fetch(
    `/api/v1/compliance/aml/alerts/${alertId}/sar.${format}`,
    { headers: authHeaders() },
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`SAR download failed: ${res.status} ${body}`);
  }
  return res.blob();
}

/** Strip PII from a `details` blob before showing it in the drawer. */
export function scrubPii(details: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(details)) {
    if (PII_SCRUB_KEYS.has(k)) {
      out[k] = "••• hidden •••";
    } else if (v && typeof v === "object" && !Array.isArray(v)) {
      out[k] = scrubPii(v as Record<string, unknown>);
    } else {
      out[k] = v;
    }
  }
  return out;
}
