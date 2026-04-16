"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';
import { useTranslations } from '@/hooks/useTranslations';
import { HelpTooltip } from '@/components/common/HelpTooltip';
import { helpContent } from '@/lib/help-content';

interface BalanceChartProps {
  data: Array<{
    date: string;
    tx_count: number;
    total_value: number;
  }>;
  days?: number;
}

export default function BalanceChart({ data, days = 30 }: BalanceChartProps) {
  const t = useTranslations('analytics.charts');
  
  // Format data for recharts
  const chartData = data.map(item => ({
    date: format(new Date(item.date), 'MMM d'),
    transactions: item.tx_count,
    value: item.total_value,
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-4 sm:p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
      <h3 className="text-base sm:text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100 flex items-center gap-2">
        {t('transactionActivity')} ({days} дн)
        <HelpTooltip 
          text={helpContent.analytics.balanceChart.text}
          example={helpContent.analytics.balanceChart.example}
          tips={helpContent.analytics.balanceChart.tips}
        />
      </h3>
      
      {data.length === 0 ? (
        <div className="h-64 flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
          <svg className="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
          <p className="text-sm">{t('noData')}</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid 
              strokeDasharray="3 3" 
              stroke="currentColor" 
              className="stroke-gray-200 dark:stroke-gray-700"
            />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 12, fill: 'currentColor' }}
              className="fill-gray-600 dark:fill-gray-400"
            />
            <YAxis 
              yAxisId="left"
              tick={{ fontSize: 12, fill: 'currentColor' }}
              className="fill-gray-600 dark:fill-gray-400"
            />
            <YAxis 
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 12, fill: 'currentColor' }}
              className="fill-gray-600 dark:fill-gray-400"
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: 'rgb(var(--tooltip-bg, 255 255 255))',
                border: '1px solid rgb(var(--tooltip-border, 229 231 235))',
                borderRadius: '8px',
                fontSize: '14px',
                color: 'rgb(var(--tooltip-text, 17 24 39))'
              }}
              wrapperClassName="dark:[--tooltip-bg:31_41_55] dark:[--tooltip-border:55_65_81] dark:[--tooltip-text:243_244_246]"
            />
            <Legend 
              wrapperStyle={{
                color: 'currentColor'
              }}
              className="text-gray-600 dark:text-gray-400"
            />
            <Line 
              yAxisId="left"
              type="monotone" 
              dataKey="transactions" 
              stroke="#3b82f6" 
              strokeWidth={2}
              dot={{ fill: '#3b82f6', r: 3 }}
              activeDot={{ r: 5 }}
              name={t('transactions')}
            />
            <Line 
              yAxisId="right"
              type="monotone" 
              dataKey="value" 
              stroke="#10b981" 
              strokeWidth={2}
              dot={{ fill: '#10b981', r: 3 }}
              activeDot={{ r: 5 }}
              name={t('totalValue')}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
