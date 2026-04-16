"use client";

import { Card, CardHeader } from "@/components/common/Card";
import { CryptoIcon } from "@/components/common/CryptoIcon";
import { helpContent } from "@/lib/help-content";
import { useTranslations } from "@/hooks/useTranslations";

type TokenBalance = {
  token: string;
  value: number;
  network_name?: string;
};

export function TokenSummary({ tokens }: { tokens: TokenBalance[] }) {
  const t = useTranslations('dashboard');
  
  return (
    <Card>
      <CardHeader 
        title={t('tokens.title')} 
        subtitle={t('tokens.subtitle')}
        helpText={helpContent.dashboard.tokenSummary.text}
        helpExample={helpContent.dashboard.tokenSummary.example}
        helpTips={helpContent.dashboard.tokenSummary.tips}
      />
      <div className="space-y-1 p-2">
        {tokens.length === 0 && (
          <p className="py-4 text-center text-xs text-slate-500">{t('tokens.noBalances')}</p>
        )}
        {tokens.map((t, i) => {
          const hasBalance = t.value > 0;
          return (
            <div
              key={i}
              className={`group flex items-center justify-between rounded-lg p-2 ${
                hasBalance
                  ? "bg-slate-100 dark:bg-slate-800/30"
                  : "hover:bg-slate-50 dark:hover:bg-slate-800/20"
              }`}
            >
              <div className="flex items-center gap-3">
                <CryptoIcon token={t.token} />
                <div>
                  <div className="text-xs font-medium text-slate-900 dark:text-white">{t.token}</div>
                  {t.network_name && (
                    <div className="text-[10px] text-slate-500 dark:text-slate-400">{t.network_name}</div>
                  )}
                </div>
              </div>
              <div
                className={`text-xs font-medium ${
                  hasBalance
                    ? "text-slate-900 dark:text-white"
                    : "text-slate-500 dark:text-slate-400"
                }`}
              >
                {typeof t.value === "number" ? t.value.toFixed(4) : t.value}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
