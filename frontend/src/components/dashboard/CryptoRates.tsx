"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import { Icon } from "@/lib/icons";
import { useTranslations } from "@/hooks/useTranslations";

interface Rate {
  token?: string;
  symbol?: string;
  name?: string;
  price_usd?: number;
  price?: number;
  change_24h?: number;
  change?: number;
}

export function CryptoRates() {
  const t = useTranslations("dashboard.rates");
  const { data, error, isLoading } = useSWR("/api/rates", () => api.get("/api/rates"), {
    refreshInterval: 60000,
  });

  const rates: Rate[] = Array.isArray(data) ? data : data?.rates || [];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/40">
      <div className="flex items-center gap-2 mb-3">
        <Icon icon="solar:chart-2-bold" className="text-lg text-indigo-500" />
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
          {t("title")}
        </h3>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-6 text-xs text-slate-400">
          <Icon icon="solar:refresh-linear" className="animate-spin mr-2" />
          {t("loading")}
        </div>
      )}

      {error && !isLoading && (
        <div className="text-xs text-slate-400 text-center py-4">{t("noData")}</div>
      )}

      {!isLoading && rates.length > 0 && (
        <div className="space-y-2">
          {rates.slice(0, 10).map((rate, i) => {
            const symbol = rate.token || rate.symbol || rate.name || "???";
            const price = rate.price_usd || rate.price || 0;
            const change = rate.change_24h || rate.change || 0;
            const isUp = change >= 0;

            return (
              <div
                key={`${symbol}-${i}`}
                className="flex items-center justify-between py-1.5 border-b border-slate-100 dark:border-slate-800 last:border-0"
              >
                <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  {symbol}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-slate-900 dark:text-white">
                    ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  {change !== 0 && (
                    <span
                      className={`text-[10px] font-medium flex items-center gap-0.5 ${
                        isUp ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                      }`}
                    >
                      <Icon
                        icon={isUp ? "solar:arrow-up-linear" : "solar:arrow-down-linear"}
                        className="text-[10px]"
                      />
                      {Math.abs(change).toFixed(2)}%
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {!isLoading && !error && rates.length === 0 && (
        <div className="text-xs text-slate-400 text-center py-4">{t("noData")}</div>
      )}
    </div>
  );
}
