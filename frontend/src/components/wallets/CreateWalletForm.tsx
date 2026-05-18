"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { api } from "@/lib/api";
import { Card, CardHeader } from "@/components/common/Card";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";

const inputClass =
  "w-full rounded-lg border border-border bg-muted px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground dark:border-border dark:bg-card/50 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary/30 dark:focus:ring-slate-600 transition-colors";

const selectClass =
  "rounded-lg border border-border bg-muted px-3 py-2 text-xs text-foreground dark:border-border dark:bg-card/50 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary/30 dark:focus:ring-slate-600 transition-colors";

/**
 * Wallet creation form.
 *
 * Headless custodial model — the form just asks for `network` and an
 * optional `info` note; the backend's wallet_service auto-injects an
 * slist with the org's own EC as the sole signatory + `min_signs:"1"`
 * (see backend/services/wallet_service.py:_create_wallet_internal).
 *
 * No multi-sig UI here: email/SMS-anchored slists trap the wallet in
 * a "pending forever" state (Safina expects an email-confirm click,
 * which leaks the platform to the merchant's end-user). The single-EC
 * model is what `www.safina.pro` itself uses and what we've verified
 * E2E across all seven networks (2026-05-18).
 */
export function CreateWalletForm() {
  const router = useRouter();
  const [network, setNetwork] = useState("5010");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // No slist field — backend signs with the org's EC and injects
      // single-signer slist itself. Sending an empty object or
      // user-entered EC here would just confuse Safina.
      await api.createWallet({ network, info });
      toast.success("Кошелёк создан. Адрес появится в течение ~60 секунд.", {
        duration: 6000,
      });
      router.push("/wallets");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create wallet");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="max-w-2xl">
      <CardHeader title="Создать кошелёк" subtitle="Новый кошелёк на стороне Safina Pay" />
      <form onSubmit={handleSubmit} className="space-y-4 p-4">
        <div>
          <label className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
            Сеть
            <HelpTooltip
              text={helpContent.createWallet.network.text}
              example={helpContent.createWallet.network.example}
              tips={helpContent.createWallet.network.tips}
            />
          </label>
          <select
            value={network}
            onChange={(e) => setNetwork(e.target.value)}
            className={`${selectClass} w-full`}
          >
            <option value="1000">Bitcoin (BTC)</option>
            <option value="3000">Ethereum (ETH)</option>
            <option value="3040">Ethereum Sepolia (testnet)</option>
            <option value="5000">Tron (TRX)</option>
            <option value="5010">Tron Nile (testnet)</option>
            <option value="5800">ORGON</option>
            <option value="5810">ORGON TestNet</option>
          </select>
        </div>

        <div>
          <label className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
            Описание
            <HelpTooltip
              text={helpContent.createWallet.description.text}
              example={helpContent.createWallet.description.example}
              tips={helpContent.createWallet.description.tips}
            />
          </label>
          <input
            type="text"
            value={info}
            onChange={(e) => setInfo(e.target.value)}
            className={inputClass}
            placeholder="Например: операционный кошелёк"
          />
        </div>

        <p className="text-[11px] text-muted-foreground/80 leading-snug">
          Подписант — EC-ключ вашей организации; подставляется автоматически.
          Активация в Safina занимает ~60 секунд, потом on-chain адрес
          появится в списке.
        </p>

        {error && (
          <p className="text-xs text-destructive">{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {loading ? "Создание…" : "Создать кошелёк"}
        </button>
      </form>
    </Card>
  );
}
