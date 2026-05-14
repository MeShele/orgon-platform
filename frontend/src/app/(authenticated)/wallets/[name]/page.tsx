"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { CopyButton } from "@/components/common/CopyButton";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { CryptoIcon } from "@/components/common/CryptoIcon";
import { Button } from "@/components/ui/Button";
import { formatValue } from "@/lib/utils";
import { api } from "@/lib/api";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";
import { formatWalletDisplayName, networkName } from "@/lib/walletDisplay";

// Pull email signers out of slist so the pending banner can name the
// exact mailbox the user must check.
function emailSignersOf(slist: unknown): string[] {
  if (!slist || typeof slist !== "object") return [];
  return Object.entries(slist as Record<string, unknown>)
    .filter(([k]) => k !== "min_signs")
    .map(([, v]) => (v as Record<string, unknown>)?.email)
    .filter((e): e is string => typeof e === "string" && e.length > 0);
}

function PendingStatusBanner({ emails }: { emails: string[] }) {
  // Steps reflect Safina's wallet lifecycle: request created → all
  // slist signers confirm → addr issued on-chain. We highlight step 2
  // because that's where the user has to take action.
  const steps = [
    { label: "Заявка создана", state: "done" as const, icon: "solar:check-circle-bold" },
    { label: "Подтверждение подписантов", state: "active" as const, icon: "solar:letter-bold" },
    { label: "Выдача on-chain адреса", state: "pending" as const, icon: "solar:wallet-money-bold" },
    { label: "Готов к работе", state: "pending" as const, icon: "solar:shield-check-bold" },
  ];
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-xl border border-warning/30 bg-warning/5 p-4"
    >
      <div className="flex items-start gap-3">
        <span className="relative mt-0.5 flex h-2 w-2 shrink-0">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-warning opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-warning" />
        </span>
        <div className="space-y-1 flex-1">
          <p className="text-sm font-medium text-foreground">Кошелёк создаётся в Safina</p>
          {emails.length > 0 ? (
            <p className="text-xs text-muted-foreground leading-relaxed">
              На&nbsp;
              <span className="font-mono text-foreground">{emails[0]}</span>
              {emails.length > 1 ? <> и&nbsp;ещё {emails.length - 1}</> : null}
              &nbsp;отправлено письмо с&nbsp;подтверждением. Проверьте папку <strong>Spam</strong> и&nbsp;нажмите ссылку — после этого Safina выдаст on-chain адрес. Обычно занимает <strong>5–10&nbsp;минут</strong>.
            </p>
          ) : (
            <p className="text-xs text-muted-foreground leading-relaxed">
              Safina формирует кошелёк и&nbsp;выдаёт on-chain адрес. Обычно занимает <strong>5–10&nbsp;минут</strong>. Адрес появится на&nbsp;этой странице автоматически.
            </p>
          )}
        </div>
      </div>
      <ol className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((s, i) => (
          <li
            key={i}
            className={
              s.state === "done"
                ? "rounded-lg border border-success/30 bg-success/5 px-3 py-2"
                : s.state === "active"
                ? "rounded-lg border border-warning/40 bg-warning/10 px-3 py-2"
                : "rounded-lg border border-border bg-muted/40 px-3 py-2"
            }
          >
            <div className="flex items-center gap-2 text-[11px] font-medium">
              <Icon
                icon={s.icon}
                className={
                  s.state === "done"
                    ? "text-success text-base"
                    : s.state === "active"
                    ? "text-warning text-base"
                    : "text-muted-foreground text-base"
                }
              />
              <span
                className={
                  s.state === "pending"
                    ? "text-muted-foreground"
                    : "text-foreground"
                }
              >
                {s.label}
              </span>
            </div>
          </li>
        ))}
      </ol>
    </motion.div>
  );
}

export default function WalletDetailPage() {
  const params = useParams();
  const router = useRouter();
  const name = params.name as string;
  const [wallet, setWallet] = useState<Record<string, unknown> | null>(null);
  const [tokens, setTokens] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getWallet(name).then(setWallet).catch((e) => setError(e.message));
    api.getWalletTokens(name).then(setTokens).catch(() => {});
  }, [name]);

  if (error) {
    return (
      <>
        <Header title="Кошелёк" />
        <div className="p-4 sm:p-6 lg:p-8">
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-xs text-destructive">
            {error}
          </div>
        </div>
      </>
    );
  }

  if (!wallet) {
    return (
      <>
        <Header title="Кошелёк" />
        <div className="p-6"><LoadingSpinner /></div>
      </>
    );
  }

  const primaryAddr =
    (wallet.addrs as string | null)?.split(",")[0]?.trim() ||
    (wallet.addr as string | null) ||
    "";
  const isPending = !primaryAddr;
  const emails = emailSignersOf(wallet.slist);

  return (
    <>
      <Header title="Кошелёк" />
      <div className="space-y-4 p-2 sm:p-4 md:p-6 lg:p-8 max-w-3xl">
        {isPending ? <PendingStatusBanner emails={emails} /> : null}
        <Card>
          <CardHeader
            title={
              String(wallet.info ?? "").trim() ||
              formatWalletDisplayName({
                label: (wallet.label as string | null) ?? null,
                name: (wallet.name as string | null) ?? name,
                wallet_name: (wallet.wallet_name as string | null) ?? null,
                my_unid: (wallet.my_unid as string | null) ?? (wallet.unid as string | null) ?? null,
                addr: (wallet.addr as string | null) ?? null,
                network: (wallet.network as number | string | null) ?? null,
              })
            }
            subtitle={`Сеть: ${networkName((wallet.network as number | string | null) ?? null)}`}
            action={
              <div className="flex items-center gap-2">
                {primaryAddr ? <CopyButton text={primaryAddr} /> : null}
                <Button
                  variant="primary"
                  size="sm"
                  disabled={!primaryAddr}
                  onClick={() => router.push(`/wallets/${name}/send`)}
                  title={primaryAddr ? "Отправить из этого кошелька" : "Доступно после активации"}
                >
                  <Icon icon="solar:plain-linear" className="text-base" />
                  Отправить
                </Button>
              </div>
            }
          />
          <div className="space-y-4 p-4">
            <div>
              <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
                Идентификатор кошелька
                <HelpTooltip text={helpContent.walletDetail.walletName.text} />
              </p>
              <div className="flex items-center gap-2">
                <p className="font-mono text-xs text-foreground">{String(wallet.wallet_name || name)}</p>
                <CopyButton text={String(wallet.wallet_name || name)} />
              </div>
            </div>
            {(() => {
              const raw = (wallet.addrs as string | null) ?? (wallet.addr as string | null);
              const list = (raw ? String(raw).split(",").map((a) => a.trim()).filter(Boolean) : []);
              if (!list.length) return null;
              return (
                <div>
                  <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
                    {list.length > 1 ? "Адреса" : "Адрес"}
                    <HelpTooltip text={helpContent.walletDetail.addresses.text} />
                  </p>
                  <div className="space-y-1.5">
                    {list.map((addr, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <p className="font-mono text-xs text-foreground">{addr}</p>
                        <CopyButton text={addr} />
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}
            {wallet.unid ? (
              <div>
                <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
                  UNID создания
                  <HelpTooltip text={helpContent.walletDetail.creationUnid.text} />
                </p>
                <p className="font-mono text-xs text-muted-foreground">{String(wallet.unid)}</p>
              </div>
            ) : null}
            {wallet.wallet_type !== undefined && wallet.wallet_type !== null ? (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5">Тип кошелька</p>
                <p className="font-mono text-xs text-foreground">
                  {Number(wallet.wallet_type) === 1 ? "MULTI-SIG (горячий)" : `STANDARD (тип ${String(wallet.wallet_type)})`}
                </p>
              </div>
            ) : null}
            {wallet.safina_signer ? (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5">EC, подписывающий запросы</p>
                <div className="flex items-center gap-2">
                  <p className="font-mono text-xs text-foreground">{String(wallet.safina_signer)}</p>
                  <CopyButton text={String(wallet.safina_signer)} />
                </div>
              </div>
            ) : null}
            {wallet.slist ? (() => {
              const slist = wallet.slist as Record<string, unknown>;
              const minSigns = slist.min_signs ? String(slist.min_signs) : null;
              const signers = Object.entries(slist).filter(([k]) => k !== "min_signs");
              return (
                <div>
                  <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
                    Подписанты {minSigns ? `(требуется ${minSigns})` : ""}
                    <HelpTooltip text={helpContent.walletDetail.signers.text} diagram={helpContent.walletDetail.signers.diagram} />
                  </p>
                  <div className="space-y-2">
                    {signers.map(([idx, raw]) => {
                      const s = raw as Record<string, unknown>;
                      return (
                        <div key={idx} className="rounded-lg border border-border bg-muted/40 p-3 text-xs space-y-1 dark:bg-card/40">
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <span className="font-medium">#{idx}</span>
                            <span>тип:</span>
                            <span className="font-mono">{String(s.type ?? "—")}</span>
                          </div>
                          {s.ecaddress ? (
                            <div className="flex items-center gap-2"><span className="text-muted-foreground w-16">EC:</span><span className="font-mono text-foreground">{String(s.ecaddress)}</span><CopyButton text={String(s.ecaddress)} /></div>
                          ) : null}
                          {s.email ? (
                            <div className="flex items-center gap-2"><span className="text-muted-foreground w-16">Email:</span><span className="font-mono text-foreground">{String(s.email)}</span></div>
                          ) : null}
                          {s.sms ? (
                            <div className="flex items-center gap-2"><span className="text-muted-foreground w-16">SMS:</span><span className="font-mono text-foreground">{String(s.sms)}</span></div>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })() : null}
          </div>
        </Card>

        <Card>
          <CardHeader title="Токены" subtitle="Балансы токенов в этом кошельке" />
          <div className="p-4">
            {tokens.length === 0 ? (
              <p className="text-xs text-muted-foreground">Нет токенов на балансе</p>
            ) : (
              <div className="space-y-2">
                {tokens.map((t, i) => {
                  const tokenStr = String(t.token || "");
                  const tokenName = tokenStr.includes(":::") ? tokenStr.split(":::")[1] : tokenStr;
                  return (
                    <div key={i} className="flex items-center justify-between rounded-lg border border-border px-4 py-3">
                      <div className="flex items-center gap-3">
                        <CryptoIcon token={tokenName} size="md" />
                        <div>
                          <p className="text-xs font-medium text-foreground">{tokenName}</p>
                          <p className="text-[10px] text-muted-foreground">Сеть: {String(t.network)}</p>
                        </div>
                      </div>
                      <p className="text-sm font-semibold text-foreground">{formatValue(String(t.value))}</p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </Card>
      </div>
    </>
  );
}
