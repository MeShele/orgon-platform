"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout, tableStyles } from "@/lib/page-layout";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";

type Tab = "onramp" | "offramp" | "accounts" | "history";

interface BankAccount {
  id: number;
  iban: string;
  bank_name: string;
  holder_name: string;
  currency: string;
  created_at: string;
}

interface FiatTransaction {
  id: string;
  type: string;
  amount: string;
  currency: string;
  crypto_amount?: string;
  crypto_currency?: string;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
}

const statusColors: Record<string, string> = {
  pending: "yellow",
  processing: "blue",
  completed: "green",
  failed: "red",
};

const statusLabels: Record<string, string> = {
  pending: "Ожидает",
  processing: "Обработка",
  completed: "Завершено",
  failed: "Ошибка",
};

export default function FiatPage() {
  const [activeTab, setActiveTab] = useState<Tab>("onramp");
  const [loading, setLoading] = useState(false);

  // Onramp
  const [onrampAmount, setOnrampAmount] = useState("");
  const [onrampFiat, setOnrampFiat] = useState("USD");
  const [onrampCrypto, setOnrampCrypto] = useState("USDT");
  const [rate, setRate] = useState<number | null>(null);
  const [rateLoading, setRateLoading] = useState(false);

  // Offramp
  const [offrampAmount, setOfframpAmount] = useState("");
  const [offrampFiat, setOfframpFiat] = useState("USD");
  const [offrampCrypto, setOfframpCrypto] = useState("USDT");
  const [offrampAccount, setOfframpAccount] = useState("");

  // Bank accounts
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [newIban, setNewIban] = useState("");
  const [newBankName, setNewBankName] = useState("");
  const [newHolderName, setNewHolderName] = useState("");

  // History
  const [transactions, setTransactions] = useState<FiatTransaction[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: "onramp", label: "Покупка крипто", icon: "solar:card-recive-linear" },
    { id: "offramp", label: "Продажа крипто", icon: "solar:card-send-linear" },
    { id: "accounts", label: "Банковские счета", icon: "solar:bank-linear" },
    { id: "history", label: "История", icon: "solar:history-linear" },
  ];

  const fiats = ["USD", "EUR", "KGS"];
  const cryptos = ["USDT", "BTC", "ETH", "USDC"];

  // Load rate
  useEffect(() => {
    if (activeTab === "onramp" && onrampCrypto && onrampFiat) {
      setRateLoading(true);
      api.getFiatRates(onrampCrypto, onrampFiat)
        .then((d: any) => setRate(d.rate ?? d.price ?? null))
        .catch(() => setRate(null))
        .finally(() => setRateLoading(false));
    }
  }, [activeTab, onrampCrypto, onrampFiat]);

  // Load accounts
  useEffect(() => {
    if (activeTab === "accounts" || activeTab === "offramp") {
      api.getBankAccounts()
        .then((d: any) => setAccounts(Array.isArray(d) ? d : d.accounts || []))
        .catch(() => {});
    }
  }, [activeTab]);

  // Load history
  useEffect(() => {
    if (activeTab === "history") {
      setHistoryLoading(true);
      api.getFiatTransactions()
        .then((d: any) => setTransactions(Array.isArray(d) ? d : d.transactions || []))
        .catch(() => {})
        .finally(() => setHistoryLoading(false));
    }
  }, [activeTab]);

  const handleOnramp = async () => {
    setLoading(true);
    try {
      await api.createOnramp({ amount: onrampAmount, fiat_currency: onrampFiat, crypto_currency: onrampCrypto });
      alert("Заявка на покупку создана");
      setOnrampAmount("");
    } catch (e: any) {
      alert(e.message || "Ошибка");
    } finally {
      setLoading(false);
    }
  };

  const handleOfframp = async () => {
    setLoading(true);
    try {
      await api.createOfframp({ amount: offrampAmount, fiat_currency: offrampFiat, crypto_currency: offrampCrypto, bank_account_id: offrampAccount });
      alert("Заявка на продажу создана");
      setOfframpAmount("");
    } catch (e: any) {
      alert(e.message || "Ошибка");
    } finally {
      setLoading(false);
    }
  };

  const handleAddAccount = async () => {
    setLoading(true);
    try {
      await api.addBankAccount({ iban: newIban, bank_name: newBankName, holder_name: newHolderName });
      setNewIban(""); setNewBankName(""); setNewHolderName("");
      const d = await api.getBankAccounts();
      setAccounts(Array.isArray(d) ? d : d.accounts || []);
    } catch (e: any) {
      alert(e.message || "Ошибка");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Header title="Фиат операции" />
      <div className={pageLayout.container}>
        {/* Tabs */}
        <div className="flex gap-1 overflow-x-auto rounded-lg bg-slate-100 p-1 dark:bg-slate-800/50">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              }`}
            >
              <Icon icon={tab.icon} className="text-base" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Onramp */}
        {activeTab === "onramp" && (
          <Card>
            <div className="p-6 space-y-4">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Покупка криптовалюты за фиат</h3>
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">Сумма</label>
                  <Input value={onrampAmount} onChange={(e) => setOnrampAmount(e.target.value)} placeholder="1000" type="number" />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">Валюта</label>
                  <select value={onrampFiat} onChange={(e) => setOnrampFiat(e.target.value)} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white">
                    {fiats.map(f => <option key={f} value={f}>{f}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">Целевая крипто</label>
                  <select value={onrampCrypto} onChange={(e) => setOnrampCrypto(e.target.value)} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white">
                    {cryptos.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              {rate !== null && (
                <div className="rounded-lg bg-blue-50 p-3 text-sm text-blue-700 dark:bg-blue-900/20 dark:text-blue-400">
                  <Icon icon="solar:info-circle-linear" className="mr-1 inline" />
                  Курс: 1 {onrampCrypto} = {rate} {onrampFiat}
                  {onrampAmount && ` → Вы получите ~${(parseFloat(onrampAmount) / rate).toFixed(6)} ${onrampCrypto}`}
                </div>
              )}
              {rateLoading && <p className="text-sm text-slate-500">Загрузка курса...</p>}
              <Button onClick={handleOnramp} disabled={loading || !onrampAmount}>
                {loading ? "Создание..." : "Создать заявку на покупку"}
              </Button>
            </div>
          </Card>
        )}

        {/* Offramp */}
        {activeTab === "offramp" && (
          <Card>
            <div className="p-6 space-y-4">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Продажа криптовалюты за фиат</h3>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div>
                  <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">Сумма крипто</label>
                  <Input value={offrampAmount} onChange={(e) => setOfframpAmount(e.target.value)} placeholder="0.5" type="number" />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">Криптовалюта</label>
                  <select value={offrampCrypto} onChange={(e) => setOfframpCrypto(e.target.value)} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white">
                    {cryptos.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">Целевая валюта</label>
                  <select value={offrampFiat} onChange={(e) => setOfframpFiat(e.target.value)} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white">
                    {fiats.map(f => <option key={f} value={f}>{f}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">Банковский счёт</label>
                  <select value={offrampAccount} onChange={(e) => setOfframpAccount(e.target.value)} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-white">
                    <option value="">Выберите счёт</option>
                    {accounts.map(a => <option key={a.id} value={a.id}>{a.bank_name} — {a.iban}</option>)}
                  </select>
                </div>
              </div>
              <Button onClick={handleOfframp} disabled={loading || !offrampAmount || !offrampAccount}>
                {loading ? "Создание..." : "Создать заявку на продажу"}
              </Button>
            </div>
          </Card>
        )}

        {/* Bank accounts */}
        {activeTab === "accounts" && (
          <div className="space-y-4">
            <Card>
              <div className="p-6 space-y-4">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Добавить банковский счёт</h3>
                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">IBAN</label>
                    <Input value={newIban} onChange={(e) => setNewIban(e.target.value)} placeholder="KG00XXXX..." />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">Название банка</label>
                    <Input value={newBankName} onChange={(e) => setNewBankName(e.target.value)} placeholder="Optima Bank" />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">Имя владельца</label>
                    <Input value={newHolderName} onChange={(e) => setNewHolderName(e.target.value)} placeholder="Иван Иванов" />
                  </div>
                </div>
                <Button onClick={handleAddAccount} disabled={loading || !newIban || !newBankName || !newHolderName}>
                  {loading ? "Добавление..." : "Добавить счёт"}
                </Button>
              </div>
            </Card>

            {/* List */}
            {accounts.length === 0 ? (
              <div className={pageLayout.empty.wrapper}>
                <Icon icon="solar:bank-linear" className={pageLayout.empty.icon} />
                <p className={pageLayout.empty.title}>Нет банковских счетов</p>
                <p className={pageLayout.empty.description}>Добавьте ваш первый банковский счёт</p>
              </div>
            ) : (
              <>
                {/* Desktop table */}
                <div className={`hidden md:block ${tableStyles.wrapper}`}>
                  <table className={tableStyles.table}>
                    <thead className={tableStyles.thead}>
                      <tr>
                        <th className={tableStyles.th}>IBAN</th>
                        <th className={tableStyles.th}>Банк</th>
                        <th className={tableStyles.th}>Владелец</th>
                        <th className={tableStyles.th}>Дата</th>
                      </tr>
                    </thead>
                    <tbody className={tableStyles.tbody}>
                      {accounts.map((a) => (
                        <tr key={a.id}>
                          <td className={tableStyles.td}><code className="text-xs">{a.iban}</code></td>
                          <td className={tableStyles.td}>{a.bank_name}</td>
                          <td className={tableStyles.td}>{a.holder_name}</td>
                          <td className={tableStyles.tdMuted}>{new Date(a.created_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {/* Mobile cards */}
                <div className="md:hidden space-y-3">
                  {accounts.map((a) => (
                    <Card key={a.id}>
                      <div className="p-4 space-y-2">
                        <p className="font-medium text-slate-900 dark:text-white">{a.bank_name}</p>
                        <p className="text-xs text-slate-500 font-mono">{a.iban}</p>
                        <p className="text-sm text-slate-600 dark:text-slate-400">{a.holder_name}</p>
                      </div>
                    </Card>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {/* History */}
        {activeTab === "history" && (
          <>
            {historyLoading ? (
              <div className={pageLayout.loading}><LoadingSpinner /></div>
            ) : transactions.length === 0 ? (
              <div className={pageLayout.empty.wrapper}>
                <Icon icon="solar:history-linear" className={pageLayout.empty.icon} />
                <p className={pageLayout.empty.title}>Нет фиат транзакций</p>
              </div>
            ) : (
              <>
                {/* Desktop */}
                <div className={`hidden md:block ${tableStyles.wrapper}`}>
                  <table className={tableStyles.table}>
                    <thead className={tableStyles.thead}>
                      <tr>
                        <th className={tableStyles.th}>Тип</th>
                        <th className={tableStyles.th}>Сумма</th>
                        <th className={tableStyles.th}>Крипто</th>
                        <th className={tableStyles.th}>Статус</th>
                        <th className={tableStyles.th}>Дата</th>
                      </tr>
                    </thead>
                    <tbody className={tableStyles.tbody}>
                      {transactions.map((tx) => (
                        <tr key={tx.id}>
                          <td className={tableStyles.td}>{tx.type === "onramp" ? "Покупка" : "Продажа"}</td>
                          <td className={tableStyles.td}>{tx.amount} {tx.currency}</td>
                          <td className={tableStyles.td}>{tx.crypto_amount ? `${tx.crypto_amount} ${tx.crypto_currency}` : "—"}</td>
                          <td className={tableStyles.td}><Badge variant={statusColors[tx.status] as any}>{statusLabels[tx.status]}</Badge></td>
                          <td className={tableStyles.tdMuted}>{new Date(tx.created_at).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {/* Mobile */}
                <div className="md:hidden space-y-3">
                  {transactions.map((tx) => (
                    <Card key={tx.id}>
                      <div className="p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-slate-900 dark:text-white">{tx.type === "onramp" ? "Покупка" : "Продажа"}</span>
                          <Badge variant={statusColors[tx.status] as any}>{statusLabels[tx.status]}</Badge>
                        </div>
                        <p className="text-sm text-slate-600 dark:text-slate-400">{tx.amount} {tx.currency}</p>
                        {tx.crypto_amount && <p className="text-sm text-slate-500">{tx.crypto_amount} {tx.crypto_currency}</p>}
                        <p className="text-xs text-slate-400">{new Date(tx.created_at).toLocaleString()}</p>
                      </div>
                    </Card>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </>
  );
}
