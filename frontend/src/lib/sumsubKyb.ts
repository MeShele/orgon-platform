// KYB (business onboarding) Sumsub helpers — sibling of sumsubKyc.ts.
//
// Backend endpoints (Wave 20, story 2.5):
//   POST /api/v1/kyc-kyb/sumsub/kyb/access-token?organization_id=<uuid>
//   GET  /api/v1/kyc-kyb/sumsub/kyb/applicant-status?organization_id=<uuid>
//
// Disabled-mode contract: backend returns 503 if any of SUMSUB_* env
// vars is unset. We surface that via SumsubNotConfiguredError so the
// page can show its pre-launch banner instead of the iframe.

import { SumsubNotConfiguredError } from "@/lib/sumsubKyc";

export interface SumsubKybAccessTokenResponse {
  access_token: string;
  expires_in: number;
  applicant_id: string;
  organization_id: string;
  external_user_id: string;
  level_name: string;
}

export interface SumsubKybApplicantStatusResponse {
  applicant_id: string;
  organization_id: string;
  review_status: string;
  review_result: Record<string, unknown> | null;
  level_name: string;
  mapped_status: string;
}

export async function fetchSumsubKybStatus(
  organizationId: string,
): Promise<SumsubKybApplicantStatusResponse | null> {
  const token = typeof window !== "undefined" ? localStorage.getItem("orgon_access_token") : "";
  const res = await fetch(
    `/api/v1/kyc-kyb/sumsub/kyb/applicant-status?organization_id=${encodeURIComponent(organizationId)}`,
    { headers: { Authorization: `Bearer ${token ?? ""}` } },
  );
  if (res.status === 404) return null;
  if (res.status === 503) throw new SumsubNotConfiguredError();
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Sumsub KYB status fetch failed: ${res.status} ${body}`);
  }
  return res.json();
}

export async function fetchSumsubKybAccessToken(
  organizationId: string,
): Promise<SumsubKybAccessTokenResponse> {
  const token = typeof window !== "undefined" ? localStorage.getItem("orgon_access_token") : "";
  const res = await fetch(
    `/api/v1/kyc-kyb/sumsub/kyb/access-token?organization_id=${encodeURIComponent(organizationId)}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token ?? ""}`,
      },
    },
  );
  if (res.status === 503) throw new SumsubNotConfiguredError();
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Sumsub KYB access-token failed: ${res.status} ${body}`);
  }
  return res.json();
}
