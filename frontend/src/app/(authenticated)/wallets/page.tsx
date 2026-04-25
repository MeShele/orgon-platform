"use client";
import { OnboardingTip } from "@/components/common/OnboardingTip";

import { useEffect, useState } from "react";
import { useTranslations } from "@/hooks/useTranslations";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { WalletTable } from "@/components/wallets/WalletTable";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Tooltip, HelpText } from "@/components/ui/Tooltip";
import { Icon } from "@/lib/icons";
import { api, API_BASE } from "@/lib/api";
import { pageLayout, buttonStyles } from "@/lib/page-layout";

export default function WalletsPage() {
  const t = useTranslations('wallets');
  const router = useRouter();
  const [wallets, setWallets] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    api
      .getWallets()
      .then(setWallets)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleExport = async () => {
    setExporting(true);
    try {
      const url = `${API_BASE}/export/wallets/csv`;
      window.open(url, "_blank");
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
      <Header title={t('title')} />
      <div className={pageLayout.container}>
        {/* Action Bar */}
        <div className={pageLayout.actionBar}>
          <p className={pageLayout.header.subtitle}>
            {t('count', { count: wallets.length })}
          </p>
          <div className="flex gap-2">
          <button
            onClick={() => router.push('/wallets/new')}
            className={buttonStyles.primary || "px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"}
          >
            <Icon icon="solar:add-circle-linear" />
            Создать кошелёк
          </button>
          <Tooltip
            content={
              <HelpText
                title="Экспорт кошельков"
                description="Сохраните список ваших кошельков в формате CSV для учета или анализа в Excel/Google Sheets."
                example="Экспорт → Открыть в Excel → Анализ балансов"
                tips={[
                  "Файл содержит: имя кошелька, адрес, баланс, дату создания",
                  "Используйте для бухгалтерского учета или отчетности",
                  "CSV можно открыть в любой программе для работы с таблицами"
                ]}
              />
            }
            position="bottom"
            maxWidth="320px"
          >
            <button
              onClick={handleExport}
              disabled={exporting || loading || wallets.length === 0}
              className={buttonStyles.secondary}
            >
              <Icon 
                icon={exporting ? "solar:loader-linear" : "solar:download-linear"} 
                className={exporting ? "animate-spin" : ""} 
              />
              {exporting ? t('exporting') : t('exportButton')}
            </button>
          </Tooltip>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className={pageLayout.error}>
            {error}
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className={pageLayout.loading}>
            <LoadingSpinner />
          </div>
        ) : (
          <WalletTable wallets={wallets as Parameters<typeof WalletTable>[0]["wallets"]} />
        )}
      </div>
    </>
  );
}
