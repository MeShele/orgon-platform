"use client";

import { NetworkIcon } from "@/components/common/CryptoIcon";
import { StatusDot } from "@/components/common/StatusBadge";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";

type Network = {
  network_id: number;
  network_name: string;
  status: number;
};

function isTestnet(name: string): boolean {
  const lower = name.toLowerCase();
  return lower.includes("test") || lower.includes("sepolia") || lower.includes("nile");
}

export function NetworkStatus({ networks }: { networks: Network[] }) {
  return (
    <div className="space-y-4">
      <div className="px-1">
        <h3 className="flex items-center gap-1 text-sm font-medium text-slate-900 dark:text-white">
          Networks
          <HelpTooltip text={helpContent.networks.networkId.text} />
        </h3>
        <p className="text-xs text-slate-500">Active blockchain networks</p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {networks.length === 0 && (
          <p className="col-span-full py-4 text-center text-xs text-slate-500">No networks loaded</p>
        )}
        {networks.map((net) => (
          <div
            key={net.network_id}
            className="group flex items-center justify-between rounded-lg border border-slate-200 bg-white p-3 shadow-sm hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/40 dark:shadow-none dark:hover:border-slate-700 transition-colors"
          >
            <div className="flex items-center gap-3">
              <NetworkIcon
                networkName={net.network_name}
                isTestnet={isTestnet(net.network_name)}
              />
              <div>
                <div className="text-xs font-medium text-slate-900 dark:text-white">
                  {net.network_name}
                </div>
                <div className="font-mono text-[10px] text-slate-500">
                  ID: {net.network_id}
                </div>
              </div>
            </div>
            <StatusDot active={net.status === 1} />
          </div>
        ))}
      </div>
    </div>
  );
}
