"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Card, CardHeader } from "@/components/common/Card";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";

const inputClass =
  "w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 dark:border-slate-800 dark:bg-slate-900/50 dark:text-white focus:outline-none focus:ring-1 focus:ring-slate-400 dark:focus:ring-slate-600 transition-colors";

const selectClass =
  "rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-900/50 dark:text-white focus:outline-none focus:ring-1 focus:ring-slate-400 dark:focus:ring-slate-600 transition-colors";

export function CreateWalletForm() {
  const router = useRouter();
  const [network, setNetwork] = useState("5010");
  const [info, setInfo] = useState("");
  const [isMultiSig, setIsMultiSig] = useState(false);
  const [minSigns, setMinSigns] = useState("2");
  const [signers, setSigners] = useState([{ type: "all", ecaddress: "" }]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const addSigner = () => {
    setSigners([...signers, { type: "all", ecaddress: "" }]);
  };

  const updateSigner = (idx: number, field: string, value: string) => {
    const updated = [...signers];
    updated[idx] = { ...updated[idx], [field]: value };
    setSigners(updated);
  };

  const removeSigner = (idx: number) => {
    setSigners(signers.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data: Record<string, unknown> = { network, info };
      if (isMultiSig && signers.length > 0) {
        const slist: Record<string, unknown> = { min_signs: minSigns };
        signers.forEach((s, i) => {
          slist[String(i)] = { type: s.type, ecaddress: s.ecaddress };
        });
        data.slist = slist;
      }
      const result = await api.createWallet(data as Parameters<typeof api.createWallet>[0]);
      router.push(`/wallets/${result.myUNID}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create wallet");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="max-w-2xl">
      <CardHeader title="Create Wallet" subtitle="Create a new wallet on Safina Pay" />
      <form onSubmit={handleSubmit} className="space-y-4 p-4">
        <div>
          <label className="flex items-center gap-1 text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
            Network
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
          <label className="flex items-center gap-1 text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
            Description
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
            placeholder="My wallet"
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="multisig"
            checked={isMultiSig}
            onChange={(e) => setIsMultiSig(e.target.checked)}
            className="rounded border-slate-300 text-slate-900 focus:ring-slate-500 dark:border-slate-700 dark:bg-slate-900"
          />
          <label htmlFor="multisig" className="flex items-center gap-1 text-xs font-medium text-slate-600 dark:text-slate-300">
            Multi-signature wallet
            <HelpTooltip 
              text={helpContent.createWallet.multiSig.text}
              example={helpContent.createWallet.multiSig.example}
              tips={helpContent.createWallet.multiSig.tips}
              diagram={helpContent.createWallet.multiSig.diagram}
            />
          </label>
        </div>

        {isMultiSig && (
          <div className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-800">
            <div>
              <label className="flex items-center gap-1 text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
                Minimum signatures required
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
              <div className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-400">
                <span className="w-32">
                  Signer type 
                  <HelpTooltip 
                    text={helpContent.createWallet.signerType.text}
                    example={helpContent.createWallet.signerType.example}
                    tips={helpContent.createWallet.signerType.tips}
                  />
                </span>
                <span className="flex-1">
                  EC address 
                  <HelpTooltip 
                    text={helpContent.createWallet.ecAddress.text}
                    example={helpContent.createWallet.ecAddress.example}
                    tips={helpContent.createWallet.ecAddress.tips}
                    diagram={helpContent.createWallet.ecAddress.diagram}
                  />
                </span>
              </div>
              
              {signers.map((s, i) => (
                <div key={i} className="flex items-center gap-2">
                  <select
                    value={s.type}
                    onChange={(e) => updateSigner(i, "type", e.target.value)}
                    className={`${selectClass} w-32`}
                  >
                    <option value="all">All methods</option>
                    <option value="any">Any method</option>
                  </select>
                  <input
                    type="text"
                    value={s.ecaddress}
                    onChange={(e) => updateSigner(i, "ecaddress", e.target.value)}
                    placeholder="0x... EC address"
                    className={`${inputClass} flex-1 font-mono`}
                  />
                  {signers.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeSigner(i)}
                      className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 transition-colors"
                    >
                      <Icon icon="solar:trash-bin-minimalistic-linear" className="text-base" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addSigner}
              className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
            >
              <Icon icon="solar:add-circle-linear" className="text-sm" />
              Add signer
            </button>
          </div>
        )}

        {error && (
          <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-slate-900 px-4 py-2.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200 transition-colors"
        >
          {loading ? "Creating..." : "Create Wallet"}
        </button>
      </form>
    </Card>
  );
}
