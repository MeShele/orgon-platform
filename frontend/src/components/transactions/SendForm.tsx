"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardHeader } from "@/components/common/Card";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";
import useSWR from "swr";

const inputClass =
  "w-full rounded-lg border border-border bg-muted px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground dark:border-border dark:bg-card/50 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary/30 dark:focus:ring-slate-600 transition-colors";

const selectClass =
  "w-full rounded-lg border border-border bg-muted px-3 py-2 text-xs text-foreground dark:border-border dark:bg-card/50 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary/30 dark:focus:ring-slate-600 transition-colors";

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  balance?: string;
}

interface Wallet {
  name: string;
  info?: string;
  network?: number;
  network_name?: string;
  addr?: string;
}

interface Token {
  token_short_name?: string;
  short_name?: string;
  name?: string;
  balance?: string;
  wallet_name?: string;
}

export function SendForm() {
  const router = useRouter();
  const [selectedWallet, setSelectedWallet] = useState("");
  const [selectedToken, setSelectedToken] = useState("");
  const [toAddress, setToAddress] = useState("");
  const [value, setValue] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState("");
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  
  // Fee estimation
  const [feeEstimate, setFeeEstimate] = useState<{ fee: string; total: string } | null>(null);
  const [estimatingFee, setEstimatingFee] = useState(false);
  
  // Address validation
  const [addressValid, setAddressValid] = useState<boolean | null>(null);
  const [addressValidating, setAddressValidating] = useState(false);
  const [addressError, setAddressError] = useState("");

  const { data: wallets } = useSWR("/api/wallets", api.getWallets);
  const { data: allTokens } = useSWR("/api/tokens", api.getTokens);

  const walletList: Wallet[] = useMemo(() => {
    if (!wallets) return [];
    return Array.isArray(wallets) ? wallets : [];
  }, [wallets]);

  const selectedWalletObj = useMemo(
    () => walletList.find((w) => w.name === selectedWallet),
    [walletList, selectedWallet]
  );

  // Tokens for selected wallet
  const tokenList: Token[] = useMemo(() => {
    if (!allTokens) return [];
    const tokens = Array.isArray(allTokens) ? allTokens : [];
    if (!selectedWallet) return tokens;
    return tokens.filter((t: Token) => t.wallet_name === selectedWallet);
  }, [allTokens, selectedWallet]);

  // Build the token string: network:::TOKEN###wallet_name
  const tokenString = useMemo(() => {
    if (!selectedWalletObj || !selectedToken) return "";
    const network = selectedWalletObj.network || "";
    return `${network}:::${selectedToken}###${selectedWalletObj.name}`;
  }, [selectedWalletObj, selectedToken]);

  // Address validation on blur
  const handleAddressBlur = async () => {
    if (!toAddress || toAddress.length < 10) {
      setAddressValid(null);
      setAddressError("");
      return;
    }
    setAddressValidating(true);
    setAddressError("");
    try {
      const res = await api.post("/api/addresses/validate", { address: toAddress, network: selectedWalletObj?.network });
      setAddressValid(res.valid !== false);
      if (!res.valid) setAddressError(res.error || "Невалидный адрес");
    } catch {
      // If endpoint doesn't exist, don't block
      setAddressValid(null);
    } finally {
      setAddressValidating(false);
    }
  };

  // Fee estimation when all fields are filled
  useEffect(() => {
    if (!tokenString || !toAddress || !value || !parseFloat(value)) {
      setFeeEstimate(null);
      return;
    }
    const timer = setTimeout(async () => {
      setEstimatingFee(true);
      try {
        const res = await api.post("/api/transactions/estimate-fee", {
          token: tokenString,
          to_address: toAddress,
          value,
        });
        setFeeEstimate({ fee: res.fee || res.estimated_fee || "0", total: res.total || "" });
      } catch {
        setFeeEstimate(null);
      } finally {
        setEstimatingFee(false);
      }
    }, 800);
    return () => clearTimeout(timer);
  }, [tokenString, toAddress, value]);

  const handleValidate = async () => {
    setValidating(true);
    setError("");
    setValidation(null);
    try {
      const result = await api.validateTransaction({
        token: tokenString,
        to_address: toAddress,
        value,
        info,
      });
      setValidation(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Validation failed");
    } finally {
      setValidating(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await api.sendTransaction({
        token: tokenString,
        to_address: toAddress,
        value,
        info,
      });
      router.push(`/transactions/${result.tx_unid}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send transaction");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="max-w-2xl">
      <CardHeader title="Отправить транзакцию" subtitle="Перевод токенов на адрес" />
      <form onSubmit={handleSubmit} className="space-y-4 p-4">
        {/* Wallet Select */}
        <div>
          <label className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
            Кошелёк
            <HelpTooltip text={helpContent.sendForm.token.text} diagram={helpContent.sendForm.token.diagram} />
          </label>
          <select
            value={selectedWallet}
            onChange={(e) => {
              setSelectedWallet(e.target.value);
              setSelectedToken("");
            }}
            className={selectClass}
            required
          >
            <option value="">Выберите кошелёк…</option>
            {walletList.map((w) => (
              <option key={w.name} value={w.name}>
                {w.info || w.name} — сеть {w.network_name || w.network}
              </option>
            ))}
          </select>
        </div>

        {/* Token Select */}
        <div>
          <label className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
            Токен
          </label>
          {tokenList.length > 0 ? (
            <select
              value={selectedToken}
              onChange={(e) => setSelectedToken(e.target.value)}
              className={selectClass}
              required
            >
              <option value="">Выберите токен…</option>
              {tokenList.map((t, i) => {
                const shortName = t.token_short_name || t.short_name || t.name || "—";
                return (
                  <option key={`${shortName}-${i}`} value={shortName}>
                    {shortName} {t.balance ? `(баланс: ${t.balance})` : ""}
                  </option>
                );
              })}
            </select>
          ) : !selectedWallet ? (
            <select className={selectClass} disabled>
              <option>Сначала выберите кошелёк</option>
            </select>
          ) : (
            <EmptyTokensCallout
              networkId={selectedWalletObj?.network}
              walletAddr={selectedWalletObj?.addr}
            />
          )}
          {tokenString && (
            <p className="mt-1 text-[10px] text-muted-foreground font-mono">{tokenString}</p>
          )}
        </div>

        <div>
          <label className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
            Адрес получателя
            <HelpTooltip text={helpContent.sendForm.toAddress.text} />
          </label>
          <div className="relative">
            <input suppressHydrationWarning
              type="text"
              value={toAddress}
              onChange={(e) => { setToAddress(e.target.value); setAddressValid(null); setAddressError(""); }}
              onBlur={handleAddressBlur}
              className={`${inputClass} font-mono pr-8`}
              placeholder="Адрес получателя"
              required
            />
            {addressValidating && (
              <Icon icon="solar:refresh-linear" className="absolute right-2 top-2.5 text-sm text-muted-foreground animate-spin" />
            )}
            {!addressValidating && addressValid === true && (
              <Icon icon="solar:check-circle-bold" className="absolute right-2 top-2.5 text-sm text-green-500" />
            )}
            {!addressValidating && addressValid === false && (
              <Icon icon="solar:close-circle-bold" className="absolute right-2 top-2.5 text-sm text-destructive" />
            )}
          </div>
          {addressError && (
            <p className="mt-1 text-[10px] text-destructive">{addressError}</p>
          )}
        </div>

        <div>
          <label className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
            Сумма
            <HelpTooltip text={helpContent.sendForm.amount.text} />
          </label>
          <input suppressHydrationWarning
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className={inputClass}
            placeholder="1.05"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">
            Описание (необязательно)
          </label>
          <input suppressHydrationWarning
            type="text"
            value={info}
            onChange={(e) => setInfo(e.target.value)}
            className={inputClass}
            placeholder="Оплата за…"
          />
        </div>

        {/* Fee Estimate */}
        {(estimatingFee || feeEstimate) && (
          <div className="rounded-lg border border-border bg-muted p-3 text-xs dark:border-border dark:bg-card/50">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Icon icon="solar:calculator-linear" className="text-sm" />
              <span className="font-medium">Оценка комиссии</span>
            </div>
            {estimatingFee ? (
              <div className="mt-2 flex items-center gap-2 text-muted-foreground">
                <Icon icon="solar:refresh-linear" className="animate-spin text-sm" />
                Расчёт...
              </div>
            ) : feeEstimate ? (
              <div className="mt-2 space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Комиссия:</span>
                  <span className="font-mono text-foreground">{feeEstimate.fee}</span>
                </div>
                {feeEstimate.total && (
                  <div className="flex justify-between border-t border-border pt-1">
                    <span className="text-muted-foreground font-medium">Итого:</span>
                    <span className="font-mono font-medium text-foreground">{feeEstimate.total}</span>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        )}

        {/* Validation Results */}
        {validation && (
          <div
            className={`rounded-lg border p-3 text-sm ${
              validation.valid
                ? "border-green-200 bg-green-50 dark:border-green-500/20 dark:bg-green-900/10"
                : "border-red-200 bg-red-50 dark:border-red-500/20 dark:bg-red-900/10"
            }`}
          >
            <div className="flex items-start gap-2">
              <span className="text-lg">{validation.valid ? "✅" : "❌"}</span>
              <div className="flex-1">
                <p className={`font-medium ${validation.valid ? "text-success" : "text-destructive"}`}>
                  {validation.valid ? "Транзакция корректна" : "Ошибка валидации"}
                </p>
                {validation.errors.length > 0 && (
                  <ul className="mt-2 space-y-1 text-xs text-destructive">
                    {validation.errors.map((err, i) => (<li key={i}>• {err}</li>))}
                  </ul>
                )}
                {validation.warnings.length > 0 && (
                  <ul className="mt-2 space-y-1 text-xs text-yellow-600 dark:text-yellow-400">
                    {validation.warnings.map((warn, i) => (<li key={i}>⚠️ {warn}</li>))}
                  </ul>
                )}
                {validation.balance && (
                  <p className="mt-2 text-xs text-muted-foreground">Доступный баланс: {validation.balance}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {error && <p className="text-xs text-destructive">{error}</p>}

        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleValidate}
            disabled={loading || validating || !tokenString || !toAddress || !value}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-xs font-medium text-foreground hover:bg-muted disabled:opacity-50 dark:border-border dark:bg-muted dark:text-faint dark:hover:bg-slate-700 transition-colors"
          >
            <Icon icon="solar:shield-check-linear" className="text-sm" />
            {validating ? "Проверка…" : "Проверить"}
          </button>
          <button
            type="submit"
            disabled={loading || validating || !tokenString || (validation ? !validation.valid : false)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            <Icon icon="solar:plain-linear" className="text-sm" />
            {loading ? "Отправка…" : "Отправить"}
          </button>
        </div>
      </form>
    </Card>
  );
}

// ─── Empty tokens helper UI ─────────────────────────────────────────
//
// Shown when the selected wallet returns 0 tokens. This is the real
// state of a fresh Safina wallet — we explain WHY it's empty and give
// concrete next steps (faucet for testnets, deposit address for
// mainnets), instead of the previous silent "Токены не найдены".

const FAUCETS: Record<number, { name: string; faucet?: string; explorer?: string; isTestnet: boolean }> = {
  1000: { name: "Bitcoin",            isTestnet: false },
  1010: { name: "Bitcoin Test",       isTestnet: true,  faucet: "https://coinfaucet.eu/en/btc-testnet/" },
  3000: { name: "Ethereum",           isTestnet: false },
  3010: { name: "Ethereum Ropsten",   isTestnet: true,  faucet: "https://sepoliafaucet.com/" },
  3040: { name: "Ethereum Sepolia",   isTestnet: true,  faucet: "https://sepoliafaucet.com/" },
  5000: { name: "Tron",               isTestnet: false },
  5010: { name: "Tron Nile TestNet",  isTestnet: true,  faucet: "https://nileex.io/join/getJoinPage" },
};

function EmptyTokensCallout({ networkId, walletAddr }: { networkId?: number; walletAddr?: string | null }) {
  const net = (networkId !== undefined && FAUCETS[networkId]) || undefined;
  const isTestnet = net?.isTestnet ?? false;
  const faucetUrl = net?.faucet;
  const networkLabel = net?.name ?? `Сеть ${networkId ?? "?"}`;

  return (
    <div className="rounded-lg border border-warning/40 bg-warning/5 p-3.5 space-y-3">
      <div className="flex items-start gap-2.5">
        <Icon icon="solar:info-circle-bold" className="text-warning text-base shrink-0 mt-0.5" />
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-foreground">На этом кошельке пока нет токенов</p>
          <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">
            {isTestnet
              ? `Это тестовая сеть ${networkLabel}. Получите тестовые токены через faucet (бесплатно), и они появятся здесь после следующего sync с Safina (≤ 1 минуты).`
              : `Чтобы отправить транзакцию, кошелёк должен иметь ненулевой баланс. Пополните его через свой Safina-кабинет или другой кошелёк, отправив средства на адрес ниже.`}
          </p>
        </div>
      </div>

      {isTestnet && faucetUrl && (
        <a
          href={faucetUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-[11px] font-medium text-primary-foreground hover:opacity-90 transition-opacity"
        >
          <Icon icon="solar:hand-money-linear" className="text-[13px]" />
          Открыть {networkLabel} Faucet
          <Icon icon="solar:arrow-right-up-linear" className="text-[12px]" />
        </a>
      )}

      {walletAddr && (
        <div className="pt-2.5 border-t border-warning/20">
          <div className="text-[10px] font-mono uppercase tracking-[0.08em] text-faint mb-1">
            Адрес кошелька (для пополнения)
          </div>
          <div className="flex items-center gap-2">
            <code className="text-[11px] font-mono text-foreground break-all">{walletAddr}</code>
            <button
              type="button"
              onClick={() => {
                navigator.clipboard.writeText(walletAddr);
              }}
              className="shrink-0 inline-flex items-center gap-1 rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground hover:text-foreground hover:border-strong transition-colors"
              aria-label="Копировать адрес"
            >
              <Icon icon="solar:copy-linear" className="text-[11px]" />
              копировать
            </button>
          </div>
        </div>
      )}

      <p className="text-[10px] text-muted-foreground">
        Или выбери другой кошелёк выше — возможно у соседнего есть баланс.
      </p>
    </div>
  );
}
