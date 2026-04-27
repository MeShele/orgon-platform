"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "@/hooks/useTranslations";
import { Header } from "@/components/layout/Header";
import { NetworkIcon } from "@/components/common/CryptoIcon";
import { StatusDot } from "@/components/common/StatusBadge";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { api } from "@/lib/api";
import { pageLayout } from "@/lib/page-layout";

type Network = {
  network_id: number;
  network_name: string;
  link: string;
  address_explorer: string;
  tx_explorer: string;
  status: number;
};

function isTestnet(name: string): boolean {
  const lower = name.toLowerCase();
  return lower.includes("test") || lower.includes("sepolia") || lower.includes("nile");
}

export default function NetworksPage() {
  const t = useTranslations('networks');
  const [networks, setNetworks] = useState<Network[]>([]);
  const [tokensInfo, setTokensInfo] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getNetworks(), api.getTokensInfo()])
      .then(([nets, tokens]) => {
        setNetworks(nets);
        setTokensInfo(tokens);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <>
        <Header title={t('title')} />
        <div className="p-6"><LoadingSpinner /></div>
      </>
    );
  }

  return (
    <>
      <Header title={t('title')} />
      <div className={pageLayout.container}>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {networks.map((net) => (
            <div
              key={net.network_id}
              className="rounded-xl border border-border bg-card p-4 shadow-sm transition-all hover:border-border dark:bg-card/40 dark:shadow-none dark:hover:border-border"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <NetworkIcon networkName={net.network_name} isTestnet={isTestnet(net.network_name)} />
                  <div>
                    <div className="text-xs font-medium text-foreground">{net.network_name}</div>
                    <div className="font-mono text-[10px] text-muted-foreground">{t('id')}: {net.network_id}</div>
                  </div>
                </div>
                <StatusDot active={net.status === 1} />
              </div>

              {net.link && (
                <a href={net.link} target="_blank" rel="noreferrer" className="text-[10px] text-muted-foreground hover:text-foreground dark:hover:text-primary-foreground transition-colors">
                  {net.link}
                </a>
              )}

              <div className="mt-3 border-t border-border pt-3">
                <p className="text-[10px] font-medium text-muted-foreground mb-2">{t('supportedTokens')}</p>
                <div className="flex flex-wrap gap-1">
                  {tokensInfo
                    .filter((t) => String(t.token).startsWith(String(net.network_id)))
                    .map((t) => (
                      <span key={String(t.token)} className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-foreground dark:bg-muted dark:text-faint">
                        {String(t.token).split(":::")[1]}
                      </span>
                    ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
