"use client";

// AML alert detail drawer — opened from /compliance AML tab when the
// user clicks a row. Slide-from-right (transform-only) per global
// animation rules. URL gains `?alert={id}` for shareable deep-links.

import { useState, useEffect } from "react";
import Link from "next/link";
import { Icon } from "@/lib/icons";
import { Button } from "@/components/ui/Button";
import {
  Drawer, DrawerContent, DrawerHeader, DrawerBody, DrawerFooter, DrawerTitle,
} from "@/components/ui/Drawer";
import {
  Dialog, DialogContent, DialogHeader, DialogFooter, DialogTitle, DialogDescription,
} from "@/components/ui/Dialog";
import { AmlSeverityBadge, AmlStatusBadge } from "./AmlBadges";
import {
  AmlConflictError,
  appendAmlNote,
  claimAmlAlert,
  downloadSarFile,
  fetchAmlAlert,
  fetchSar,
  releaseHeldTransaction,
  resolveAmlAlert,
  scrubPii,
  submitSar,
  type AmlAlertDetail,
  type AmlDecision,
  type SarSubmission,
} from "@/lib/amlAlerts";

interface Props {
  alertId: string | null;
  onClose: () => void;
  onMutated: () => void; // parent revalidates list/stats
}

export function AmlAlertDrawer({ alertId, onClose, onMutated }: Props) {
  const open = alertId !== null;
  const [alert, setAlert] = useState<AmlAlertDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);
  const [note, setNote] = useState("");
  const [decisionDialog, setDecisionDialog] = useState<AmlDecision | null>(null);
  const [resolution, setResolution] = useState("");
  const [reportRef, setReportRef] = useState("");
  const [sar, setSar] = useState<SarSubmission | null>(null);
  const [sarPreviewOpen, setSarPreviewOpen] = useState(false);
  const [releaseHoldOpen, setReleaseHoldOpen] = useState(false);
  const [releaseReason, setReleaseReason] = useState("");

  useEffect(() => {
    if (!alertId) return;
    setLoading(true);
    setError(null);
    setNote("");
    setResolution("");
    setReportRef("");
    setSar(null);
    Promise.all([
      fetchAmlAlert(alertId),
      // SAR may not exist yet — fetchSar() returns null on 404 silently.
      fetchSar(alertId).catch(() => null),
    ])
      .then(([a, s]) => { setAlert(a); setSar(s); })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [alertId]);

  async function refresh() {
    if (!alertId) return;
    try {
      const fresh = await fetchAmlAlert(alertId);
      setAlert(fresh);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleClaim() {
    if (!alertId) return;
    setActionPending(true);
    try {
      const updated = await claimAmlAlert(alertId);
      setAlert(updated);
      onMutated();
    } catch (e) {
      if (e instanceof AmlConflictError) {
        setError(`Не удалось взять в работу: ${e.reason}`);
        await refresh();
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setActionPending(false);
    }
  }

  async function handleResolveConfirmed() {
    if (!alertId || !decisionDialog) return;
    setActionPending(true);
    try {
      const updated = await resolveAmlAlert(alertId, {
        decision: decisionDialog,
        resolution,
        ...(decisionDialog === "reported" ? { report_reference: reportRef } : {}),
      });
      setAlert(updated);
      setDecisionDialog(null);
      onMutated();
    } catch (e) {
      if (e instanceof AmlConflictError) {
        setError(`Не удалось закрыть: ${e.reason}`);
        await refresh();
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setActionPending(false);
    }
  }

  async function handleReleaseHoldConfirmed() {
    if (!alertId || !releaseReason.trim()) return;
    setActionPending(true);
    try {
      await releaseHeldTransaction(alertId, releaseReason.trim());
      setReleaseHoldOpen(false);
      setReleaseReason("");
      onMutated();
      await refresh();
    } catch (e) {
      if (e instanceof AmlConflictError) {
        setError(`Не удалось снять удержание: ${e.reason}`);
        await refresh();
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setActionPending(false);
    }
  }

  async function handleGenerateSar() {
    if (!alertId) return;
    setActionPending(true);
    try {
      const fresh = await submitSar(alertId);
      setSar(fresh);
      setSarPreviewOpen(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setActionPending(false);
    }
  }

  async function handleDownloadSar(format: "json" | "md") {
    if (!alertId) return;
    try {
      const blob = await downloadSarFile(alertId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sar-${alertId}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleAddNote() {
    if (!alertId || !note.trim()) return;
    setActionPending(true);
    try {
      const updated = await appendAmlNote(alertId, note.trim());
      setAlert(updated);
      setNote("");
      onMutated();
    } catch (e) {
      if (e instanceof AmlConflictError) {
        setError(`Заметка не добавлена: ${e.reason}`);
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setActionPending(false);
    }
  }

  const detailsScrubbed = alert?.details ? scrubPii(alert.details) : null;
  const isTerminal = alert?.status === "resolved"
    || alert?.status === "false_positive"
    || alert?.status === "reported";

  return (
    <>
      <Drawer
        open={open}
        onOpenChange={(o) => { if (!o) onClose(); }}
      >
        <DrawerContent width="lg" ariaLabel="AML alert details">
          <DrawerHeader>
            <div className="flex items-center justify-between gap-3">
              <DrawerTitle>AML-алерт</DrawerTitle>
              {alert && <AmlStatusBadge status={alert.status} />}
            </div>
            {alert && (
              <p className="text-[11px] font-mono text-muted-foreground truncate">{alert.id}</p>
            )}
          </DrawerHeader>

          <DrawerBody>
            {loading && (
              <div className="flex items-center justify-center py-12">
                <Icon icon="svg-spinners:ring-resize" className="text-2xl text-primary" />
              </div>
            )}

            {error && (
              <div className="mb-3 rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            {alert && !loading && (
              <div className="space-y-5">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <AmlSeverityBadge severity={alert.severity} />
                    <span className="text-xs text-muted-foreground">{alert.alert_type}</span>
                  </div>
                  <p className="text-sm text-foreground">{alert.description}</p>
                  <p className="text-xs text-muted-foreground">
                    Создан: {new Date(alert.created_at).toLocaleString("ru-RU")}
                  </p>
                </div>

                {alert.assigned_to && (
                  <div className="rounded-lg border border-border bg-muted/30 p-3 text-sm">
                    <p className="text-xs text-muted-foreground mb-0.5">В работе у</p>
                    <p className="text-foreground" title={alert.assigned_to_email ?? undefined}>
                      {alert.assigned_to_name ?? alert.assigned_to_email ?? `user#${alert.assigned_to}`}
                    </p>
                  </div>
                )}

                {alert.related_transaction && (
                  <div className="rounded-lg border border-primary/40 bg-primary/5 p-3 text-sm">
                    <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                      <Icon icon="solar:link-bold" /> Связанная транзакция
                    </p>
                    {typeof alert.related_transaction === "object" && alert.related_transaction !== null && (
                      <>
                        <Link
                          href={`/transactions/${(alert.related_transaction as { unid?: string }).unid ?? ""}`}
                          className="text-primary text-sm underline-offset-4 hover:underline"
                        >
                          {(alert.related_transaction as { unid?: string }).unid ?? "Открыть транзакцию"}
                        </Link>
                        <span className="ml-2 text-xs text-muted-foreground">
                          · {(alert.related_transaction as { status?: string }).status ?? "—"}
                        </span>
                        {(alert.related_transaction as { status?: string }).status === "on_hold" && !isTerminal && (
                          <div className="mt-2">
                            <Button
                              size="sm"
                              variant="warning"
                              onClick={() => setReleaseHoldOpen(true)}
                              disabled={actionPending}
                            >
                              <Icon icon="solar:shield-cross-linear" />
                              Снять удержание
                            </Button>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}

                {detailsScrubbed && Object.keys(detailsScrubbed).length > 0 && (
                  <div className="rounded-lg border border-border bg-card p-3">
                    <p className="text-xs text-muted-foreground mb-1">Детали (PII скрыта)</p>
                    <pre className="text-[11px] font-mono whitespace-pre-wrap break-words text-foreground/80 max-h-64 overflow-auto">
                      {JSON.stringify(detailsScrubbed, null, 2)}
                    </pre>
                  </div>
                )}

                {alert.investigation_notes && (
                  <div className="rounded-lg border border-border p-3">
                    <p className="text-xs text-muted-foreground mb-1">Заметки расследования</p>
                    <pre className="text-[12px] font-mono whitespace-pre-wrap text-foreground/80 max-h-48 overflow-auto">
                      {alert.investigation_notes}
                    </pre>
                  </div>
                )}

                {alert.resolution && (
                  <div className="rounded-lg border border-success/40 bg-success/5 p-3">
                    <p className="text-xs text-muted-foreground mb-0.5">Решение</p>
                    <p className="text-sm text-foreground">{alert.resolution}</p>
                    {alert.report_reference && (
                      <p className="text-xs text-muted-foreground mt-1">
                        SAR-номер: <span className="font-mono">{alert.report_reference}</span>
                      </p>
                    )}
                  </div>
                )}

                {/* SAR submission card — shown for any reported alert
                    or when a submission already exists. Wave 24 / Story 2.9. */}
                {(alert.status === "reported" || sar) && (
                  <div className="rounded-lg border border-primary/40 bg-primary/5 p-3">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs font-medium text-foreground flex items-center gap-1">
                        <Icon icon="solar:document-text-bold" className="text-primary" />
                        SAR-отчёт
                      </p>
                      {sar && (
                        <span className="text-[11px] text-muted-foreground">
                          {sar.submission_backend} · {sar.status}
                        </span>
                      )}
                    </div>
                    {!sar && (
                      <p className="text-xs text-muted-foreground mb-2">
                        Сформируйте структурированный SAR (JSON + Markdown) для подачи в Финнадзор.
                      </p>
                    )}
                    {sar?.response_body && (
                      <p className="text-[11px] text-muted-foreground mb-2 italic">
                        {sar.response_body}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-2">
                      {!sar ? (
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={handleGenerateSar}
                          disabled={actionPending}
                        >
                          Сформировать SAR
                        </Button>
                      ) : (
                        <>
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => setSarPreviewOpen(true)}
                            disabled={actionPending}
                          >
                            Предпросмотр
                          </Button>
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => handleDownloadSar("md")}
                            disabled={actionPending}
                          >
                            Скачать .md
                          </Button>
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => handleDownloadSar("json")}
                            disabled={actionPending}
                          >
                            Скачать .json
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {!isTerminal && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground">Добавить заметку</p>
                    <textarea
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      rows={3}
                      maxLength={4000}
                      placeholder="Что узнали при расследовании…"
                      className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
                    />
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={handleAddNote}
                      disabled={actionPending || !note.trim()}
                    >
                      Сохранить заметку
                    </Button>
                  </div>
                )}
              </div>
            )}
          </DrawerBody>

          <DrawerFooter>
            {alert && !isTerminal && alert.status === "open" && (
              <Button onClick={handleClaim} disabled={actionPending}>
                Взять в работу
              </Button>
            )}
            {alert && !isTerminal && (
              <>
                <Button
                  variant="secondary"
                  onClick={() => { setDecisionDialog("false_positive"); }}
                  disabled={actionPending}
                >
                  Ложное срабатывание
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => { setDecisionDialog("resolved"); }}
                  disabled={actionPending}
                >
                  Закрыть как решённое
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => { setDecisionDialog("reported"); }}
                  disabled={actionPending}
                >
                  Передать регулятору
                </Button>
              </>
            )}
          </DrawerFooter>
        </DrawerContent>
      </Drawer>

      {/* Confirmation dialog with resolution textarea + (optional) SAR-ref */}
      <Dialog open={decisionDialog !== null} onOpenChange={(o) => { if (!o) setDecisionDialog(null); }}>
        <DialogContent ariaLabel="Подтверждение решения" size="md">
          <DialogHeader>
            <DialogTitle>
              {decisionDialog === "false_positive" && "Ложное срабатывание"}
              {decisionDialog === "resolved" && "Закрыть как решённое"}
              {decisionDialog === "reported" && "Передать регулятору"}
            </DialogTitle>
            <DialogDescription>
              {decisionDialog === "reported"
                ? "После отправки SAR-номера статус нельзя отменить. Убедитесь что отчёт зарегистрирован у регулятора."
                : "Зафиксируйте решение — оно попадёт в audit-log и compliance-отчёт."}
            </DialogDescription>
          </DialogHeader>

          <div className="px-5 py-4 space-y-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                Резолюция (обязательно)
              </label>
              <textarea
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                rows={3}
                maxLength={2000}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
                placeholder="Краткое описание решения…"
              />
            </div>
            {decisionDialog === "reported" && (
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Номер SAR / референс регулятора <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  value={reportRef}
                  onChange={(e) => setReportRef(e.target.value)}
                  maxLength={100}
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground font-mono"
                  placeholder="SAR-2026-001"
                />
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="secondary" onClick={() => setDecisionDialog(null)} disabled={actionPending}>
              Отмена
            </Button>
            <Button
              onClick={handleResolveConfirmed}
              disabled={
                actionPending ||
                !resolution.trim() ||
                (decisionDialog === "reported" && !reportRef.trim())
              }
              variant={decisionDialog === "reported" ? "destructive" : "primary"}
            >
              Подтвердить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Release-from-hold confirmation — Wave 26 / Story 2.11. */}
      <Dialog
        open={releaseHoldOpen}
        onOpenChange={(o) => { if (!o) setReleaseHoldOpen(false); }}
      >
        <DialogContent ariaLabel="Снять удержание" size="md">
          <DialogHeader>
            <DialogTitle>Снять удержание с транзакции</DialogTitle>
            <DialogDescription>
              Транзакция вернётся в статус «pending» и снова будет доступна
              для подписи. Причина будет сохранена в audit-log для compliance-аудита.
            </DialogDescription>
          </DialogHeader>
          <div className="px-5 py-4 space-y-2">
            <label className="block text-xs font-medium text-muted-foreground">
              Причина (обязательно)
            </label>
            <textarea
              value={releaseReason}
              onChange={(e) => setReleaseReason(e.target.value)}
              rows={3}
              maxLength={2000}
              className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
              placeholder="Например: AML-офицер проверил, false-positive."
            />
          </div>
          <DialogFooter>
            <Button
              variant="secondary"
              onClick={() => { setReleaseHoldOpen(false); setReleaseReason(""); }}
              disabled={actionPending}
            >
              Отмена
            </Button>
            <Button
              variant="warning"
              onClick={handleReleaseHoldConfirmed}
              disabled={actionPending || !releaseReason.trim()}
            >
              Снять удержание
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* SAR preview modal — Markdown rendered with monospace fallback. */}
      <Dialog
        open={sarPreviewOpen}
        onOpenChange={(o) => { if (!o) setSarPreviewOpen(false); }}
      >
        <DialogContent ariaLabel="SAR preview" size="lg">
          <DialogHeader>
            <DialogTitle>Предпросмотр SAR</DialogTitle>
            <DialogDescription>
              {sar
                ? `Backend: ${sar.submission_backend} · Статус: ${sar.status}`
                : "—"}
            </DialogDescription>
          </DialogHeader>
          <div className="px-5 py-4 max-h-[60vh] overflow-y-auto">
            <pre className="text-[12px] font-mono whitespace-pre-wrap break-words text-foreground/90">
              {sar?.rendered_markdown ?? ""}
            </pre>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => handleDownloadSar("md")}>
              Скачать .md
            </Button>
            <Button variant="secondary" onClick={() => handleDownloadSar("json")}>
              Скачать .json
            </Button>
            <Button onClick={() => setSarPreviewOpen(false)}>Закрыть</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
