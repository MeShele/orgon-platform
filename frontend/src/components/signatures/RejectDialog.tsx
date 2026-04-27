"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useTranslations } from "@/hooks/useTranslations";

interface Props {
  txUnid: string;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}

export function RejectDialog({ txUnid, onConfirm, onCancel }: Props) {
  const t = useTranslations('signatures.pending.rejectDialog');
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onConfirm(reason);
      onCancel();
    } catch (error) {
      console.error("Failed to reject transaction:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const truncateTxUnid = (unid: string) => {
    if (unid.length <= 16) return unid;
    return `${unid.substring(0, 8)}...${unid.substring(unid.length - 8)}`;
  };

  return (
    <Dialog.Root open onOpenChange={(open) => !open && onCancel()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed left-[50%] top-[50%] z-50 w-full max-w-md translate-x-[-50%] translate-y-[-50%] rounded-lg border border-border bg-white p-6 shadow-lg dark:border-gray-700 dark:bg-gray-800 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]">
          <Dialog.Title className="text-lg font-semibold text-foreground">
            {t('title')}
          </Dialog.Title>

          <Dialog.Description className="sr-only">
            {t('title')}
          </Dialog.Description>

          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div>
              <label
                htmlFor="reason"
                className="block text-sm font-medium text-foreground"
              >
                {t('reasonLabel')}
              </label>
              <textarea
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder={t('reasonPlaceholder')}
                rows={3}
                className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-foreground placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-primary/30/20 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100 dark:placeholder-gray-500 dark:focus:border-blue-400"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={onCancel}
                disabled={isSubmitting}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-foreground hover:bg-muted focus:outline-none focus:ring-2 focus:ring-primary/30/20 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                {t('cancelButton')}
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="rounded-lg bg-destructive px-4 py-2.5 text-sm font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-red-500/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {t('confirmButton')}
              </button>
            </div>
          </form>

          <Dialog.Close asChild>
            <button
              className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-white transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:ring-offset-2 disabled:pointer-events-none dark:ring-offset-gray-800"
              aria-label="Close"
            >
              <svg
                className="h-4 w-4 text-muted-foreground"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
