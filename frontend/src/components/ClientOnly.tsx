"use client";

import { useEffect, useState } from 'react';

/**
 * ClientOnly wrapper to prevent SSR hydration mismatch
 * Use for components with dynamic content (icons, dates, Math.random, etc)
 */
export function ClientOnly({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return <>{children}</>;
}
