"use client";

import { useState, useEffect } from "react";
import * as Select from "@radix-ui/react-select";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";
import { useTranslations } from "@/hooks/useTranslations";

interface Filters {
  wallet?: string;
  status?: string;
  network?: string;
  from_date?: string;
  to_date?: string;
}

interface Props {
  onFilterChange: (filters: Filters) => void;
  wallets: Array<{ name: string }>;
  networks: Array<{ network_id: string; network_name: string }>;
}

export function TransactionFilters({
  onFilterChange,
  wallets,
  networks,
}: Props) {
  const t = useTranslations('transactions');
  const [filters, setFilters] = useState<Filters>({});
  const [activeCount, setActiveCount] = useState(0);

  useEffect(() => {
    const count = Object.values(filters).filter((v) => v !== "" && v !== undefined).length;
    setActiveCount(count);
  }, [filters]);

  const handleChange = (key: keyof Filters, value: string | undefined) => {
    setFilters((prev) => {
      const newFilters = { ...prev };
      if (value === undefined || value === "__all__") {
        delete newFilters[key];
      } else {
        newFilters[key] = value;
      }
      return newFilters;
    });
  };

  const handleApply = () => {
    onFilterChange(filters);
  };

  const handleClear = () => {
    setFilters({});
    onFilterChange({});
  };

  const statuses = [
    { value: "pending", label: t('statuses.pending') },
    { value: "signed", label: t('statuses.signed') },
    { value: "confirmed", label: t('statuses.confirmed') },
    { value: "rejected", label: t('statuses.rejected') },
  ];

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {t('filters.title')}
          {activeCount > 0 && (
            <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
              {activeCount}
            </span>
          )}
        </h3>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {/* Wallet Filter */}
        <div>
          <label className="mb-1 flex items-center gap-1 text-xs font-medium text-gray-700 dark:text-gray-300">
            {t('filters.wallet')}
            <HelpTooltip 
              text={helpContent.transactionFilters.wallet.text}
              example={helpContent.transactionFilters.wallet.example}
              tips={helpContent.transactionFilters.wallet.tips}
            />
          </label>
          <Select.Root
            value={filters.wallet || "__all__"}
            onValueChange={(value) => handleChange("wallet", value)}
          >
            <Select.Trigger className="flex h-9 w-full items-center justify-between rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-900 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100 dark:hover:bg-gray-800">
              <Select.Value placeholder={t('filters.allWallets')} />
              <Select.Icon>
                <Icon icon="solar:alt-arrow-down-linear" className="h-4 w-4" />
              </Select.Icon>
            </Select.Trigger>
            <Select.Portal>
              <Select.Content className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800">
                <Select.Viewport className="p-1">
                  <Select.Item
                    value="__all__"
                    className="relative flex cursor-pointer select-none items-center rounded px-8 py-2 text-sm text-gray-900 outline-none hover:bg-gray-100 dark:text-gray-100 dark:hover:bg-gray-700"
                  >
                    <Select.ItemText>{t('filters.allWallets')}</Select.ItemText>
                  </Select.Item>
                  {wallets.map((wallet) => (
                    <Select.Item
                      key={wallet.name}
                      value={wallet.name}
                      className="relative flex cursor-pointer select-none items-center rounded px-8 py-2 text-sm text-gray-900 outline-none hover:bg-gray-100 dark:text-gray-100 dark:hover:bg-gray-700"
                    >
                      <Select.ItemText>{wallet.name}</Select.ItemText>
                    </Select.Item>
                  ))}
                </Select.Viewport>
              </Select.Content>
            </Select.Portal>
          </Select.Root>
        </div>

        {/* Status Filter */}
        <div>
          <label className="mb-1 flex items-center gap-1 text-xs font-medium text-gray-700 dark:text-gray-300">
            {t('filters.status')}
            <HelpTooltip 
              text={helpContent.transactionFilters.status.text}
              example={helpContent.transactionFilters.status.example}
              tips={helpContent.transactionFilters.status.tips}
            />
          </label>
          <Select.Root
            value={filters.status || "__all__"}
            onValueChange={(value) => handleChange("status", value)}
          >
            <Select.Trigger className="flex h-9 w-full items-center justify-between rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-900 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100 dark:hover:bg-gray-800">
              <Select.Value placeholder={t('filters.allStatuses')} />
              <Select.Icon>
                <Icon icon="solar:alt-arrow-down-linear" className="h-4 w-4" />
              </Select.Icon>
            </Select.Trigger>
            <Select.Portal>
              <Select.Content className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800">
                <Select.Viewport className="p-1">
                  <Select.Item
                    value="__all__"
                    className="relative flex cursor-pointer select-none items-center rounded px-8 py-2 text-sm text-gray-900 outline-none hover:bg-gray-100 dark:text-gray-100 dark:hover:bg-gray-700"
                  >
                    <Select.ItemText>{t('filters.allStatuses')}</Select.ItemText>
                  </Select.Item>
                  {statuses.map((status) => (
                    <Select.Item
                      key={status.value}
                      value={status.value}
                      className="relative flex cursor-pointer select-none items-center rounded px-8 py-2 text-sm text-gray-900 outline-none hover:bg-gray-100 dark:text-gray-100 dark:hover:bg-gray-700"
                    >
                      <Select.ItemText>{status.label}</Select.ItemText>
                    </Select.Item>
                  ))}
                </Select.Viewport>
              </Select.Content>
            </Select.Portal>
          </Select.Root>
        </div>

        {/* Network Filter */}
        <div>
          <label className="mb-1 flex items-center gap-1 text-xs font-medium text-gray-700 dark:text-gray-300">
            {t('filters.network')}
            <HelpTooltip 
              text={helpContent.transactionFilters.network.text}
              example={helpContent.transactionFilters.network.example}
              tips={helpContent.transactionFilters.network.tips}
            />
          </label>
          <Select.Root
            value={filters.network || "__all__"}
            onValueChange={(value) => handleChange("network", value)}
          >
            <Select.Trigger className="flex h-9 w-full items-center justify-between rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-900 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100 dark:hover:bg-gray-800">
              <Select.Value placeholder={t('filters.allNetworks')} />
              <Select.Icon>
                <Icon icon="solar:alt-arrow-down-linear" className="h-4 w-4" />
              </Select.Icon>
            </Select.Trigger>
            <Select.Portal>
              <Select.Content className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800">
                <Select.Viewport className="p-1">
                  <Select.Item
                    value="__all__"
                    className="relative flex cursor-pointer select-none items-center rounded px-8 py-2 text-sm text-gray-900 outline-none hover:bg-gray-100 dark:text-gray-100 dark:hover:bg-gray-700"
                  >
                    <Select.ItemText>{t('filters.allNetworks')}</Select.ItemText>
                  </Select.Item>
                  {networks.map((network) => (
                    <Select.Item
                      key={network.network_id}
                      value={network.network_id}
                      className="relative flex cursor-pointer select-none items-center rounded px-8 py-2 text-sm text-gray-900 outline-none hover:bg-gray-100 dark:text-gray-100 dark:hover:bg-gray-700"
                    >
                      <Select.ItemText>{network.network_name}</Select.ItemText>
                    </Select.Item>
                  ))}
                </Select.Viewport>
              </Select.Content>
            </Select.Portal>
          </Select.Root>
        </div>

        {/* From Date */}
        <div>
          <label
            htmlFor="from_date"
            className="mb-1 flex items-center gap-1 text-xs font-medium text-gray-700 dark:text-gray-300"
          >
            {t('filters.fromDate')}
            <HelpTooltip 
              text={helpContent.transactionFilters.period.text}
              example={helpContent.transactionFilters.period.example}
              tips={helpContent.transactionFilters.period.tips}
            />
          </label>
          <input
            type="date"
            id="from_date"
            value={filters.from_date || ""}
            onChange={(e) => handleChange("from_date", e.target.value)}
            className="h-9 w-full rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
          />
        </div>

        {/* To Date */}
        <div>
          <label
            htmlFor="to_date"
            className="mb-1 flex items-center gap-1 text-xs font-medium text-gray-700 dark:text-gray-300"
          >
            {t('filters.toDate')}
            <HelpTooltip 
              text={helpContent.transactionFilters.period.text}
              example={helpContent.transactionFilters.period.example}
              tips={helpContent.transactionFilters.period.tips}
            />
          </label>
          <input
            type="date"
            id="to_date"
            value={filters.to_date || ""}
            onChange={(e) => handleChange("to_date", e.target.value)}
            className="h-9 w-full rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
          />
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mt-4 flex gap-2">
        <button
          onClick={handleApply}
          className="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
        >
          {t('filters.applyButton')}
        </button>
        {activeCount > 0 && (
          <button
            onClick={handleClear}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            {t('filters.clearButton')}
          </button>
        )}
      </div>
    </div>
  );
}
