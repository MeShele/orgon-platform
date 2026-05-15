"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import toast from "react-hot-toast";

import { Card, CardHeader } from "@/components/common/Card";
import { CopyButton } from "@/components/common/CopyButton";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";

type KeyRow = {
  id: string;
  key_pub: string;
  label: string | null;
  scopes: string[];
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
};

type IssueResponse = {
  id: string;
  key_pub: string;
  secret_once: string;
  scopes: string[];
  label: string | null;
  warning: string;
};

const ALL_SCOPES: { value: string; label: string; desc: string }[] = [
  { value: "users:read", label: "users:read", desc: "Список / получение end-users" },
  { value: "users:write", label: "users:write", desc: "Создание / обновление end-users" },
  { value: "wallets:read", label: "wallets:read", desc: "Чтение кошельков и балансов" },
  { value: "wallets:write", label: "wallets:write", desc: "Создание кошельков" },
  { value: "tx:read", label: "tx:read", desc: "Чтение транзакций" },
  { value: "tx:send", label: "tx:send", desc: "Инициация и подпись транзакций" },
];

export function ApiKeysSection({ merchantId }: { merchantId: string | null }) {
  const [keys, setKeys] = useState<KeyRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // create modal
  const [creating, setCreating] = useState(false);
  const [label, setLabel] = useState("");
  const [sandbox, setSandbox] = useState(false);
  const [scopes, setScopes] = useState<string[]>([
    "users:read",
    "users:write",
    "wallets:read",
    "wallets:write",
    "tx:read",
    "tx:send",
  ]);
  const [submitting, setSubmitting] = useState(false);

  // one-time reveal
  const [revealed, setRevealed] = useState<IssueResponse | null>(null);

  const refresh = useCallback(async () => {
    if (!merchantId) {
      setLoading(false);
      return;
    }
    try {
      const rows = (await api.listMerchantApiKeys(merchantId)) as KeyRow[];
      setKeys(Array.isArray(rows) ? rows : []);
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить ключи");
    } finally {
      setLoading(false);
    }
  }, [merchantId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onIssue = async () => {
    if (!merchantId) return;
    setSubmitting(true);
    try {
      const res = (await api.issueMerchantApiKey(merchantId, {
        label: label || undefined,
        scopes,
        sandbox,
      })) as IssueResponse;
      setRevealed(res);
      setCreating(false);
      setLabel("");
      void refresh();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Не удалось выпустить ключ");
    } finally {
      setSubmitting(false);
    }
  };

  const onRevoke = async (keyId: string) => {
    if (!merchantId) return;
    if (!confirm("Отозвать ключ? Это действие необратимо.")) return;
    try {
      await api.revokeMerchantApiKey(merchantId, keyId);
      toast.success("Ключ отозван");
      void refresh();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Ошибка отзыва");
    }
  };

  if (!merchantId) {
    return (
      <Card>
        <CardHeader title="API ключи" subtitle="Доступ к публичному API /v1/*" />
        <div className="p-4 text-xs text-muted-foreground">
          У вас нет привязки к организации — обратитесь к администратору.
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader
          title="API ключи"
          subtitle="Доступ к публичному API /v1/* для интеграции"
          action={
            <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
              <Icon icon="solar:key-bold" className="text-base" />
              Выпустить ключ
            </Button>
          }
        />
        <div className="p-4 space-y-3">
          {loading ? (
            <div className="py-6"><LoadingSpinner /></div>
          ) : error ? (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
              {error}
            </div>
          ) : keys.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Ключей нет. Выпустите первый — он понадобится merchant-у для подписи запросов к /v1/*.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="text-muted-foreground border-b border-border">
                  <tr className="text-left">
                    <th className="py-2 pr-3 font-medium">Метка</th>
                    <th className="py-2 pr-3 font-medium">Public key</th>
                    <th className="py-2 pr-3 font-medium">Среда</th>
                    <th className="py-2 pr-3 font-medium">Scopes</th>
                    <th className="py-2 pr-3 font-medium">Использован</th>
                    <th className="py-2 pr-3 font-medium">Статус</th>
                    <th />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {keys.map((k) => {
                    const env = k.key_pub.startsWith("okt_") ? "sandbox" : "live";
                    const revoked = !!k.revoked_at;
                    return (
                      <tr key={k.id} className={revoked ? "opacity-60" : ""}>
                        <td className="py-2 pr-3">{k.label ?? <span className="text-muted-foreground">—</span>}</td>
                        <td className="py-2 pr-3 font-mono flex items-center gap-1">
                          <span>{shortPub(k.key_pub)}</span>
                          <CopyButton text={k.key_pub} />
                        </td>
                        <td className="py-2 pr-3">
                          <span className={env === "sandbox" ? "rounded-full bg-warning/15 text-warning px-2 py-0.5 text-[10px]" : "rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]"}>
                            {env}
                          </span>
                        </td>
                        <td className="py-2 pr-3 font-mono text-[10px] text-muted-foreground">
                          {(k.scopes || []).join(", ") || "—"}
                        </td>
                        <td className="py-2 pr-3 text-muted-foreground">
                          {k.last_used_at ? new Date(k.last_used_at).toLocaleString("ru-RU") : "—"}
                        </td>
                        <td className="py-2 pr-3">
                          {revoked ? (
                            <span className="rounded-full bg-destructive/15 text-destructive px-2 py-0.5 text-[10px]">отозван</span>
                          ) : (
                            <span className="rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]">активен</span>
                          )}
                        </td>
                        <td className="py-2 pr-3">
                          {!revoked ? (
                            <button
                              onClick={() => onRevoke(k.id)}
                              className="text-xs text-destructive hover:underline"
                            >
                              Отозвать
                            </button>
                          ) : null}
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

      <AnimatePresence>
        {creating ? (
          <Modal onClose={() => setCreating(false)}>
            <h3 className="text-sm font-medium mb-3">Новый API ключ</h3>
            <div className="space-y-3 text-xs">
              <Field label="Метка (для себя)">
                <input
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  placeholder="prod / rotation 2026Q3 / тест-интеграции"
                  className={fieldClass}
                  maxLength={80}
                />
              </Field>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={sandbox} onChange={(e) => setSandbox(e.target.checked)} />
                <span>Sandbox-ключ (только testnet, отдельный merchant scope)</span>
              </label>
              <div>
                <p className="text-muted-foreground mb-1.5">Scopes</p>
                <div className="space-y-1">
                  {ALL_SCOPES.map((s) => (
                    <label key={s.value} className="flex items-start gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={scopes.includes(s.value)}
                        onChange={(e) => {
                          setScopes((cur) =>
                            e.target.checked ? [...cur, s.value] : cur.filter((x) => x !== s.value),
                          );
                        }}
                      />
                      <span>
                        <span className="font-mono">{s.label}</span>{" "}
                        <span className="text-muted-foreground">— {s.desc}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-3">
                <Button variant="secondary" size="sm" onClick={() => setCreating(false)} disabled={submitting}>
                  Отмена
                </Button>
                <Button variant="primary" size="sm" onClick={onIssue} disabled={submitting || scopes.length === 0} loading={submitting}>
                  Выпустить
                </Button>
              </div>
            </div>
          </Modal>
        ) : null}

        {revealed ? (
          <Modal onClose={() => setRevealed(null)} wide>
            <h3 className="text-sm font-medium mb-1">Ключ выпущен</h3>
            <p className="text-xs text-muted-foreground mb-3">{revealed.warning}</p>
            <Field label="Public key (X-ORGON-Key)">
              <div className="flex items-center gap-2 rounded-lg border border-border bg-muted px-3 py-2 font-mono text-[11px]">
                <span className="flex-1 break-all">{revealed.key_pub}</span>
                <CopyButton text={revealed.key_pub} />
              </div>
            </Field>
            <Field label="Secret (для подписи HMAC) — показывается один раз">
              <div className="flex items-center gap-2 rounded-lg border border-warning/40 bg-warning/5 px-3 py-2 font-mono text-[11px]">
                <span className="flex-1 break-all">{revealed.secret_once}</span>
                <CopyButton text={revealed.secret_once} />
              </div>
            </Field>
            <div className="rounded-lg border border-border bg-muted/30 p-3 text-[11px] text-muted-foreground space-y-1">
              <p className="font-medium text-foreground">Как использовать</p>
              <p>
                В каждом запросе к <code className="font-mono">/v1/*</code> добавьте заголовки:
              </p>
              <pre className="rounded bg-card px-2 py-1 text-[10px] overflow-x-auto">{`X-ORGON-Key: ${revealed.key_pub}
X-ORGON-Timestamp: <unix ms>
X-ORGON-Nonce: <uuid>
X-ORGON-Signature: hex(HMAC-SHA256(secret, ts + '\\n' + nonce + '\\n' + METHOD + '\\n' + path + '\\n' + body))`}</pre>
            </div>
            <div className="flex justify-end gap-2 pt-3">
              <Button variant="primary" size="sm" onClick={() => setRevealed(null)}>
                Я сохранил secret
              </Button>
            </div>
          </Modal>
        ) : null}
      </AnimatePresence>
    </>
  );
}

const fieldClass =
  "w-full rounded-lg border border-border bg-muted px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/30 transition-colors";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-xs text-muted-foreground mb-1.5 block">{label}</label>
      {children}
    </div>
  );
}

function shortPub(s: string) {
  if (s.length <= 16) return s;
  return `${s.slice(0, 10)}…${s.slice(-6)}`;
}

function Modal({
  children,
  onClose,
  wide = false,
}: {
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
    >
      <motion.div
        className={`relative rounded-xl border border-border bg-card p-5 shadow-lg ${wide ? "w-full max-w-2xl" : "w-full max-w-md"}`}
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, y: 12, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 12, scale: 0.98 }}
        transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
      >
        <button
          onClick={onClose}
          aria-label="Закрыть"
          className="absolute top-3 right-3 text-muted-foreground hover:text-foreground"
        >
          <Icon icon="solar:close-circle-linear" className="text-lg" />
        </button>
        {children}
      </motion.div>
    </motion.div>
  );
}
