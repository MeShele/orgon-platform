"use client";

// KYB (business onboarding) page — Wave 20, story 2.5.
//
// Mirrors /compliance/kyc but operates on an organization, not a user:
//   - externalUserId schema:  orgon-org-<organization_uuid>
//   - access-token endpoint:  POST /sumsub/kyb/access-token?organization_id=
//   - status endpoint:        GET  /sumsub/kyb/applicant-status?organization_id=
//   - RBAC: only super_admin / company_admin may start the flow
//   - Status: any org member can read state
//
// Org context resolution: the user's primary org_id is fetched via
// `api.getCurrentUser()` (existing helper). MVP behaviour assumes one
// org per user — multi-org tenant switching is already exposed via
// `api.switchOrganization()` elsewhere in the app and remains that
// page's concern, not ours.

import { useEffect, useState, useCallback } from "react";
import { Icon } from "@/lib/icons";
import { SumsubWebSdkContainer } from "@/components/compliance/SumsubWebSdkContainer";
import { SumsubNotConfiguredError, type SumsubMappedStatus } from "@/lib/sumsubKyc";
import {
  fetchSumsubKybStatus,
  fetchSumsubKybAccessToken,
  type SumsubKybApplicantStatusResponse,
} from "@/lib/sumsubKyb";
import { api } from "@/lib/api";

const STATUS_LABELS: Record<SumsubMappedStatus, string> = {
  not_started: "Не начата",
  pending: "На рассмотрении",
  manual_review: "Ручная проверка",
  approved: "Подтверждена",
  rejected: "Отклонена",
  needs_resubmit: "Требуются доп. документы",
};

const STATUS_COLORS: Record<SumsubMappedStatus, string> = {
  not_started: "bg-muted text-muted-foreground",
  pending: "bg-warning/10 text-warning",
  manual_review: "bg-primary/10 text-primary",
  approved: "bg-success/10 text-success",
  rejected: "bg-destructive/10 text-destructive",
  needs_resubmit: "bg-warning/10 text-warning",
};

interface CurrentUser {
  id?: number | string;
  role?: string;
  organization_id?: string | null;
  organization_name?: string | null;
}

export default function KybPage() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [orgName, setOrgName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<SumsubKybApplicantStatusResponse | null>(null);
  const [notConfigured, setNotConfigured] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [iframeOpen, setIframeOpen] = useState(false);

  const refresh = useCallback(async (organizationId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchSumsubKybStatus(organizationId);
      setStatus(res);
      setNotConfigured(false);
    } catch (e) {
      if (e instanceof SumsubNotConfiguredError) {
        setNotConfigured(true);
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const me = (await api.getCurrentUser()) as CurrentUser;
        setUser(me);
        const oid = me.organization_id ?? null;
        setOrgId(oid);
        setOrgName(me.organization_name ?? null);
        if (oid) {
          await refresh(oid);
        } else {
          setLoading(false);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setLoading(false);
      }
    })();
  }, [refresh]);

  const handleSdkComplete = useCallback(() => {
    setIframeOpen(false);
    if (orgId) setTimeout(() => refresh(orgId), 2000);
  }, [orgId, refresh]);

  const role = (user?.role ?? "").toLowerCase();
  const canStartKyb = role === "super_admin" || role === "company_admin";

  const mappedStatus = (status?.mapped_status ?? "not_started") as SumsubMappedStatus;
  const canStart =
    canStartKyb &&
    !iframeOpen &&
    (mappedStatus === "not_started" ||
      mappedStatus === "needs_resubmit" ||
      mappedStatus === "rejected");

  return (
    <div className="space-y-6 p-2 sm:p-4 md:p-6 lg:p-8 max-w-3xl mx-auto">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <Icon icon="solar:buildings-bold" className="text-2xl text-primary" />
        <div>
          <h1 className="text-2xl font-bold text-foreground">KYB верификация</h1>
          <p className="text-sm text-muted-foreground">
            Проверка организации через Sumsub. Учредительные документы загружаются напрямую в их защищённый сервис.
          </p>
        </div>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <Icon icon="svg-spinners:ring-resize" className="text-3xl text-primary" />
        </div>
      )}

      {/* No organization context */}
      {!loading && !orgId && (
        <div className="rounded-xl border border-warning/40 bg-warning/5 p-6">
          <div className="flex items-start gap-3">
            <Icon icon="solar:buildings-bold" className="text-warning text-2xl shrink-0 mt-0.5" />
            <div className="space-y-2">
              <p className="text-base font-medium text-foreground">
                У вашей учётной записи нет организации
              </p>
              <p className="text-sm text-muted-foreground leading-relaxed">
                KYB-верификация запускается на уровне организации. Создайте организацию
                в разделе настроек или попросите администратора добавить вас в существующую.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Sumsub-not-configured banner */}
      {!loading && orgId && notConfigured && (
        <div className="rounded-xl border border-warning/40 bg-warning/5 p-6">
          <div className="flex items-start gap-3">
            <Icon icon="solar:settings-bold" className="text-warning text-2xl shrink-0 mt-0.5" />
            <div className="space-y-2">
              <p className="text-base font-medium text-foreground">
                Платформа в режиме pre-launch
              </p>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Sumsub KYB-интеграция готова к работе, но конкретно на этом окружении
                ещё не выставлены креды. Свяжитесь с поддержкой
                <a
                  className="text-primary underline-offset-4 hover:underline mx-1"
                  href="mailto:support@orgon.asystem.kg"
                >
                  support@orgon.asystem.kg
                </a>
                — мы подключим вас к pilot-окружению с активным KYB.
              </p>
              <p className="text-xs text-muted-foreground">
                Под капотом всё подключено: Sumsub WebSDK, webhook receiver, AML-handler.
                Чтобы включить — в Coolify нужно выставить{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-[11px]">SUMSUB_APP_TOKEN</code>,{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-[11px]">SUMSUB_SECRET_KEY</code>,{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-[11px]">SUMSUB_WEBHOOK_SECRET</code>{" "}
                и при необходимости{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-[11px]">SUMSUB_KYB_LEVEL_NAME</code>.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Generic error */}
      {!loading && orgId && !notConfigured && error && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-6">
          <div className="flex items-start gap-3">
            <Icon icon="solar:danger-circle-bold" className="text-destructive text-xl shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-foreground">Не удалось загрузить статус</p>
              <p className="text-xs text-muted-foreground mt-1">{error}</p>
              <button
                onClick={() => orgId && refresh(orgId)}
                className="mt-3 text-xs text-primary hover:underline"
              >
                Попробовать ещё раз
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Status panel */}
      {!loading && orgId && !notConfigured && !error && (
        <>
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Организация</h3>
                <p className="text-base font-medium text-foreground">
                  {orgName ?? "Без названия"}
                </p>
                <p className="text-[11px] font-mono text-muted-foreground mt-1">{orgId}</p>
              </div>
              <span
                className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[mappedStatus]}`}
              >
                {STATUS_LABELS[mappedStatus]}
              </span>
            </div>
            {status?.review_result && typeof status.review_result === "object" && (
              <div className="mt-3 text-xs text-muted-foreground space-y-1">
                {"clientComment" in status.review_result && (
                  <p>
                    <span className="font-medium">Комментарий:</span>{" "}
                    {String(status.review_result.clientComment)}
                  </p>
                )}
                {"moderationComment" in status.review_result && (
                  <p>
                    <span className="font-medium">Модератор:</span>{" "}
                    {String(status.review_result.moderationComment)}
                  </p>
                )}
              </div>
            )}
            {status?.applicant_id && (
              <p className="mt-3 text-[10px] font-mono text-muted-foreground">
                applicant: {status.applicant_id}
              </p>
            )}
          </div>

          {/* Approved — terminal happy state */}
          {mappedStatus === "approved" && (
            <div className="rounded-xl border border-success/40 bg-success/5 p-6 text-center">
              <Icon icon="solar:verified-check-bold" className="text-4xl text-success mx-auto mb-2" />
              <p className="text-success font-medium">Организация подтверждена</p>
              <p className="text-xs text-muted-foreground mt-1">
                KYB пройден — институциональный пилот доступен.
              </p>
            </div>
          )}

          {/* Pending / manual review */}
          {(mappedStatus === "pending" || mappedStatus === "manual_review") && !iframeOpen && (
            <div className="rounded-xl border border-border bg-card p-5">
              <p className="text-sm text-muted-foreground">
                Документы получены и в очереди на проверку. Если Sumsub запросит дополнительные данные,
                откройте окно верификации ещё раз.
              </p>
              {canStartKyb && (
                <button
                  onClick={() => setIframeOpen(true)}
                  className="mt-4 px-4 py-2 text-sm bg-secondary text-foreground rounded-lg hover:bg-muted transition-colors border border-border"
                >
                  Открыть окно верификации
                </button>
              )}
            </div>
          )}

          {/* Role-gate banner — non-admin viewers see status only */}
          {!canStartKyb && mappedStatus !== "approved" && (
            <div className="rounded-xl border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
              Только администратор организации может запустить или повторить KYB-верификацию.
              Если нужно начать процесс — свяжитесь с {orgName ?? "вашим"} администратором.
            </div>
          )}

          {/* CTA */}
          {canStart && (
            <button
              onClick={() => setIframeOpen(true)}
              className="w-full py-3 bg-primary text-primary-foreground rounded-xl font-medium hover:opacity-90 transition-opacity"
            >
              {mappedStatus === "not_started" ? "Начать верификацию организации" : "Пройти ещё раз"}
            </button>
          )}

          {/* Iframe */}
          {iframeOpen && orgId && (
            <SumsubWebSdkContainer
              onComplete={handleSdkComplete}
              lang="ru"
              tokenFetcher={() => fetchSumsubKybAccessToken(orgId)}
            />
          )}
        </>
      )}
    </div>
  );
}
