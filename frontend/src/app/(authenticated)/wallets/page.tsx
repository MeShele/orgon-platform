"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "@/hooks/useTranslations";
import { Header } from "@/components/layout/Header";
import { Eyebrow, BigNum, Mono } from "@/components/ui/primitives";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/lib/icons";
import { api, API_BASE } from "@/lib/api";
import { formatWalletDisplayName, networkName } from "@/lib/walletDisplay";

interface Wallet {
  id?: number;
  name?: string;
  label?: string | null;
  network?: number;
  my_unid?: string;
  is_favorite?: boolean;
  addr?: string;
  organization_id?: string | null;
  wallet_type?: number;
  token_short_names?: string;
  created_at?: string;
}

export default function WalletsPage() {
  const t = useTranslations("wallets");
  const router = useRouter();
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    api
      .getWallets()
      .then((data) => setWallets(Array.isArray(data) ? data : []))
      .catch((err) => setError(err.message ?? "Не удалось загрузить кошельки"))
      .finally(() => setLoading(false));
  }, []);

  function handleExport() {
    setExporting(true);
    try {
      window.open(`${API_BASE}/export/wallets/csv`, "_blank");
    } finally {
      setTimeout(() => setExporting(false), 600);
    }
  }

  const totalCount = wallets.length;
  const favCount = wallets.filter((w) => w.is_favorite).length;

  return (
    <>
      <Header title={t("title")} />

      <div className="px-4 sm:px-6 lg:px-10 py-8 space-y-6">
        {/* Top bar */}
        <div className="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <Eyebrow dash>Кошельки</Eyebrow>
            <h2 className="mt-2 text-[24px] sm:text-[28px] font-medium tracking-[-0.02em] text-foreground">
              {totalCount > 0 ? `${totalCount} ${pluralize(totalCount, ["кошелёк", "кошелька", "кошельков"])}` : "Нет кошельков"}
              {favCount > 0 && (
                <span className="ml-3 text-[14px] text-muted-foreground font-normal">
                  · {favCount} в избранном
                </span>
              )}
            </h2>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" size="md" onClick={handleExport} disabled={exporting || loading || totalCount === 0} loading={exporting}>
              <Icon icon="solar:download-linear" className="text-[15px]" />
              {t("exportButton")}
            </Button>
            <Button variant="primary" size="md" onClick={() => router.push("/wallets/new")}>
              <Icon icon="solar:add-circle-linear" className="text-[15px]" />
              Создать кошелёк
            </Button>
          </div>
        </div>

        {error && (
          <div className="border border-destructive/40 bg-destructive/5 p-4 text-[13px] text-destructive">
            {error}
          </div>
        )}

        {/* Wallet table */}
        <div className="border border-border bg-card overflow-x-auto">
          <table className="w-full text-[13px] border-collapse">
            <thead>
              <tr className="border-b border-border text-left">
                <Th className="px-5">Название</Th>
                <Th>Сеть</Th>
                <Th>Тип</Th>
                <Th>Адрес</Th>
                <Th>Токены</Th>
                <Th className="text-right pr-5">UNID</Th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center text-muted-foreground">
                    Загрузка…
                  </td>
                </tr>
              ) : wallets.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-16 text-center">
                    <Icon icon="solar:wallet-linear" className="text-[48px] text-faint" />
                    <p className="mt-3 text-[14px] text-muted-foreground">Кошельков пока нет</p>
                    <Link href="/wallets/new" className="inline-block mt-4">
                      <Button variant="primary" size="sm">Создать первый</Button>
                    </Link>
                  </td>
                </tr>
              ) : (
                wallets.map((w) => {
                  const displayName = formatWalletDisplayName(w);
                  const href = `/wallets/${encodeURIComponent(w.name ?? "")}`;
                  // Row click → navigation. Cmd/Ctrl/middle-click still
                  // works because we delegate to router.push only on
                  // plain left-click; modified clicks fall through and
                  // the inner <Link> handles them via the browser's
                  // default new-tab behaviour.
                  const handleRowClick: React.MouseEventHandler<HTMLTableRowElement> = (e) => {
                    if (e.defaultPrevented) return;
                    if (e.button !== 0) return;
                    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
                    router.push(href);
                  };
                  return (
                    <tr
                      key={w.id ?? w.my_unid}
                      onClick={handleRowClick}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          router.push(href);
                        }
                      }}
                      tabIndex={0}
                      role="link"
                      aria-label={`Открыть кошелёк ${displayName}`}
                      className="border-b border-border last:border-b-0 hover:bg-muted/40 cursor-pointer focus:bg-muted/40 focus:outline-none"
                    >
                      <td className="px-5 py-3.5">
                        <Link
                          href={href}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-2 text-foreground hover:text-primary"
                          title={w.my_unid ?? w.name ?? undefined}
                        >
                          {w.is_favorite && (
                            <Icon icon="solar:star-bold" className="text-warning text-[14px] shrink-0" />
                          )}
                          <span className="font-medium truncate max-w-xs">{displayName}</span>
                        </Link>
                      </td>
                      <td className="px-3 py-3.5">
                        <Badge variant="outline">{networkName(w.network)}</Badge>
                      </td>
                      <td className="px-3 py-3.5">
                        <Mono size="xs" className="text-muted-foreground">
                          {w.wallet_type === 1 ? "MULTI-SIG" : "STANDARD"}
                        </Mono>
                      </td>
                      <td className="px-3 py-3.5">
                        <Mono truncate>{w.addr ?? "—"}</Mono>
                      </td>
                      <td className="px-3 py-3.5 text-muted-foreground">
                        <Mono size="xs" truncate startChars={20} endChars={0}>{w.token_short_names ?? "—"}</Mono>
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <Mono truncate>{w.my_unid ?? "—"}</Mono>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <th className={`px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal ${className}`}>
      {children}
    </th>
  );
}

function pluralize(n: number, forms: [string, string, string]): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 19) return forms[2];
  if (mod10 === 1) return forms[0];
  if (mod10 >= 2 && mod10 <= 4) return forms[1];
  return forms[2];
}
