"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useTranslations } from '@/hooks/useTranslations';
import { HelpTooltip } from '@/components/common/HelpTooltip';
import { helpContent } from '@/lib/help-content';

interface VolumeChartProps {
  data: Array<{
    network_id: number;
    network_name: string;
    tx_count: number;
    total_value: number;
  }>;
}

export default function VolumeChart({ data }: VolumeChartProps) {
  const t = useTranslations('analytics.charts');
  
  // Format data for recharts
  const chartData = data.slice(0, 10).map(item => ({
    network: item.network_name || `${t('network')} ${item.network_id}`,
    transactions: item.tx_count,
    value: item.total_value,
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-4 sm:p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
      <h3 className="text-base sm:text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100 flex items-center gap-2">
        {t('transactionVolume')}
        <HelpTooltip 
          text={helpContent.analytics.volumeChart.text}
          example={helpContent.analytics.volumeChart.example}
          tips={helpContent.analytics.volumeChart.tips}
        />
      </h3>
      
      {data.length === 0 ? (
        <div className="h-64 flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
          <svg className="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-sm">{t('noData')}</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid 
              strokeDasharray="3 3" 
              stroke="currentColor" 
              className="stroke-gray-200 dark:stroke-gray-700"
            />
            <XAxis 
              dataKey="network" 
              tick={{ fontSize: 12, fill: 'currentColor' }}
              className="fill-gray-600 dark:fill-gray-400"
              angle={-45}
              textAnchor="end"
              height={80}
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
            <Bar 
              yAxisId="left"
              dataKey="transactions" 
              fill="#3b82f6" 
              radius={[8, 8, 0, 0]}
              name={t('transactions')}
            />
            <Bar 
              yAxisId="right"
              dataKey="value" 
              fill="#10b981" 
              radius={[8, 8, 0, 0]}
              name={t('totalValue')}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
