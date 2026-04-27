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
    <div className="rounded-xl border border-border bg-white dark:border-border dark:bg-card p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Icon icon="solar:calculator-bold" className="text-2xl text-primary" />
        <h2 className="text-lg font-bold text-foreground">Margin Calculator</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Tariff Plan</label>
          <select value={tier} onChange={(e) => setTier(e.target.value as Tier)} className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground">
            <option value="A">A — Start (small exchanges)</option>
            <option value="B">B — Business (medium)</option>
            <option value="C">C — Enterprise (banks)</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Network</label>
          <select value={network} onChange={(e) => setNetwork(e.target.value)} className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground">
            {Object.keys(BLOCKCHAIN_FEES).map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Transaction Amount ($)</label>
          <input type="number" value={amount} onChange={(e) => setAmount(+e.target.value)} className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground" />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Monthly Transactions</label>
          <input type="number" value={txCount} onChange={(e) => setTxCount(+e.target.value)} className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground" />
        </div>
      </div>

      <div className="border-t border-border pt-4">
        <h3 className="text-sm font-semibold text-foreground mb-3">Per Transaction Breakdown</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-muted-foreground">TX Commission ({(t.txFee * 100).toFixed(1)}%)</span><span className="text-foreground font-medium">${txCommission.toFixed(2)}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Blockchain Fee ({network})</span><span className="text-foreground font-medium">${blockchainFee.toFixed(2)}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Blockchain Markup ({(t.blockchainMarkup * 100)}%)</span><span className="text-foreground font-medium">${(blockchainFee * t.blockchainMarkup).toFixed(2)}</span></div>
          <div className="flex justify-between border-t border-border pt-2 font-semibold"><span className="text-foreground">Total Client Pays</span><span className="text-primary dark:text-primary">${totalPerTx.toFixed(2)}</span></div>
        </div>
      </div>

      <div className="border-t border-border pt-4">
        <h3 className="text-sm font-semibold text-foreground mb-3">Monthly Revenue (Tier {tier})</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-muted-foreground">Subscription Fee</span><span className="text-foreground font-medium">${t.monthlyFee.toFixed(0)}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">TX Revenue ({txCount} × ${txCommission.toFixed(2)})</span><span className="text-foreground font-medium">${(txCount * txCommission).toFixed(2)}</span></div>
          <div className="flex justify-between font-semibold"><span className="text-foreground">Total Monthly</span><span className="text-success">${monthlyRevenue.toFixed(2)}</span></div>
          <div className="flex justify-between text-xs"><span className="text-muted-foreground">ASYSTEM Share (50%)</span><span className="text-muted-foreground">${asystemShare.toFixed(2)}</span></div>
          <div className="flex justify-between text-xs"><span className="text-muted-foreground">KAZ.ONE Share (50%)</span><span className="text-muted-foreground">${kazOneShare.toFixed(2)}</span></div>
        </div>
      </div>
    </div>
  );
}
