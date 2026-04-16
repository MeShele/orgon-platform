"use client";

import { Icon as IconifyIcon } from '@/lib/icons';
import { useEffect, useState } from 'react';

/**
 * Safe Icon wrapper to prevent hydration mismatch from @iconify/react
 * 
 * Issue: Iconify generates dynamic IDs for SVG masks/defs (iconifyReact0, iconifyReact1...)
 * which differ between SSR and client, causing React hydration errors.
 * 
 * Solution: Render placeholder during SSR, mount icon on client only.
 */
export function SafeIcon({ 
  icon, 
  className,
  ...props 
}: { 
  icon: string; 
  className?: string;
  [key: string]: any;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    // SSR placeholder: empty span with same dimensions
    return <span className={className} style={{ display: 'inline-block', width: '1em', height: '1em' }} />;
  }

  return <IconifyIcon icon={icon} className={className} {...props} />;
}
