"use client";

import { useState, useEffect } from "react";
import { Icon } from "@/lib/icons";

interface OnboardingTipProps {
  id: string;
  text: string;
  icon?: string;
}

export function OnboardingTip({ id, text, icon = "solar:info-circle-bold" }: OnboardingTipProps) {
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    const key = `orgon_tip_${id}`;
    if (!localStorage.getItem(key)) {
      setDismissed(false);
    }
  }, [id]);

  const dismiss = () => {
    localStorage.setItem(`orgon_tip_${id}`, "1");
    setDismissed(true);
  };

  if (dismissed) return null;

  return (
    <div className="rounded-lg bg-primary/10 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 p-3 flex items-start gap-3">
      <Icon icon={icon} className="text-lg text-primary shrink-0 mt-0.5" />
      <p className="text-sm text-primary dark:text-indigo-300 flex-1">{text}</p>
      <button onClick={dismiss} className="text-primary hover:text-primary shrink-0">
        <Icon icon="solar:close-circle-linear" className="text-lg" />
      </button>
    </div>
  );
}
