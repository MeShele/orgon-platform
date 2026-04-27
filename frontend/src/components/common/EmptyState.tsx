"use client";

import { Icon } from "@/lib/icons";

interface EmptyStateProps {
  icon: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  actionHref?: string;
}

export function EmptyState({ icon, title, description, actionLabel, onAction, actionHref }: EmptyStateProps) {
  const ActionTag = actionHref ? "a" : "button";
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
        <Icon icon={icon} className="text-3xl text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground mb-6 max-w-md">{description}</p>
      {actionLabel && (
        <ActionTag
          onClick={onAction}
          {...(actionHref ? { href: actionHref } : {})}
          className="px-4 py-2 rounded-lg bg-primary text-white text-sm hover:opacity-90 transition-colors"
        >
          {actionLabel}
        </ActionTag>
      )}
    </div>
  );
}
