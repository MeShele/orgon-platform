"use client";

export function LoadingSpinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const sizeClass = {
    sm: "h-4 w-4",
    md: "h-8 w-8",
    lg: "h-12 w-12",
  }[size];

  return (
    <div className="flex items-center justify-center p-8">
      <div
        className={`${sizeClass} animate-spin rounded-full border-2 border-border border-t-slate-900 dark:border-border dark:border-t-white`}
      />
    </div>
  );
}
