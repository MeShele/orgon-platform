"use client";

import { useState } from "react";
import { Icon } from "@/lib/icons";

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
      title="Copy"
    >
      {copied ? (
        <Icon icon="solar:check-circle-bold" className="h-3.5 w-3.5 text-emerald-500" />
      ) : (
        <Icon icon="solar:copy-linear" className="h-3.5 w-3.5" />
      )}
    </button>
  );
}
