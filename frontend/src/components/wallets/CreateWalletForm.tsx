"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardHeader } from "@/components/common/Card";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";

const inputClass =
  "w-full rounded-lg border border-border bg-muted px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground dark:border-border dark:bg-card/50 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary/30 dark:focus:ring-slate-600 transition-colors";

const selectClass =
  "rounded-lg border border-border bg-muted px-3 py-2 text-xs text-foreground dark:border-border dark:bg-card/50 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary/30 dark:focus:ring-slate-600 transition-colors";

type SignerMethod = "ecaddress" | "email" | "sms";
type Signer = { type: "all" | "any"; method: SignerMethod; value: string };

export function CreateWalletForm() {
  const router = useRouter();
  const [network, setNetwork] = useState("5010");
  const [info, setInfo] = useState("");
  const [isMultiSig, setIsMultiSig] = useState(false);
  const [minSigns, setMinSigns] = useState("2");
  const [signers, setSigners] = useState<Signer[]>([
    { type: "all", method: "ecaddress", value: "" },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const addSigner = () => {
    setSigners([...signers, { type: "all", method: "ecaddress", value: "" }]);
  };

  const updateSigner = <K extends keyof Signer>(idx: number, field: K, value: Signer[K]) => {
    const updated = [...signers];
    updated[idx] = { ...updated[idx], [field]: value };
    setSigners(updated);
  };

  const removeSigner = (idx: number) => {
    setSigners(signers.filter((_, i) => i !== idx));
  };

  const placeholderFor = (m: SignerMethod) =>
    m === "ecaddress" ? "0x… EC-адрес" : m === "email" ? "user@example.com" : "+77770000000";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data: Record<string, unknown> = { network, info };
      if (isMultiSig && signers.length > 0) {
        const slist: Record<string, unknown> = { min_signs: minSigns };
        signers.forEach((s, i) => {
          slist[String(i)] = { type: s.type, [s.method]: s.value };
        });
        data.slist = slist;
      }
      await api.createWallet(data as Parameters<typeof api.createWallet>[0]);
      // Wallet is in the DB right away with empty addr; the list
      // renders it under "Ожидание активации" until the scheduler
      // sync fills in the on-chain addr (5–10 min). Routing into the
      // detail page would be hostile while there's nothing to act on
      // there, so we land back on the list.
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
            <option value="1010">Bitcoin Test (BTC)</option>
            <option value="3000">Ethereum (ETH)</option>
            <option value="3010">ETH Ropsten Test</option>
            <option value="5000">Tron (TRX)</option>
            <option value="5010">Tron Nile TestNet (TRX)</option>
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

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="multisig"
            checked={isMultiSig}
            onChange={(e) => setIsMultiSig(e.target.checked)}
            className="rounded border-slate-300 text-foreground focus:ring-slate-500 dark:border-border dark:bg-card"
          />
          <label htmlFor="multisig" className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
            Мультиподписной кошелёк
            <HelpTooltip
              text={helpContent.createWallet.multiSig.text}
              example={helpContent.createWallet.multiSig.example}
              tips={helpContent.createWallet.multiSig.tips}
              diagram={helpContent.createWallet.multiSig.diagram}
            />
          </label>
        </div>

        {isMultiSig && (
          <div className="space-y-3 rounded-lg border border-border p-4 dark:border-border">
            <div>
              <label className="flex items-center gap-1 text-xs font-medium text-muted-foreground mb-1.5">
                Минимум подписей для проведения
                <HelpTooltip
                  text={helpContent.createWallet.minSigns.text}
                  example={helpContent.createWallet.minSigns.example}
                  tips={helpContent.createWallet.minSigns.tips}
                />
              </label>
              <input
                type="number"
                value={minSigns}
                onChange={(e) => setMinSigns(e.target.value)}
                min="1"
                className={`${inputClass} w-32`}
              />
            </div>

            <div className="space-y-2">
              <div className="grid grid-cols-[7rem_8rem_1fr_auto] gap-2 text-xs font-medium text-muted-foreground">
                <span>
                  Подтверждение
                  <HelpTooltip
                    text={helpContent.createWallet.signerType.text}
                    example={helpContent.createWallet.signerType.example}
                    tips={helpContent.createWallet.signerType.tips}
                  />
                </span>
                <span>Способ</span>
                <span>
                  Идентификатор
                  <HelpTooltip
                    text={helpContent.createWallet.ecAddress.text}
                    example={helpContent.createWallet.ecAddress.example}
                    tips={helpContent.createWallet.ecAddress.tips}
                    diagram={helpContent.createWallet.ecAddress.diagram}
                  />
                </span>
                <span />
              </div>

              {signers.map((s, i) => (
                <div key={i} className="grid grid-cols-[7rem_8rem_1fr_auto] gap-2 items-center">
                  <select
                    value={s.type}
                    onChange={(e) => updateSigner(i, "type", e.target.value as Signer["type"])}
                    className={selectClass}
                  >
                    <option value="all">Все методы</option>
                    <option value="any">Любой метод</option>
                  </select>
                  <select
                    value={s.method}
                    onChange={(e) =>
                      updateSigner(i, "method", e.target.value as SignerMethod)
                    }
                    className={selectClass}
                  >
                    <option value="ecaddress">EC-адрес</option>
                    <option value="email">Email</option>
                    <option value="sms">SMS</option>
                  </select>
                  <input
                    type={s.method === "email" ? "email" : "text"}
                    value={s.value}
                    onChange={(e) => updateSigner(i, "value", e.target.value)}
                    placeholder={placeholderFor(s.method)}
                    className={`${inputClass} font-mono`}
                  />
                  {signers.length > 1 ? (
                    <button
                      type="button"
                      onClick={() => removeSigner(i)}
                      className="text-destructive hover:text-destructive dark:hover:text-red-300 transition-colors"
                      aria-label="Удалить подписанта"
                    >
                      <Icon icon="solar:trash-bin-minimalistic-linear" className="text-base" />
                    </button>
                  ) : (
                    <span />
                  )}
                </div>
              ))}

              {signers.some((s) => s.method === "email") ? (
                <p className="text-[11px] text-muted-foreground/80 leading-snug pt-1">
                  Email-подписант получит письмо с ссылкой подтверждения от Safina.
                  Без клика по ссылке кошелёк не активируется (адрес не выдаётся).
                </p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={addSigner}
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground dark:hover:text-white transition-colors"
            >
              <Icon icon="solar:add-circle-linear" className="text-sm" />
              Добавить подписанта
            </button>
          </div>
        )}

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
