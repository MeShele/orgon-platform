"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { useTranslations } from '@/hooks/useTranslations';
import { HelpTooltip } from '@/components/common/HelpTooltip';
import { helpContent } from '@/lib/help-content';

interface TokenDistributionProps {
  data: Array<{
    token: string;
    value: number;
    percentage: number;
    tx_count: number;
  }>;
}

const COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
  '#6366f1', // indigo
  '#14b8a6', // teal
];

export default function TokenDistribution({ data }: TokenDistributionProps) {
  const t = useTranslations('analytics.charts');
  
  // Take top 10 tokens
  const chartData = data.slice(0, 10).map((item, index) => ({
    name: item.token,
    value: item.value,
    percentage: item.percentage,
    tx_count: item.tx_count,
    fill: COLORS[index % COLORS.length],
  }));

  // Custom label
  const renderLabel = (entry: any) => {
    if (entry.percentage < 5) return ''; // Hide small labels
    return `${entry.name} (${entry.percentage.toFixed(1)}%)`;
  };

  return (
    <div className="bg-card rounded-xl p-4 sm:p-6 border border-border shadow-sm">
      <h3 className="text-base sm:text-lg font-semibold mb-4 text-foreground flex items-center gap-2">
        {t('tokenDistribution')}
        <HelpTooltip 
          text={helpContent.analytics.tokenDistribution.text}
          example={helpContent.analytics.tokenDistribution.example}
          tips={helpContent.analytics.tokenDistribution.tips}
        />
      </h3>
      
      {data.length === 0 ? (
        <div className="h-64 flex flex-col items-center justify-center text-muted-foreground">
          <svg className="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
          </svg>
          <p className="text-sm">{t('noData')}</p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={renderLabel}
                outerRadius={90}
                fill="#8884d8"
                dataKey="value"
                className="text-xs font-medium fill-gray-700 dark:fill-gray-300"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{
                  backgroundColor: 'rgb(var(--tooltip-bg, 255 255 255))',
                  border: '1px solid rgb(var(--tooltip-border, 229 231 235))',
                  borderRadius: '8px',
                  fontSize: '14px',
                  color: 'rgb(var(--tooltip-text, 17 24 39))'
                }}
                wrapperClassName="dark:[--tooltip-bg:31_41_55] dark:[--tooltip-border:55_65_81] dark:[--tooltip-text:243_244_246]"
                formatter={(value: number | undefined, name: string | undefined, props: any) => [
                  `${(value || 0).toFixed(2)} (${props.payload.percentage.toFixed(1)}%)`,
                  props.payload.name || name || ''
                ]}
              />
            </PieChart>
          </ResponsiveContainer>
          
          {/* Legend with details */}
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {chartData.map((item, index) => (
              <div 
                key={index} 
                className="flex items-center justify-between p-2 hover:bg-muted dark:hover:bg-gray-700/50 rounded-lg transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div 
                    className="w-3 h-3 rounded-sm flex-shrink-0" 
                    style={{ backgroundColor: item.fill }}
                  />
                  <span className="font-medium text-sm text-foreground truncate">
                    {item.name}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground flex-shrink-0 ml-2">
                  {item.percentage.toFixed(1)}% ({item.tx_count} {t('txCount')})
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
