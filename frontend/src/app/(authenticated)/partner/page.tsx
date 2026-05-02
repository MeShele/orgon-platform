"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout, tableStyles } from "@/lib/page-layout";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { HelpTooltip } from "@/components/common/HelpTooltip";

type Tab = "overview" | "wallets" | "transactions" | "addresses" | "scheduled" | "info";

export default function PartnerPage() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(false);

  // Overview
  const [volume, setVolume] = useState<any>(null);
  const [distribution, setDistribution] = useState<any>(null);
  const [fees, setFees] = useState<any>(null);

  // Wallets
  const [wallets, setWallets] = useState<any[]>([]);
  const [selectedWallet, setSelectedWallet] = useState<any>(null);

  // Transactions
  const [transactions, setTransactions] = useState<any[]>([]);
  const [selectedTx, setSelectedTx] = useState<any>(null);

  // Addresses
  const [addresses, setAddresses] = useState<any[]>([]);

  // Scheduled
  const [scheduled, setScheduled] = useState<any[]>([]);

  // Info
  const [networks, setNetworks] = useState<any[]>([]);
  const [tokens, setTokens] = useState<any[]>([]);
  const [pendingSigs, setPendingSigs] = useState<any[]>([]);

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: "overview", label: "Обзор", icon: "solar:chart-linear" },
    { id: "wallets", label: "Кошельки", icon: "solar:wallet-linear" },
    { id: "transactions", label: "Транзакции", icon: "solar:transfer-horizontal-linear" },
    { id: "addresses", label: "Адреса", icon: "solar:map-point-linear" },
    { id: "scheduled", label: "Запланированные", icon: "solar:calendar-linear" },
    { id: "info", label: "Информация", icon: "solar:info-circle-linear" },
  ];

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        switch (activeTab) {
          case "overview":
            const [v, d, f] = await Promise.all([
              api.getPartnerVolume().catch(() => null),
              api.getPartnerDistribution().catch(() => null),
              api.getPartnerFees().catch(() => null),
            ]);
            setVolume(v); setDistribution(d); setFees(f);
            break;
          case "wallets":
            const w = await api.getPartnerWallets().catch(() => []);
            setWallets(Array.isArray(w) ? w : w.wallets || []);
            break;
          case "transactions":
            const t = await api.getPartnerTransactions().catch(() => []);
            setTransactions(Array.isArray(t) ? t : t.transactions || []);
            break;
          case "addresses":
            const a = await api.getPartnerAddresses().catch(() => []);
            setAddresses(Array.isArray(a) ? a : a.addresses || []);
            break;
          case "scheduled":
            const s = await api.getPartnerScheduledTransactions().catch(() => []);
            setScheduled(Array.isArray(s) ? s : s.transactions || []);
            break;
          case "info":
            const [n, tk, p] = await Promise.all([
              api.getPartnerNetworks().catch(() => []),
              api.getPartnerTokensInfo().catch(() => []),
              api.getPartnerPendingSignatures().catch(() => []),
            ]);
            setNetworks(Array.isArray(n) ? n : n.networks || []);
            setTokens(Array.isArray(tk) ? tk : tk.tokens || []);
            setPendingSigs(Array.isArray(p) ? p : p.signatures || []);
            break;
        }
      } catch {} finally {
        setLoading(false);
      }
    };
    load();
  }, [activeTab]);

  const handleSign = async (unid: string) => {
    try {
      await api.signPartnerTransaction(unid);
      const t = await api.getPartnerTransactions();
      setTransactions(Array.isArray(t) ? t : t.transactions || []);
    } catch (e: any) { alert(e.message || "Ошибка"); }
  };

  const handleReject = async (unid: string) => {
    try {
      await api.rejectPartnerTransaction(unid);
      const t = await api.getPartnerTransactions();
      setTransactions(Array.isArray(t) ? t : t.transactions || []);
    } catch (e: any) { alert(e.message || "Ошибка"); }
  };

  const handleCancelScheduled = async (txId: string) => {
    if (!confirm("Отменить запланированную транзакцию?")) return;
    try {
      await api.cancelPartnerScheduledTransaction(txId);
      const s = await api.getPartnerScheduledTransactions();
      setScheduled(Array.isArray(s) ? s : s.transactions || []);
    } catch (e: any) { alert(e.message || "Ошибка"); }
  };

  const handleExport = async () => {
    try {
      const data = await api.exportPartnerAnalytics();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "partner-analytics.json"; a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) { alert(e.message || "Ошибка экспорта"); }
  };

  return (
    <>
      <Header title="Партнёр API" />
      <div className={pageLayout.container}>
        <div className="flex items-center gap-2">
          <HelpTooltip
            text="B2B Partner API — отдельный канал для интеграции внешних платформ (биржи, exchanger'ы)."
            tips={[
              "Аутентификация через HMAC-подпись (X-Signature заголовок), отдельная от user-сессии.",
              "Replay-guard через X-Idempotency-Key (ORGON_PARTNER_REPLAY_OFF=0 в prod).",
              "Webhook обратной связи: партнёр получает callback'и о статусах транзакций.",
              "Все Partner API requests пишутся в audit_log_b2b — отдельная таблица от внутренней audit_log.",
            ]}
          />
          <span className="text-xs text-muted-foreground">Что это и зачем нужно</span>
        </div>
        {/* Tabs */}
        <div className="flex gap-1 overflow-x-auto rounded-lg bg-muted p-1 dark:bg-muted/50">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-white text-foreground shadow-sm dark:bg-muted"
                  : "text-muted-foreground hover:text-foreground dark:text-muted-foreground dark:hover:text-primary-foreground"
              }`}
            >
              <Icon icon={tab.icon} className="text-base" />
              {tab.label}
            </button>
          ))}
        </div>

        {loading && <div className={pageLayout.loading}><LoadingSpinner /></div>}

        {/* Overview */}
        {!loading && activeTab === "overview" && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <Button variant="secondary" onClick={handleExport}>
                <Icon icon="solar:download-linear" className="mr-1" />
                Экспорт аналитики
              </Button>
            </div>
            <div className={pageLayout.grid.cols3}>
              <Card>
                <div className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-primary/10 p-2.5">
                      <Icon icon="solar:chart-bold" className="text-xl text-primary" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-foreground">{volume?.total_volume ?? "—"}</p>
                      <p className="text-xs text-muted-foreground">Объём транзакций</p>
                    </div>
                  </div>
                </div>
              </Card>
              <Card>
                <div className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-success/10 p-2.5">
                      <Icon icon="solar:pie-chart-bold" className="text-xl text-success" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-foreground">{distribution?.total_wallets ?? "—"}</p>
                      <p className="text-xs text-muted-foreground">Распределение</p>
                    </div>
                  </div>
                </div>
              </Card>
              <Card>
                <div className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-warning/10 p-2.5">
                      <Icon icon="solar:tag-price-bold" className="text-xl text-warning" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-foreground">{fees?.total_fees ?? "—"}</p>
                      <p className="text-xs text-muted-foreground">Комиссии</p>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
            {volume && volume.data && volume.data.length > 0 && (
              <Card>
                <div className="p-4">
                  <h4 className="mb-3 font-semibold text-foreground">Детали объёма</h4>
                  <div className="space-y-2">
                    {volume.data.map((item: any, i: number) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                        <span className="text-sm text-muted-foreground">{item.network_name || `Network ${item.network_id}`}</span>
                        <div className="text-right">
                          <span className="text-sm font-medium text-foreground">{item.tx_count} tx</span>
                          <span className="text-xs text-muted-foreground ml-2">{Number(item.total_value || 0).toFixed(4)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 pt-3 border-t border-border flex justify-between text-sm">
                    <span className="text-muted-foreground">Всего транзакций:</span>
                    <span className="font-medium text-foreground">{volume.total_transactions}</span>
                  </div>
                </div>
              </Card>
            )}
          </div>
        )}

        {/* Wallets */}
        {!loading && activeTab === "wallets" && (
          wallets.length === 0 ? (
            <div className={pageLayout.empty.wrapper}>
              <Icon icon="solar:wallet-linear" className={pageLayout.empty.icon} />
              <p className={pageLayout.empty.title}>Нет партнёрских кошельков</p>
            </div>
          ) : (
            <>
              <div className={`hidden md:block ${tableStyles.wrapper}`}>
                <table className={tableStyles.table}>
                  <thead className={tableStyles.thead}>
                    <tr>
                      <th className={tableStyles.th}>Имя</th>
                      <th className={tableStyles.th}>Адрес</th>
                      <th className={tableStyles.th}>Сеть</th>
                      <th className={tableStyles.th}>Баланс</th>
                    </tr>
                  </thead>
                  <tbody className={tableStyles.tbody}>
                    {wallets.map((w: any, i: number) => (
                      <tr key={i} className="cursor-pointer hover:bg-muted dark:hover:bg-muted/50" onClick={() => setSelectedWallet(w)}>
                        <td className={tableStyles.td}>{w.name || w.wallet_name || "—"}</td>
                        <td className={tableStyles.td}><code className="text-xs">{w.address || "—"}</code></td>
                        <td className={tableStyles.td}>{w.network || "—"}</td>
                        <td className={tableStyles.td}>{w.balance ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="md:hidden space-y-3">
                {wallets.map((w: any, i: number) => (
                  <Card key={i}>
                    <div className="p-4 space-y-1" onClick={() => setSelectedWallet(w)}>
                      <p className="font-medium text-foreground">{w.name || w.wallet_name}</p>
                      <p className="text-xs text-muted-foreground font-mono truncate">{w.address}</p>
                      <p className="text-sm text-muted-foreground">{w.network} · {w.balance ?? "—"}</p>
                    </div>
                  </Card>
                ))}
              </div>
            </>
          )
        )}

        {/* Transactions */}
        {!loading && activeTab === "transactions" && (
          transactions.length === 0 ? (
            <div className={pageLayout.empty.wrapper}>
              <Icon icon="solar:transfer-horizontal-linear" className={pageLayout.empty.icon} />
              <p className={pageLayout.empty.title}>Нет транзакций</p>
            </div>
          ) : (
            <>
              <div className={`hidden md:block ${tableStyles.wrapper}`}>
                <table className={tableStyles.table}>
                  <thead className={tableStyles.thead}>
                    <tr>
                      <th className={tableStyles.th}>UNID</th>
                      <th className={tableStyles.th}>Кому</th>
                      <th className={tableStyles.th}>Сумма</th>
                      <th className={tableStyles.th}>Статус</th>
                      <th className={tableStyles.th}>Действия</th>
                    </tr>
                  </thead>
                  <tbody className={tableStyles.tbody}>
                    {transactions.map((tx: any, i: number) => (
                      <tr key={i}>
                        <td className={tableStyles.td}><code className="text-xs">{(tx.unid || tx.id || "").slice(0, 12)}...</code></td>
                        <td className={tableStyles.td}><code className="text-xs">{(tx.to_address || tx.to || "").slice(0, 16)}...</code></td>
                        <td className={tableStyles.td}>{tx.value || tx.amount} {tx.token}</td>
                        <td className={tableStyles.td}><Badge variant={tx.status === "completed" ? "green" : tx.status === "failed" ? "red" : "yellow"}>{tx.status}</Badge></td>
                        <td className={tableStyles.td}>
                          <div className="flex gap-2">
                            {tx.status === "pending" && (
                              <>
                                <Button size="sm" onClick={() => handleSign(tx.unid || tx.id)}>Подписать</Button>
                                <Button size="sm" variant="danger" onClick={() => handleReject(tx.unid || tx.id)}>Отклонить</Button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="md:hidden space-y-3">
                {transactions.map((tx: any, i: number) => (
                  <Card key={i}>
                    <div className="p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <code className="text-xs text-muted-foreground">{(tx.unid || tx.id || "").slice(0, 12)}...</code>
                        <Badge variant={tx.status === "completed" ? "green" : tx.status === "failed" ? "red" : "yellow"}>{tx.status}</Badge>
                      </div>
                      <p className="text-sm text-foreground">{tx.value || tx.amount} {tx.token}</p>
                      <p className="text-xs text-muted-foreground truncate">→ {tx.to_address || tx.to}</p>
                      {tx.status === "pending" && (
                        <div className="flex gap-2 pt-1">
                          <Button size="sm" onClick={() => handleSign(tx.unid || tx.id)}>Подписать</Button>
                          <Button size="sm" variant="danger" onClick={() => handleReject(tx.unid || tx.id)}>Отклонить</Button>
                        </div>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            </>
          )
        )}

        {/* Addresses */}
        {!loading && activeTab === "addresses" && (
          addresses.length === 0 ? (
            <div className={pageLayout.empty.wrapper}>
              <Icon icon="solar:map-point-linear" className={pageLayout.empty.icon} />
              <p className={pageLayout.empty.title}>Нет адресов</p>
            </div>
          ) : (
            <>
              <div className={`hidden md:block ${tableStyles.wrapper}`}>
                <table className={tableStyles.table}>
                  <thead className={tableStyles.thead}>
                    <tr>
                      <th className={tableStyles.th}>ID</th>
                      <th className={tableStyles.th}>Адрес</th>
                      <th className={tableStyles.th}>Сеть</th>
                      <th className={tableStyles.th}>Метка</th>
                    </tr>
                  </thead>
                  <tbody className={tableStyles.tbody}>
                    {addresses.map((a: any, i: number) => (
                      <tr key={i}>
                        <td className={tableStyles.td}>{a.id}</td>
                        <td className={tableStyles.td}><code className="text-xs">{a.address}</code></td>
                        <td className={tableStyles.td}>{a.network || "—"}</td>
                        <td className={tableStyles.td}>{a.label || a.name || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="md:hidden space-y-3">
                {addresses.map((a: any, i: number) => (
                  <Card key={i}>
                    <div className="p-4 space-y-1">
                      <p className="font-medium text-foreground">{a.label || a.name || `Адрес #${a.id}`}</p>
                      <p className="text-xs text-muted-foreground font-mono truncate">{a.address}</p>
                      <p className="text-xs text-muted-foreground">{a.network}</p>
                    </div>
                  </Card>
                ))}
              </div>
            </>
          )
        )}

        {/* Scheduled */}
        {!loading && activeTab === "scheduled" && (
          scheduled.length === 0 ? (
            <div className={pageLayout.empty.wrapper}>
              <Icon icon="solar:calendar-linear" className={pageLayout.empty.icon} />
              <p className={pageLayout.empty.title}>Нет запланированных транзакций</p>
            </div>
          ) : (
            <>
              <div className={`hidden md:block ${tableStyles.wrapper}`}>
                <table className={tableStyles.table}>
                  <thead className={tableStyles.thead}>
                    <tr>
                      <th className={tableStyles.th}>ID</th>
                      <th className={tableStyles.th}>Кому</th>
                      <th className={tableStyles.th}>Сумма</th>
                      <th className={tableStyles.th}>Дата</th>
                      <th className={tableStyles.th}>Действия</th>
                    </tr>
                  </thead>
                  <tbody className={tableStyles.tbody}>
                    {scheduled.map((s: any, i: number) => (
                      <tr key={i}>
                        <td className={tableStyles.td}>{s.id || s.tx_id}</td>
                        <td className={tableStyles.td}><code className="text-xs">{(s.to_address || "").slice(0, 16)}...</code></td>
                        <td className={tableStyles.td}>{s.value || s.amount} {s.token}</td>
                        <td className={tableStyles.tdMuted}>{s.scheduled_at ? new Date(s.scheduled_at).toLocaleString() : "—"}</td>
                        <td className={tableStyles.td}>
                          <Button size="sm" variant="danger" onClick={() => handleCancelScheduled(s.id || s.tx_id)}>Отменить</Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="md:hidden space-y-3">
                {scheduled.map((s: any, i: number) => (
                  <Card key={i}>
                    <div className="p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-foreground">{s.value || s.amount} {s.token}</span>
                        <Button size="sm" variant="danger" onClick={() => handleCancelScheduled(s.id || s.tx_id)}>Отменить</Button>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">→ {s.to_address}</p>
                      <p className="text-xs text-muted-foreground">{s.scheduled_at ? new Date(s.scheduled_at).toLocaleString() : ""}</p>
                    </div>
                  </Card>
                ))}
              </div>
            </>
          )
        )}

        {/* Info */}
        {!loading && activeTab === "info" && (
          <div className="space-y-4">
            <Card>
              <div className="p-4">
                <h4 className="mb-3 font-semibold text-foreground">
                  <Icon icon="solar:global-linear" className="mr-2 inline" />
                  Доступные сети ({networks.length})
                </h4>
                {networks.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Нет данных</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {networks.map((n: any, i: number) => (
                      <Badge key={i} variant="blue">{n.name || n.network || JSON.stringify(n)}</Badge>
                    ))}
                  </div>
                )}
              </div>
            </Card>
            <Card>
              <div className="p-4">
                <h4 className="mb-3 font-semibold text-foreground">
                  <Icon icon="solar:coin-linear" className="mr-2 inline" />
                  Доступные токены ({tokens.length})
                </h4>
                {tokens.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Нет данных</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {tokens.map((t: any, i: number) => (
                      <Badge key={i} variant="green">{t.symbol || t.name || JSON.stringify(t)}</Badge>
                    ))}
                  </div>
                )}
              </div>
            </Card>
            <Card>
              <div className="p-4">
                <h4 className="mb-3 font-semibold text-foreground">
                  <Icon icon="solar:pen-linear" className="mr-2 inline" />
                  Ожидающие подписи ({pendingSigs.length})
                </h4>
                {pendingSigs.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Нет ожидающих подписей</p>
                ) : (
                  <div className="space-y-2">
                    {pendingSigs.map((s: any, i: number) => (
                      <div key={i} className="rounded border border-border p-3 text-sm dark:border-border">
                        <div className="text-xs">
                          <span className="font-medium">{s.tx_unid || s.id}</span>
                          <span className="text-muted-foreground ml-2">{s.status || 'pending'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          </div>
        )}
      </div>
    </>
  );
}
