"use client";

import Link from "next/link";
import { Card } from "@/components/common/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";
import { useTranslations } from "@/hooks/useTranslations";

interface Activity {
  type: "transaction" | "signature";
  timestamp: string;
  title: string;
  details: {
    tx_unid?: string;
    token?: string;
    value?: string;
    to_address?: string;
    status?: string;
    action?: string;
    signer?: string;
    reason?: string;
  };
  priority: "low" | "medium" | "high";
}

interface Props {
  activities: Activity[];
  limit?: number;
}

export function RecentActivity({ activities, limit = 20 }: Props) {
  const t = useTranslations('dashboard');
  const displayActivities = activities.slice(0, limit);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffMinutes < 1) return t('activity.justNow');
    if (diffMinutes < 60) return t('activity.minutesAgo', { count: diffMinutes });

    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return t('activity.hoursAgo', { count: diffHours });

    const diffDays = Math.floor(diffHours / 24);
    return t('activity.daysAgo', { count: diffDays });
  };

  const getActivityIcon = (activity: Activity) => {
    if (activity.type === "transaction") {
      switch (activity.details.status) {
        case "confirmed":
          return "solar:check-circle-bold";
        case "pending":
          return "solar:hourglass-linear";
        case "signed":
          return "solar:pen-linear";
        case "rejected":
          return "solar:close-circle-bold";
        default:
          return "solar:export-linear";
      }
    } else {
      // signature
      return activity.details.action === "signed" 
        ? "solar:check-circle-bold" 
        : "solar:close-circle-bold";
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "border-l-red-500";
      case "medium":
        return "border-l-yellow-500";
      case "low":
        return "border-l-green-500";
      default:
        return "border-l-gray-500";
    }
  };

  const truncate = (str: string, length: number) => {
    if (str.length <= length) return str;
    return `${str.substring(0, length)}...`;
  };

  if (displayActivities.length === 0) {
    return (
      <Card>
        <div className="p-6 text-center">
          <Icon 
            icon="solar:inbox-linear" 
            className="mx-auto mb-4 text-6xl text-muted-foreground dark:text-muted-foreground"
          />
          <h3 className="text-lg font-medium text-foreground">
            {t('activity.noActivity')}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {t('activity.noActivityDesc')}
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            {t('activity.title')}
            <HelpTooltip
              text={helpContent.dashboard.recentActivity.text}
              example={helpContent.dashboard.recentActivity.example}
              tips={helpContent.dashboard.recentActivity.tips}
            />
          </h3>
          <span className="text-sm text-muted-foreground">
            {t('activity.lastEvents', { count: displayActivities.length })}
          </span>
        </div>

        <div className="space-y-3">
          {displayActivities.map((activity, index) => (
            <div
              key={`${activity.type}-${activity.details.tx_unid}-${index}`}
              className={`flex items-start gap-3 rounded-lg border-l-4 bg-gray-50 p-3 dark:bg-gray-800 ${getPriorityColor(
                activity.priority
              )}`}
            >
              <Icon 
                icon={getActivityIcon(activity)} 
                className="text-xl flex-shrink-0 mt-0.5 text-muted-foreground"
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground">
                  {activity.title}
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span>{formatTimestamp(activity.timestamp)}</span>
                  {activity.details.token && (
                    <>
                      <span>•</span>
                      <span className="font-medium">{activity.details.token}</span>
                    </>
                  )}
                  {activity.details.value && (
                    <>
                      <span>•</span>
                      <span className="font-mono">{activity.details.value}</span>
                    </>
                  )}
                  {activity.details.status && (
                    <>
                      <span>•</span>
                      <StatusBadge status={activity.details.status} />
                    </>
                  )}
                </div>
                {activity.details.tx_unid && (
                  <Link
                    href={`/transactions/${activity.details.tx_unid}`}
                    className="mt-1 inline-block text-xs font-medium text-blue-600 hover:underline dark:text-blue-400"
                  >
                    {t('activity.viewDetails')}
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>

        {activities.length > limit && (
          <div className="mt-4 text-center">
            <Link
              href="/transactions"
              className="text-sm font-medium text-blue-600 hover:underline dark:text-blue-400"
            >
              {t('activity.viewAll')}
            </Link>
          </div>
        )}
      </div>
    </Card>
  );
}
