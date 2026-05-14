"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { CopyButton } from "@/components/common/CopyButton";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { CryptoIcon } from "@/components/common/CryptoIcon";
import { formatValue } from "@/lib/utils";
import { api } from "@/lib/api";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";
import { formatWalletDisplayName, networkName } from "@/lib/walletDisplay";

export default function WalletDetailPage() {
  const params = useParams();
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

  return (
    <>
      <Header title="Кошелёк" />
      <div className="space-y-4 p-2 sm:p-4 md:p-6 lg:p-8 max-w-3xl">
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
