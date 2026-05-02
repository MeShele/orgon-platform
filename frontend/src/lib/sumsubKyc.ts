// Type declarations for the Sumsub WebSDK loaded via <script> tag.
// We don't depend on @sumsub/websdk-react — Sumsub publishes their
// builder at static.sumsub.com which auto-updates with security
// patches. See ADR-8 in docs/stories/2-4-sumsub-kyc-architecture.md.

export interface SumsubAccessTokenResponse {
  access_token: string;
  expires_in: number;
  applicant_id: string;
  external_user_id: string;
  level_name: string;
}

export interface SumsubApplicantStatusResponse {
  applicant_id: string;
  review_status: string;
  review_result: Record<string, unknown> | null;
  level_name: string;
  // ORGON-mapped status (matches kyc_submissions.status enum):
  // 'not_started' | 'pending' | 'manual_review' | 'approved' | 'rejected' | 'needs_resubmit'
  mapped_status: string;
}

export type SumsubMappedStatus =
  | "not_started"
  | "pending"
  | "manual_review"
  | "approved"
  | "rejected"
  | "needs_resubmit";

/**
 * Fetch the current user's Sumsub status from our backend.
 * Returns null when the user hasn't started verification yet (404).
 * Throws on 503 (Sumsub not configured) so the caller can show
 * a "platform pre-launch" banner instead of the iframe.
 */
export async function fetchSumsubStatus(): Promise<SumsubApplicantStatusResponse | null> {
  const token = typeof window !== "undefined" ? localStorage.getItem("orgon_access_token") : "";
  const res = await fetch("/api/v1/kyc-kyb/sumsub/applicant-status", {
    headers: { Authorization: `Bearer ${token ?? ""}` },
  });
  if (res.status === 404) return null;
  if (res.status === 503) throw new SumsubNotConfiguredError();
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Sumsub status fetch failed: ${res.status} ${body}`);
  }
  return res.json();
}

/**
 * Mint a fresh WebSDK access token (creates Sumsub applicant on
 * first call, idempotent on subsequent calls).
 */
export async function fetchSumsubAccessToken(): Promise<SumsubAccessTokenResponse> {
  const token = typeof window !== "undefined" ? localStorage.getItem("orgon_access_token") : "";
  const res = await fetch("/api/v1/kyc-kyb/sumsub/access-token", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token ?? ""}`,
    },
  });
  if (res.status === 503) throw new SumsubNotConfiguredError();
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Sumsub access-token failed: ${res.status} ${body}`);
  }
  return res.json();
}

export class SumsubNotConfiguredError extends Error {
  constructor() {
    super("Sumsub is not configured on this environment");
    this.name = "SumsubNotConfiguredError";
  }
}

// ────────────────────────────────────────────────────────────────────
// Sumsub WebSDK global declarations
// ────────────────────────────────────────────────────────────────────

interface SumsubBuilder {
  withConf(conf: { lang?: string; email?: string; phone?: string; theme?: "light" | "dark" }): SumsubBuilder;
  withOptions(opts: { addViewportTag?: boolean; adaptIframeHeight?: boolean }): SumsubBuilder;
  on(event: string, handler: (...args: unknown[]) => void): SumsubBuilder;
  onMessage(handler: (type: string, payload: unknown) => void): SumsubBuilder;
  build(): { launch: (selector: string) => void };
}

interface SumsubWebSdk {
  init(
    accessToken: string,
    refreshTokenFn: () => Promise<string>,
  ): SumsubBuilder;
}

declare global {
  interface Window {
    snsWebSdk?: SumsubWebSdk;
  }
}
