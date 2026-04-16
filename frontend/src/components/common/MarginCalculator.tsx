"use client";

import { useState } from "react";
import { Icon } from "@/lib/icons";

type Tier = "A" | "B" | "C";

const TIERS = {
  A: { name: "Start", txFee: 0.005, blockchainMarkup: 0.20, kycFee: 1.0, monthlyFee: 50 },
  B: { name: "Business", txFee: 0.002, blockchainMarkup: 0.15, kycFee: 0.5, monthlyFee: 800 },
  C: { name: "Enterprise", txFee: 0.001, blockchainMarkup: 0.10, kycFee: 0.3, monthlyFee: 5000 },
};

const BLOCKCHAIN_FEES: Record<string, number> = {
  BTC: 3.0,
  ETH: 5.0,
  TRX: 1.0,
  BNB: 0.5,
};

export function MarginCalculator() {
  const [tier, setTier] = useState<Tier>("B");
  const [amount, setAmount] = useState(1000);
  const [network, setNetwork] = useState("BTC");
  const [txCount, setTxCount] = useState(100);

  const t = TIERS[tier];
  const blockchainFee = BLOCKCHAIN_FEES[network] || 3;
  const txCommission = amount * t.txFee;
  const blockchainTotal = blockchainFee * (1 + t.blockchainMarkup);
  const totalPerTx = txCommission + blockchainTotal;
  const monthlyRevenue = txCount * txCommission + t.monthlyFee;
  const kazOneShare = monthlyRevenue * 0.5;
  const asystemShare = monthlyRevenue * 0.5;

  return (
    <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Icon icon="solar:calculator-bold" className="text-2xl text-indigo-500" />
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Margin Calculator</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Tariff Plan</label>
          <select value={tier} onChange={(e) => setTier(e.target.value as Tier)} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-white">
            <option value="A">A — Start (small exchanges)</option>
            <option value="B">B — Business (medium)</option>
            <option value="C">C — Enterprise (banks)</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Network</label>
          <select value={network} onChange={(e) => setNetwork(e.target.value)} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-white">
            {Object.keys(BLOCKCHAIN_FEES).map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Transaction Amount ($)</label>
          <input type="number" value={amount} onChange={(e) => setAmount(+e.target.value)} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-white" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Monthly Transactions</label>
          <input type="number" value={txCount} onChange={(e) => setTxCount(+e.target.value)} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-white" />
        </div>
      </div>

      <div className="border-t border-slate-200 dark:border-slate-800 pt-4">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Per Transaction Breakdown</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-slate-500">TX Commission ({(t.txFee * 100).toFixed(1)}%)</span><span className="text-slate-900 dark:text-white font-medium">${txCommission.toFixed(2)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Blockchain Fee ({network})</span><span className="text-slate-900 dark:text-white font-medium">${blockchainFee.toFixed(2)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Blockchain Markup ({(t.blockchainMarkup * 100)}%)</span><span className="text-slate-900 dark:text-white font-medium">${(blockchainFee * t.blockchainMarkup).toFixed(2)}</span></div>
          <div className="flex justify-between border-t border-slate-200 dark:border-slate-700 pt-2 font-semibold"><span className="text-slate-700 dark:text-slate-300">Total Client Pays</span><span className="text-indigo-600 dark:text-indigo-400">${totalPerTx.toFixed(2)}</span></div>
        </div>
      </div>

      <div className="border-t border-slate-200 dark:border-slate-800 pt-4">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Monthly Revenue (Tier {tier})</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-slate-500">Subscription Fee</span><span className="text-slate-900 dark:text-white font-medium">${t.monthlyFee.toFixed(0)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">TX Revenue ({txCount} × ${txCommission.toFixed(2)})</span><span className="text-slate-900 dark:text-white font-medium">${(txCount * txCommission).toFixed(2)}</span></div>
          <div className="flex justify-between font-semibold"><span className="text-slate-700 dark:text-slate-300">Total Monthly</span><span className="text-emerald-600 dark:text-emerald-400">${monthlyRevenue.toFixed(2)}</span></div>
          <div className="flex justify-between text-xs"><span className="text-slate-400">ASYSTEM Share (50%)</span><span className="text-slate-500">${asystemShare.toFixed(2)}</span></div>
          <div className="flex justify-between text-xs"><span className="text-slate-400">KAZ.ONE Share (50%)</span><span className="text-slate-500">${kazOneShare.toFixed(2)}</span></div>
        </div>
      </div>
    </div>
  );
}
