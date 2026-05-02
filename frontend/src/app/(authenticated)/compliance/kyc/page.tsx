"use client";

// KYC verification page (Wave 19, story 2.4).
//
// Behaviour by user state + backend config:
//
// 1. Sumsub configured (SUMSUB_* env vars present in Coolify):
//    - User without applicant → "Start verification" CTA → mint
//      access-token → embed iframe.
//    - User with pending/manual_review status → status panel + iframe
//      (Sumsub iframe handles re-entry to upload more docs if needed).
//    - User approved → green "verified" panel, no iframe.
//    - User rejected/needs_resubmit → red banner with reason +
//      "Try again" → re-mint token → iframe.
//
// 2. Sumsub NOT configured (env vars unset, e.g. shared-test orgon.asystem.ai):
//    - Backend returns 503 from both endpoints.
//    - We show a polished "platform pre-launch" banner explaining
//      that KYC will be enabled once admin pastes the credentials.
//    - No iframe is loaded.
//
// This is exactly the deployment story the user asked for: paste env
// vars in Coolify → redeploy backend → KYC works on the same code,
// no rewires needed.

import { useEffect, useState, useCallback } from "react";
import { Icon } from "@/lib/icons";
import { SumsubWebSdkContainer } from "@/components/compliance/SumsubWebSdkContainer";
import {
  fetchSumsubStatus,
  SumsubNotConfiguredError,
  type SumsubApplicantStatusResponse,
  type SumsubMappedStatus,
} from "@/lib/sumsubKyc";

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

export default function KycPage() {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<SumsubApplicantStatusResponse | null>(null);
  const [notConfigured, setNotConfigured] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [iframeOpen, setIframeOpen] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchSumsubStatus();
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
    refresh();
  }, [refresh]);

  const handleSdkComplete = useCallback(() => {
    setIframeOpen(false);
    // Status will arrive via webhook; refresh in 2s gives backend time
    // to receive the webhook + update DB. Frontend then sees fresh state.
    setTimeout(refresh, 2000);
  }, [refresh]);

  const mappedStatus = (status?.mapped_status ?? "not_started") as SumsubMappedStatus;
  const canStart =
    !iframeOpen && (mappedStatus === "not_started" || mappedStatus === "needs_resubmit" || mappedStatus === "rejected");

  return (
    <div className="space-y-6 p-2 sm:p-4 md:p-6 lg:p-8 max-w-3xl mx-auto">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <Icon icon="solar:user-check-bold" className="text-2xl text-primary" />
        <div>
          <h1 className="text-2xl font-bold text-foreground">KYC верификация</h1>
          <p className="text-sm text-muted-foreground">
            Подтверждение личности через Sumsub. Документы загружаются напрямую в их защищённый сервис.
          </p>
        </div>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <Icon icon="svg-spinners:ring-resize" className="text-3xl text-primary" />
        </div>
      )}

      {/* Sumsub-not-configured banner */}
      {!loading && notConfigured && (
        <div className="rounded-xl border border-warning/40 bg-warning/5 p-6">
          <div className="flex items-start gap-3">
            <Icon icon="solar:settings-bold" className="text-warning text-2xl shrink-0 mt-0.5" />
            <div className="space-y-2">
              <p className="text-base font-medium text-foreground">
                Платформа в режиме pre-launch
              </p>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Sumsub-интеграция готова к работе, но конкретно на этом окружении
                ещё не выставлены креды. Свяжитесь с поддержкой
                <a
                  className="text-primary underline-offset-4 hover:underline mx-1"
                  href="mailto:support@orgon.asystem.kg"
                >
                  support@orgon.asystem.kg
                </a>
                — мы подключим вас к pilot-окружению с активным KYC.
              </p>
              <p className="text-xs text-muted-foreground">
                Под капотом всё подключено: Sumsub WebSDK, webhook receiver, AML-handler.
                Чтобы включить — в Coolify нужно выставить{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-[11px]">SUMSUB_APP_TOKEN</code>,{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-[11px]">SUMSUB_SECRET_KEY</code>,{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-[11px]">SUMSUB_WEBHOOK_SECRET</code>.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Generic error state */}
      {!loading && !notConfigured && error && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-6">
          <div className="flex items-start gap-3">
            <Icon icon="solar:danger-circle-bold" className="text-destructive text-xl shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-foreground">Не удалось загрузить статус</p>
              <p className="text-xs text-muted-foreground mt-1">{error}</p>
              <button
                onClick={refresh}
                className="mt-3 text-xs text-primary hover:underline"
              >
                Попробовать ещё раз
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Status panel */}
      {!loading && !notConfigured && !error && (
        <>
          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Текущий статус</h3>
            <span
              className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[mappedStatus]}`}
            >
              {STATUS_LABELS[mappedStatus]}
            </span>
            {status?.review_result && typeof status.review_result === "object" && (
              <div className="mt-3 text-xs text-muted-foreground space-y-1">
                {/* Show comment-if-any from Sumsub */}
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

          {/* Approved — terminal happy state, no iframe */}
          {mappedStatus === "approved" && (
            <div className="rounded-xl border border-success/40 bg-success/5 p-6 text-center">
              <Icon icon="solar:verified-check-bold" className="text-4xl text-success mx-auto mb-2" />
              <p className="text-success font-medium">Личность подтверждена</p>
              <p className="text-xs text-muted-foreground mt-1">
                Вы можете создавать кошельки и проводить транзакции.
              </p>
            </div>
          )}

          {/* Pending / manual review — iframe stays available so user can re-upload if Sumsub asks for more docs */}
          {(mappedStatus === "pending" || mappedStatus === "manual_review") && !iframeOpen && (
            <div className="rounded-xl border border-border bg-card p-5">
              <p className="text-sm text-muted-foreground">
                Документы получены и в очереди на проверку. Если Sumsub запросит дополнительные данные,
                откройте окно верификации ещё раз.
              </p>
              <button
                onClick={() => setIframeOpen(true)}
                className="mt-4 px-4 py-2 text-sm bg-secondary text-foreground rounded-lg hover:bg-muted transition-colors border border-border"
              >
                Открыть окно верификации
              </button>
            </div>
          )}

          {/* CTA to start / restart */}
          {canStart && (
            <button
              onClick={() => setIframeOpen(true)}
              className="w-full py-3 bg-primary text-primary-foreground rounded-xl font-medium hover:opacity-90 transition-opacity"
            >
              {mappedStatus === "not_started" ? "Начать верификацию" : "Пройти ещё раз"}
            </button>
          )}

          {/* Iframe */}
          {iframeOpen && (
            <SumsubWebSdkContainer onComplete={handleSdkComplete} lang="ru" />
          )}
        </>
      )}
    </div>
  );
}
