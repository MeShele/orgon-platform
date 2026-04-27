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
        <Header title="Wallet Detail" />
        <div className="p-4 sm:p-6 lg:p-8">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-xs text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-400">
            {error}
          </div>
        </div>
      </>
    );
  }

  if (!wallet) {
    return (
      <>
        <Header title="Wallet Detail" />
        <div className="p-6"><LoadingSpinner /></div>
      </>
    );
  }

  return (
    <>
      <Header title="Wallet Detail" />
      <div className="space-y-4 p-2 sm:p-4 md:p-6 lg:p-8 max-w-3xl">
        <Card>
          <CardHeader
            title={String(wallet.info || wallet.wallet_name || name)}
            subtitle={`Network: ${wallet.network}`}
          />
          <div className="space-y-4 p-4">
            <div>
              <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
                Wallet Name
                <HelpTooltip text={helpContent.walletDetail.walletName.text} />
              </p>
              <div className="flex items-center gap-2">
                <p className="font-mono text-xs text-foreground">{String(wallet.wallet_name || name)}</p>
                <CopyButton text={String(wallet.wallet_name || name)} />
              </div>
            </div>
            {wallet.addrs ? (
              <div>
                <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
                  Addresses
                  <HelpTooltip text={helpContent.walletDetail.addresses.text} />
                </p>
                <div className="space-y-1.5">
                  {String(wallet.addrs).split(",").map((addr, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <p className="font-mono text-xs text-foreground">{addr}</p>
                      <CopyButton text={addr} />
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            {wallet.unid ? (
              <div>
                <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
                  Creation UNID
                  <HelpTooltip text={helpContent.walletDetail.creationUnid.text} />
                </p>
                <p className="font-mono text-xs text-muted-foreground">{String(wallet.unid)}</p>
              </div>
            ) : null}
            {wallet.slist ? (
              <div>
                <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
                  Signers (Multi-sig)
                  <HelpTooltip text={helpContent.walletDetail.signers.text} diagram={helpContent.walletDetail.signers.diagram} />
                </p>
                <pre className="mt-1 rounded-lg border border-border bg-muted p-3 text-[10px] font-mono text-muted-foreground dark:border-border dark:bg-card/50 dark:text-muted-foreground">
                  {JSON.stringify(wallet.slist, null, 2)}
                </pre>
              </div>
            ) : null}
          </div>
        </Card>

        <Card>
          <CardHeader title="Tokens" subtitle="Token balances in this wallet" />
          <div className="p-4">
            {tokens.length === 0 ? (
              <p className="text-xs text-muted-foreground">No tokens found</p>
            ) : (
              <div className="space-y-2">
                {tokens.map((t, i) => {
                  const tokenStr = String(t.token || "");
                  const tokenName = tokenStr.includes(":::") ? tokenStr.split(":::")[1] : tokenStr;
                  return (
                    <div key={i} className="flex items-center justify-between rounded-lg border border-slate-100 px-4 py-3 dark:border-border">
                      <div className="flex items-center gap-3">
                        <CryptoIcon token={tokenName} size="md" />
                        <div>
                          <p className="text-xs font-medium text-foreground">{tokenName}</p>
                          <p className="text-[10px] text-muted-foreground">Network: {String(t.network)}</p>
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
