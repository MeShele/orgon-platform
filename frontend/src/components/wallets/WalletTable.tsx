"use client";

import { useState } from "react";
import Link from "next/link";
import { CopyButton } from "@/components/common/CopyButton";
import { shortenAddress } from "@/lib/utils";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";
import { useTranslations } from "@/hooks/useTranslations";
import { api } from "@/lib/api";

type Wallet = {
  name: string;
  network: number;
  addr: string;
  info: string;
  token_short_names: string;
  label?: string;
  is_favorite?: number;
};

export function WalletTable({ wallets: initialWallets }: { wallets: Wallet[] }) {
  const t = useTranslations('wallets.table');
  const [wallets, setWallets] = useState<Wallet[]>(initialWallets);
  const [editingLabel, setEditingLabel] = useState<string | null>(null);
  const [labelValue, setLabelValue] = useState("");

  const toggleFavorite = async (name: string) => {
    try {
      await api.post(`/api/wallets/${name}/favorite`);
      setWallets((prev) =>
        prev.map((w) =>
          w.name === name ? { ...w, is_favorite: w.is_favorite ? 0 : 1 } : w
        )
      );
    } catch (err) {
      console.error("Failed to toggle favorite:", err);
    }
  };

  const startEditLabel = (w: Wallet) => {
    setEditingLabel(w.name);
    setLabelValue(w.label || "");
  };

  const saveLabel = async (name: string) => {
    try {
      await api.put(`/api/wallets/${name}/label`, { label: labelValue });
      setWallets((prev) =>
        prev.map((w) => (w.name === name ? { ...w, label: labelValue } : w))
      );
    } catch (err) {
      console.error("Failed to save label:", err);
    }
    setEditingLabel(null);
  };

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900/40 dark:shadow-none">
      <div className="overflow-x-auto"><table className="min-w-full text-left text-xs">
        <thead className="text-slate-500 dark:text-slate-400">
          <tr className="border-b border-slate-100 dark:border-slate-800">
            <th className="whitespace-nowrap px-4 py-3 font-medium">
              <HelpTooltip 
                text={helpContent.walletTable.favorite.text}
                example={helpContent.walletTable.favorite.example}
                tips={helpContent.walletTable.favorite.tips}
              />
            </th>
            <th className="whitespace-nowrap px-4 py-3 font-medium">
              <span className="inline-flex items-center gap-1">
                {t('name')} 
                <HelpTooltip 
                  text={helpContent.walletTable.name.text}
                  example={helpContent.walletTable.name.example}
                  tips={helpContent.walletTable.name.tips}
                />
              </span>
            </th>
            <th className="hidden md:table-cell whitespace-nowrap px-4 py-3 font-medium">
              <span className="inline-flex items-center gap-1">
                {t('address')} 
                <HelpTooltip 
                  text={helpContent.walletTable.address.text}
                  example={helpContent.walletTable.address.example}
                  tips={helpContent.walletTable.address.tips}
                />
              </span>
            </th>
            <th className="whitespace-nowrap px-4 py-3 font-medium">
              <span className="inline-flex items-center gap-1">
                {t('network')} 
                <HelpTooltip 
                  text={helpContent.walletTable.network.text}
                  example={helpContent.walletTable.network.example}
                  tips={helpContent.walletTable.network.tips}
                />
              </span>
            </th>
            <th className="hidden md:table-cell whitespace-nowrap px-4 py-3 font-medium">
              <span className="inline-flex items-center gap-1">
                {t('tokens')} 
                <HelpTooltip 
                  text={helpContent.walletTable.tokens.text}
                  example={helpContent.walletTable.tokens.example}
                  tips={helpContent.walletTable.tokens.tips}
                />
              </span>
            </th>
            <th className="hidden md:table-cell whitespace-nowrap px-4 py-3 font-medium">
              <span className="inline-flex items-center gap-1">
                {t('info')} 
                <HelpTooltip 
                  text={helpContent.walletTable.info.text}
                  example={helpContent.walletTable.info.example}
                  tips={helpContent.walletTable.info.tips}
                />
              </span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
          {wallets.length === 0 && (
            <tr>
              <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                {t('noWallets')}
              </td>
            </tr>
          )}
          {wallets.map((w) => (
            <tr key={w.name} className="transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/30">
              <td className="px-4 py-3">
                <button
                  onClick={() => toggleFavorite(w.name)}
                  className="hover:scale-110 transition-transform"
                  title={w.is_favorite ? "Убрать из избранного" : "Добавить в избранное"}
                >
                  <Icon
                    icon={w.is_favorite ? "solar:star-bold" : "solar:star-linear"}
                    className={`text-base cursor-pointer ${
                      w.is_favorite
                        ? "text-amber-400"
                        : "text-slate-300 hover:text-amber-300 dark:text-slate-700 dark:hover:text-amber-500"
                    }`}
                  />
                </button>
              </td>
              <td className="px-4 py-3">
                {editingLabel === w.name ? (
                  <form
                    onSubmit={(e) => { e.preventDefault(); saveLabel(w.name); }}
                    className="flex items-center gap-1"
                  >
                    <input
                      type="text"
                      value={labelValue}
                      onChange={(e) => setLabelValue(e.target.value)}
                      className="w-32 rounded border border-slate-300 bg-white px-2 py-0.5 text-xs dark:border-slate-700 dark:bg-slate-800 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      autoFocus
                      onBlur={() => saveLabel(w.name)}
                      onKeyDown={(e) => e.key === "Escape" && setEditingLabel(null)}
                    />
                  </form>
                ) : (
                  <div className="flex items-center gap-1 group">
                    <Link
                      href={`/wallets/${w.name}`}
                      className="font-medium text-slate-900 hover:text-indigo-600 dark:text-white dark:hover:text-indigo-400 transition-colors"
                    >
                      {w.label || shortenAddress(w.name, 8)}
                    </Link>
                    <button
                      onClick={() => startEditLabel(w)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Редактировать метку"
                    >
                      <Icon icon="solar:pen-linear" className="text-xs text-slate-400 hover:text-indigo-500" />
                    </button>
                  </div>
                )}
              </td>
              <td className="hidden md:table-cell px-4 py-3">
                {w.addr ? (
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-slate-700 dark:text-slate-300">
                      {shortenAddress(w.addr)}
                    </span>
                    <CopyButton text={w.addr} />
                  </div>
                ) : (
                  <span className="text-slate-500 italic">{t('pending')}</span>
                )}
              </td>
              <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{w.network}</td>
              <td className="hidden md:table-cell px-4 py-3">
                {w.token_short_names && (
                  <div className="flex flex-wrap gap-1">
                    {w.token_short_names.split(",").map((t) => (
                      <span
                        key={t}
                        className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                      >
                        {t.trim()}
                      </span>
                    ))}
                  </div>
                )}
              </td>
              <td className="hidden md:table-cell px-4 py-3 text-slate-600 dark:text-slate-400">{w.info || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table></div>
    </div>
  );
}
