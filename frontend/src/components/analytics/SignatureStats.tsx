"use client";

import { useTranslations } from '@/hooks/useTranslations';
import { HelpTooltip } from '@/components/common/HelpTooltip';
import { helpContent } from '@/lib/help-content';

interface SignatureStatsProps {
  data: {
    signed: number;
    total: number;
    pending: number;
    completion_rate: number;
  };
}

export default function SignatureStats({ data }: SignatureStatsProps) {
  const t = useTranslations('analytics');
  const { signed, total, pending, completion_rate } = data;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-4 sm:p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
      <h3 className="text-base sm:text-lg font-semibold mb-6 text-gray-900 dark:text-gray-100 flex items-center gap-2">
        {t('charts.signatureStats')}
        <HelpTooltip 
          text={helpContent.analytics.signatureStats.text}
          example={helpContent.analytics.signatureStats.example}
          tips={helpContent.analytics.signatureStats.tips}
        />
      </h3>
      
      {total === 0 ? (
        <div className="h-48 flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
          <svg className="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-sm">{t('charts.noData')}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Circular Progress */}
          <div className="flex justify-center">
            <div className="relative w-32 h-32 sm:w-40 sm:h-40">
              {/* Background circle */}
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="50%"
                  cy="50%"
                  r="45%"
                  stroke="currentColor"
                  strokeWidth="10"
                  fill="none"
                  className="stroke-gray-200 dark:stroke-gray-700"
                />
                {/* Progress circle */}
                <circle
                  cx="50%"
                  cy="50%"
                  r="45%"
                  stroke="#10b981"
                  strokeWidth="10"
                  fill="none"
                  strokeDasharray={`${2 * Math.PI * 45}`}
                  strokeDashoffset={`${2 * Math.PI * 45 * (1 - completion_rate / 100)}`}
                  strokeLinecap="round"
                  className="transition-all duration-1000"
                  style={{ transformOrigin: 'center' }}
                />
              </svg>
              
              {/* Percentage text */}
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">
                  {completion_rate.toFixed(0)}%
                </span>
                <span className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                  {t('stats.signed')}
                </span>
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-2 sm:gap-4">
            <div className="text-center p-2 sm:p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-100 dark:border-green-800/30">
              <div className="text-xl sm:text-2xl font-bold text-green-600 dark:text-green-400">{signed}</div>
              <div className="text-xs text-green-700 dark:text-green-500 mt-1">{t('stats.signed')}</div>
            </div>
            
            <div className="text-center p-2 sm:p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-100 dark:border-yellow-800/30">
              <div className="text-xl sm:text-2xl font-bold text-yellow-600 dark:text-yellow-400">{pending}</div>
              <div className="text-xs text-yellow-700 dark:text-yellow-500 mt-1">{t('stats.pending')}</div>
            </div>
            
            <div className="text-center p-2 sm:p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-800/30">
              <div className="text-xl sm:text-2xl font-bold text-blue-600 dark:text-blue-400">{total}</div>
              <div className="text-xs text-blue-700 dark:text-blue-500 mt-1">{t('stats.totalSignatures')}</div>
            </div>
          </div>

          {/* Progress Bar */}
          <div>
            <div className="flex justify-between text-xs sm:text-sm text-gray-600 dark:text-gray-400 mb-2">
              <span>{t('stats.signed')}</span>
              <span>{signed} / {total}</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
              <div
                className="bg-green-600 dark:bg-green-500 h-2.5 rounded-full transition-all duration-1000"
                style={{ width: `${completion_rate}%` }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
