"use client";

// Monitoring-rules admin page (Wave 25, Story 2.10).
// Lists rules, lets admin create / edit / toggle / delete.
// RBAC: visible to company_admin / company_auditor / super_admin.
// Auditors see read-only — write actions are gated server-side (403)
// and we additionally hide them in the UI to avoid sending obviously
// failing requests.

import { useState, useEffect, useCallback } from "react";
import useSWR from "swr";
import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  Dialog, DialogContent, DialogHeader, DialogFooter, DialogTitle, DialogDescription,
} from "@/components/ui/Dialog";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout } from "@/lib/page-layout";
import {
  createRule,
  deleteRule,
  fetchRules,
  updateRule,
  type MonitoringRule,
  type MonitoringRuleCreate,
  type RuleAction,
  type RuleSeverity,
  type RuleType,
} from "@/lib/amlRules";

// ────────────────────────────────────────────────────────────────────
// Static maps — same Russian copy as AML triage badges
// ────────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<RuleType, string> = {
  threshold: "Порог суммы",
  velocity: "Частота",
  blacklist_address: "Чёрный список адресов",
};

const ACTION_LABELS: Record<RuleAction, string> = {
  alert: "Только алерт",
  hold: "Удержание",
  block: "Блокировка",
};

const SEVERITY_LABELS: Record<RuleSeverity, string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  critical: "Критический",
};

const SEVERITY_VARIANT: Record<RuleSeverity, "gray" | "primary" | "warning" | "danger"> = {
  low: "gray",
  medium: "primary",
  high: "warning",
  critical: "danger",
};

const ACTION_VARIANT: Record<RuleAction, "gray" | "warning" | "danger"> = {
  alert: "gray",
  hold: "warning",
  block: "danger",
};

// ────────────────────────────────────────────────────────────────────
// Page
// ────────────────────────────────────────────────────────────────────

export default function RulesPage() {
  const [me, setMe] = useState<{ role?: string; organization_id?: string | null } | null>(null);
  const [editTarget, setEditTarget] = useState<MonitoringRule | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const { data: rules, isLoading, error, mutate } = useSWR<MonitoringRule[]>(
    "aml-rules",
    fetchRules,
    { refreshInterval: 60000 },
  );

  useEffect(() => {
    api.getCurrentUser()
      .then((u) => setMe(u as { role?: string; organization_id?: string | null }))
      .catch(() => setMe(null));
  }, []);

  const role = (me?.role ?? "").toLowerCase();
  const isAdmin = role === "company_admin" || role === "super_admin"
    || role === "platform_admin" || role === "admin";
  const isSuperAdmin = role === "super_admin" || role === "platform_admin" || role === "admin";

  const refresh = useCallback(() => { mutate(); }, [mutate]);

  return (
    <>
      <Header title="Правила мониторинга" />
      <div className={pageLayout.container}>
        <Card>
          <div className="p-4 sm:p-6 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-foreground">
                AML rule engine
              </h2>
              <p className="text-xs text-muted-foreground mt-1 max-w-xl">
                Правила срабатывают на каждой исходящей транзакции.
                Действие <b>«Блокировка»</b> отменяет транзу до отправки в Safina,
                <b> «Удержание»</b> переводит её в статус «На удержании»,
                <b> «Только алерт»</b> создаёт запись в очереди AML без блокировки.
              </p>
            </div>
            {isAdmin && (
              <Button onClick={() => setCreateOpen(true)}>
                <Icon icon="solar:add-circle-linear" />
                Добавить правило
              </Button>
            )}
          </div>
        </Card>

        {error && (
          <Card>
            <div className="p-4 text-sm text-destructive">
              Не удалось загрузить правила: {String(error)}
            </div>
          </Card>
        )}

        <Card>
          <div className="p-0">
            {isLoading && (
              <div className="flex items-center justify-center py-16">
                <Icon icon="svg-spinners:ring-resize" className="text-2xl text-primary" />
              </div>
            )}

            {!isLoading && rules && rules.length === 0 && (
              <div className="py-16 text-center">
                <Icon icon="solar:shield-keyhole-bold" className="text-4xl text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-foreground">Правил пока нет</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Без правил движок пропускает все транзакции. Добавьте threshold/velocity/blacklist чтобы включить контроль.
                </p>
              </div>
            )}

            {!isLoading && rules && rules.length > 0 && (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-4 text-xs font-mono uppercase tracking-wider text-muted-foreground">Название</th>
                      <th className="text-left py-3 px-4 text-xs font-mono uppercase tracking-wider text-muted-foreground">Тип</th>
                      <th className="text-left py-3 px-4 text-xs font-mono uppercase tracking-wider text-muted-foreground">Severity</th>
                      <th className="text-left py-3 px-4 text-xs font-mono uppercase tracking-wider text-muted-foreground">Действие</th>
                      <th className="text-left py-3 px-4 text-xs font-mono uppercase tracking-wider text-muted-foreground">Активно</th>
                      <th className="text-left py-3 px-4 text-xs font-mono uppercase tracking-wider text-muted-foreground">Скоуп</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {rules.map((rule) => {
                      const isGlobal = rule.organization_id === null;
                      const canEdit = isAdmin && (isGlobal ? isSuperAdmin : true);
                      return (
                        <tr key={rule.id} className="hover:bg-muted/30">
                          <td className="py-3 px-4">
                            <div className="text-sm text-foreground font-medium">{rule.rule_name}</div>
                            {rule.description && (
                              <div className="text-xs text-muted-foreground truncate max-w-[24rem]">
                                {rule.description}
                              </div>
                            )}
                          </td>
                          <td className="py-3 px-4 text-xs text-muted-foreground">
                            {TYPE_LABELS[rule.rule_type]}
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant={SEVERITY_VARIANT[rule.severity]} mono>
                              {SEVERITY_LABELS[rule.severity]}
                            </Badge>
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant={ACTION_VARIANT[rule.action]}>
                              {ACTION_LABELS[rule.action]}
                            </Badge>
                          </td>
                          <td className="py-3 px-4">
                            <ActiveToggle
                              rule={rule} canEdit={canEdit} onChange={refresh}
                            />
                          </td>
                          <td className="py-3 px-4 text-xs text-muted-foreground">
                            {isGlobal ? <Badge variant="navy">Global</Badge> : "Org"}
                          </td>
                          <td className="py-3 px-4 text-right">
                            {canEdit && (
                              <div className="flex justify-end gap-1">
                                <Button
                                  size="sm" variant="ghost"
                                  onClick={() => setEditTarget(rule)}
                                >
                                  <Icon icon="solar:pen-linear" />
                                </Button>
                                <DeleteButton rule={rule} onDeleted={refresh} />
                              </div>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </Card>
      </div>

      <RuleFormDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSaved={() => { setCreateOpen(false); refresh(); }}
        defaultOrgId={me?.organization_id ?? null}
        canSetGlobal={isSuperAdmin}
      />

      <RuleFormDialog
        rule={editTarget ?? undefined}
        open={editTarget !== null}
        onClose={() => setEditTarget(null)}
        onSaved={() => { setEditTarget(null); refresh(); }}
        defaultOrgId={editTarget?.organization_id ?? me?.organization_id ?? null}
        canSetGlobal={isSuperAdmin}
      />
    </>
  );
}

// ────────────────────────────────────────────────────────────────────
// Active toggle (inline PATCH)
// ────────────────────────────────────────────────────────────────────

function ActiveToggle({
  rule, canEdit, onChange,
}: { rule: MonitoringRule; canEdit: boolean; onChange: () => void }) {
  const [pending, setPending] = useState(false);
  const handle = async () => {
    if (!canEdit || pending) return;
    setPending(true);
    try {
      await updateRule(rule.id, { is_active: !rule.is_active });
      onChange();
    } catch (e) {
      window.alert(`Не удалось обновить: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setPending(false);
    }
  };
  return (
    <button
      type="button"
      onClick={handle}
      disabled={!canEdit || pending}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
        rule.is_active ? "bg-success" : "bg-muted"
      } disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-card transition-transform ${
          rule.is_active ? "translate-x-4" : "translate-x-0.5"
        }`}
      />
    </button>
  );
}

// ────────────────────────────────────────────────────────────────────
// Delete with confirm
// ────────────────────────────────────────────────────────────────────

function DeleteButton({
  rule, onDeleted,
}: { rule: MonitoringRule; onDeleted: () => void }) {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const handle = async () => {
    setPending(true);
    try {
      await deleteRule(rule.id);
      setOpen(false);
      onDeleted();
    } catch (e) {
      window.alert(`Не удалось удалить: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setPending(false);
    }
  };
  return (
    <>
      <Button size="sm" variant="ghost" onClick={() => setOpen(true)}>
        <Icon icon="solar:trash-bin-2-linear" className="text-destructive" />
      </Button>
      <Dialog open={open} onOpenChange={(o) => !o && setOpen(false)}>
        <DialogContent ariaLabel="Удалить правило" size="sm">
          <DialogHeader>
            <DialogTitle>Удалить правило?</DialogTitle>
            <DialogDescription>
              «{rule.rule_name}» будет удалено навсегда. Связанные алерты сохранятся,
              но новые с этим правилом срабатывать не будут.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setOpen(false)} disabled={pending}>
              Отмена
            </Button>
            <Button variant="destructive" onClick={handle} disabled={pending}>
              Удалить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ────────────────────────────────────────────────────────────────────
// Form dialog (create + edit share the same component)
// ────────────────────────────────────────────────────────────────────

function RuleFormDialog({
  rule, open, onClose, onSaved, defaultOrgId, canSetGlobal,
}: {
  rule?: MonitoringRule;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  defaultOrgId: string | null;
  canSetGlobal: boolean;
}) {
  const isEdit = !!rule;
  const [name, setName] = useState("");
  const [type, setType] = useState<RuleType>("threshold");
  const [description, setDescription] = useState("");
  const [action, setAction] = useState<RuleAction>("alert");
  const [severity, setSeverity] = useState<RuleSeverity>("medium");
  const [isActive, setIsActive] = useState(true);
  const [scope, setScope] = useState<"org" | "global">("org");

  // Type-specific config inputs.
  const [thresholdUsd, setThresholdUsd] = useState("");
  const [velCount, setVelCount] = useState("10");
  const [velWindow, setVelWindow] = useState("1");
  const [blacklist, setBlacklist] = useState("");

  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    if (rule) {
      setName(rule.rule_name);
      setType(rule.rule_type);
      setDescription(rule.description ?? "");
      setAction(rule.action);
      setSeverity(rule.severity);
      setIsActive(rule.is_active);
      setScope(rule.organization_id === null ? "global" : "org");
      const cfg = rule.rule_config as Record<string, unknown>;
      if (rule.rule_type === "threshold") {
        const thr = cfg.threshold_usd ?? cfg.threshold;
        setThresholdUsd(thr != null ? String(thr) : "");
      } else if (rule.rule_type === "velocity") {
        setVelCount(String(cfg.count ?? 10));
        setVelWindow(String(cfg.window_hours ?? 1));
      } else if (rule.rule_type === "blacklist_address") {
        const addrs = (cfg.addresses as string[]) ?? [];
        setBlacklist(addrs.join("\n"));
      }
    } else {
      setName("");
      setType("threshold");
      setDescription("");
      setAction("alert");
      setSeverity("medium");
      setIsActive(true);
      setScope("org");
      setThresholdUsd("");
      setVelCount("10");
      setVelWindow("1");
      setBlacklist("");
    }
  }, [open, rule]);

  function buildConfig(): Record<string, unknown> | null {
    if (type === "threshold") {
      const n = Number(thresholdUsd);
      if (!Number.isFinite(n) || n <= 0) {
        setError("Порог должен быть положительным числом");
        return null;
      }
      return { threshold_usd: n };
    }
    if (type === "velocity") {
      const c = parseInt(velCount, 10);
      const w = parseInt(velWindow, 10);
      if (!Number.isInteger(c) || c <= 0) { setError("count должен быть > 0"); return null; }
      if (!Number.isInteger(w) || w <= 0) { setError("window_hours должен быть > 0"); return null; }
      return { count: c, window_hours: w };
    }
    if (type === "blacklist_address") {
      const addrs = blacklist
        .split(/\s+/)
        .map((s) => s.trim())
        .filter(Boolean);
      if (addrs.length === 0) { setError("Минимум один адрес"); return null; }
      return { addresses: addrs };
    }
    return null;
  }

  const handleSave = async () => {
    setError(null);
    if (!name.trim()) { setError("Название обязательно"); return; }
    const cfg = buildConfig();
    if (!cfg) return;
    const orgId = scope === "global" ? null : (defaultOrgId ?? rule?.organization_id ?? null);
    setPending(true);
    try {
      if (isEdit && rule) {
        await updateRule(rule.id, {
          rule_name: name.trim(),
          rule_type: type,
          description: description.trim() || undefined,
          rule_config: cfg,
          action,
          severity,
          is_active: isActive,
        });
      } else {
        const body: MonitoringRuleCreate = {
          organization_id: orgId,
          rule_name: name.trim(),
          rule_type: type,
          description: description.trim() || undefined,
          rule_config: cfg,
          action,
          severity,
          is_active: isActive,
        };
        await createRule(body);
      }
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPending(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent ariaLabel="Правило мониторинга" size="lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Редактировать правило" : "Новое правило"}</DialogTitle>
          <DialogDescription>
            Изменения активируются сразу — следующая транзакция уже проходит через обновлённый набор правил.
          </DialogDescription>
        </DialogHeader>

        <div className="px-5 py-4 space-y-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Название *</label>
            <input
              value={name} onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
              maxLength={255} placeholder="Threshold $10k"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Описание</label>
            <textarea
              value={description} onChange={(e) => setDescription(e.target.value)}
              rows={2} maxLength={2000}
              className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
              placeholder="Что это правило проверяет и почему включено."
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Тип</label>
              <select
                value={type} onChange={(e) => setType(e.target.value as RuleType)}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
              >
                {(Object.keys(TYPE_LABELS) as RuleType[]).map((t) => (
                  <option key={t} value={t}>{TYPE_LABELS[t]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Severity</label>
              <select
                value={severity} onChange={(e) => setSeverity(e.target.value as RuleSeverity)}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
              >
                {(Object.keys(SEVERITY_LABELS) as RuleSeverity[]).map((s) => (
                  <option key={s} value={s}>{SEVERITY_LABELS[s]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Действие</label>
              <select
                value={action} onChange={(e) => setAction(e.target.value as RuleAction)}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
              >
                {(Object.keys(ACTION_LABELS) as RuleAction[]).map((a) => (
                  <option key={a} value={a}>{ACTION_LABELS[a]}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Type-specific config */}
          {type === "threshold" && (
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                Порог (USD)
              </label>
              <input
                type="number" value={thresholdUsd}
                onChange={(e) => setThresholdUsd(e.target.value)}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
                placeholder="10000"
              />
            </div>
          )}

          {type === "velocity" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Количество транзакций
                </label>
                <input
                  type="number" value={velCount}
                  onChange={(e) => setVelCount(e.target.value)}
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  За окно (часы)
                </label>
                <input
                  type="number" value={velWindow}
                  onChange={(e) => setVelWindow(e.target.value)}
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
                />
              </div>
            </div>
          )}

          {type === "blacklist_address" && (
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                Адреса (по одному в строке)
              </label>
              <textarea
                value={blacklist} onChange={(e) => setBlacklist(e.target.value)}
                rows={4}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground font-mono"
                placeholder="0xBAD1...&#10;0xBAD2..."
              />
            </div>
          )}

          {canSetGlobal && (
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Скоуп</label>
              <select
                value={scope} onChange={(e) => setScope(e.target.value as "org" | "global")}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
                disabled={isEdit}
              >
                <option value="org">Только моя организация</option>
                <option value="global">Глобальное правило (все организации)</option>
              </select>
            </div>
          )}

          <label className="inline-flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox" checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
            />
            Активно
          </label>

          {error && (
            <div className="text-xs text-destructive">{error}</div>
          )}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={onClose} disabled={pending}>Отмена</Button>
          <Button onClick={handleSave} disabled={pending}>
            {isEdit ? "Сохранить" : "Создать"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
