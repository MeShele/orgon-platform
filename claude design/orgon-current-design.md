# ORGON — Crimson Ledger Design Bundle

Snapshot of the redesigned frontend at `https://orgon-preview.asystem.kg`.
Use this as the source of truth when iterating in Claude Design.

> **How to read this file:** every section below is a separate file from the
> repository. The path is the section heading. The block right after is the
> exact source code. When you propose changes, output the same path-headed
> sections so they can be diffed back into the repo.

## Quick design summary

**Theme:** Crimson Ledger — institutional, dense, sharp corners (`--radius:0`).
- Light is the default, dark is composed (not inverted).
- Accent: crimson `#b81e2f` (light) / `#e23b50` (dark).
- Mono everywhere for addresses, hashes, eyebrow labels, status dots.
- IBM Plex Mono + Inter via `next/font/google`.

**Stack:** Next.js 16 App Router, React 19, TypeScript 5, Tailwind 4
(`@theme inline` syntax, no `tailwind.config.js`), Radix UI primitives,
Framer Motion, Iconify (`solar` set).

**Live preview:** https://orgon-preview.asystem.kg
Демо: `demo-admin@orgon.io` / `demo-signer@orgon.io` / `demo-viewer@orgon.io`,
пароль `demo2026`.

**API base:** `https://orgon-preview-api.asystem.kg/api/redoc` — OpenAPI docs.

---

# 1. Tokens / theme

### `frontend/src/app/globals.css`

```css
/* ORGON · Crimson Ledger
 * Institutional-grade design tokens.
 * Light is the default theme; dark is composed (not inverted).
 *
 * Fonts are wired via next/font in layout.tsx (Inter + IBM Plex Mono).
 * --font-display reuses Inter weight 500/600 with tight letter-spacing.
 */

@import 'react-datepicker/dist/react-datepicker.css';
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

@theme inline {
  /* Surface tokens */
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);

  /* Brand */
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);

  /* Quiet surfaces */
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);

  /* Semantic */
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-success: var(--success);
  --color-success-foreground: var(--success-foreground);
  --color-warning: var(--warning);
  --color-warning-foreground: var(--warning-foreground);

  /* Crimson Ledger extras */
  --color-navy: var(--navy);
  --color-navy-foreground: var(--navy-foreground);
  --color-surface-2: var(--surface-2);
  --color-border-strong: var(--border-strong);
  --color-faint: var(--faint);

  /* Form / utility */
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);

  /* Charts */
  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);

  /* Sidebar */
  --color-sidebar: var(--sidebar);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-ring: var(--sidebar-ring);

  /* Typography */
  --font-sans: var(--font-sans);
  --font-display: var(--font-display);
  --font-mono: var(--font-mono);
  --font-serif: var(--font-serif);

  /* Radius — Crimson Ledger is sharp by design.
     rounded-* utilities are pinned to 0; rounded-full kept for dots & avatars. */
  --radius-sm: 0px;
  --radius-md: 0px;
  --radius-lg: 0px;
  --radius-xl: 0px;
  --radius-2xl: 0px;
  --radius-3xl: 0px;
  --radius-full: 9999px;

  /* Shadows — minimal, mostly absent in light, subtle inner-glow in dark */
  --shadow-2xs: 0 1px 0 0 rgb(0 0 0 / 0.02);
  --shadow-xs:  0 1px 0 0 rgb(0 0 0 / 0.04);
  --shadow-sm:  0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow:     0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md:  0 2px 6px -1px rgb(0 0 0 / 0.06);
  --shadow-lg:  0 4px 12px -2px rgb(0 0 0 / 0.08);
  --shadow-xl:  0 8px 20px -4px rgb(0 0 0 / 0.10);
  --shadow-2xl: 0 16px 40px -8px rgb(0 0 0 / 0.14);
}

/* ============================================================
   LIGHT (default) — paper white, ink, crimson accent
   ============================================================ */
:root {
  /* Crimson Ledger · LIGHT */
  --background: #ffffff;          /* paper */
  --foreground: #0e1320;          /* ink with a navy whisper */
  --surface-2: #f3f2ef;           /* warm grey for sidebar/secondary surfaces */
  --faint: #8a8d96;               /* eyebrow / labels — quietest text */

  --card: #fafaf9;                /* off-white, separates from bg */
  --card-foreground: #0e1320;
  --popover: #ffffff;
  --popover-foreground: #0e1320;

  --primary: #b81e2f;             /* crimson — brand action */
  --primary-foreground: #ffffff;
  --secondary: #f3f2ef;           /* warm grey button */
  --secondary-foreground: #0e1320;

  --muted: #fafaf9;               /* quiet bg */
  --muted-foreground: #5a5e6a;
  --accent: #fbe8ea;              /* crimson-tinted soft hover */
  --accent-foreground: #7a1320;

  --destructive: #b81e2f;
  --destructive-foreground: #ffffff;
  --success: #2e6f3b;
  --success-foreground: #ffffff;
  --warning: #a86a00;
  --warning-foreground: #ffffff;

  --navy: #0a1428;                /* logo navy — for blocks (login left, popular plan) */
  --navy-foreground: #ffffff;

  --border: #e6e4df;
  --border-strong: #cbc8c1;
  --input: #e6e4df;
  --ring: #b81e2f;

  /* Charts — discriminate-color set */
  --chart-1: #b81e2f;             /* crimson */
  --chart-2: #0a1428;             /* navy */
  --chart-3: #2e6f3b;             /* green */
  --chart-4: #a86a00;             /* amber */
  --chart-5: #5a5e6a;             /* warm grey */

  /* Sidebar */
  --sidebar: #f3f2ef;
  --sidebar-foreground: #0e1320;
  --sidebar-primary: #b81e2f;
  --sidebar-primary-foreground: #ffffff;
  --sidebar-accent: #fafaf9;
  --sidebar-accent-foreground: #0e1320;
  --sidebar-border: #e6e4df;
  --sidebar-ring: #b81e2f;

  /* Typography fallbacks (real values come from next/font CSS variables) */
  --font-sans: var(--font-inter), Inter, system-ui, -apple-system, sans-serif;
  --font-display: var(--font-inter), Inter, system-ui, -apple-system, sans-serif;
  --font-mono: var(--font-plex-mono), "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace;
  --font-serif: "IBM Plex Serif", Georgia, serif;

  /* Radius (legacy — most utilities pinned via @theme above) */
  --radius: 0;

  --tracking-tight: -0.02em;
  --tracking-normal: 0em;
}

/* ============================================================
   DARK — midnight navy, brighter crimson; not an inversion
   ============================================================ */
.dark {
  --background: #070d1a;
  --foreground: #eef2f8;
  --surface-2: #142142;
  --faint: #5e6886;

  --card: #0e1830;
  --card-foreground: #eef2f8;
  --popover: #0e1830;
  --popover-foreground: #eef2f8;

  --primary: #e23b50;             /* brighter on navy */
  --primary-foreground: #ffffff;
  --secondary: #142142;
  --secondary-foreground: #eef2f8;

  --muted: #0e1830;
  --muted-foreground: #9aa3b8;
  --accent: #3d0f15;              /* deep crimson tint */
  --accent-foreground: #ff5d72;

  --destructive: #e23b50;
  --destructive-foreground: #ffffff;
  --success: #5fbf78;
  --success-foreground: #07210f;
  --warning: #e0a040;
  --warning-foreground: #2a1a04;

  --navy: #070d1a;
  --navy-foreground: #eef2f8;

  --border: #1f2c4d;
  --border-strong: #2e3d65;
  --input: #1f2c4d;
  --ring: #e23b50;

  --chart-1: #e23b50;
  --chart-2: #5fa0ff;
  --chart-3: #5fbf78;
  --chart-4: #e0a040;
  --chart-5: #9aa3b8;

  --sidebar: #0e1830;
  --sidebar-foreground: #eef2f8;
  --sidebar-primary: #e23b50;
  --sidebar-primary-foreground: #ffffff;
  --sidebar-accent: #142142;
  --sidebar-accent-foreground: #eef2f8;
  --sidebar-border: #1f2c4d;
  --sidebar-ring: #e23b50;
}

/* ============================================================
   Base
   ============================================================ */
body {
  font-family: var(--font-sans);
  background: var(--background);
  color: var(--foreground);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  letter-spacing: var(--tracking-normal);
  font-feature-settings: "ss01", "cv11";
}

/* tabular numbers for everything that should align (status counts, KPIs, money) */
.tabular,
[data-tabular] {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
}

/* Aceternity spotlight keyframe — kept for legacy components */
@keyframes spotlight {
  0%   { opacity: 0; transform: translate(-72%, -62%) scale(0.5); }
  100% { opacity: 1; transform: translate(-50%, -40%) scale(1); }
}
.animate-spotlight {
  animation: spotlight 2s ease .75s 1 forwards;
}

/* Custom scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--border-strong);
  border-radius: 0;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--muted-foreground);
}

::selection {
  background: var(--primary);
  color: var(--primary-foreground);
}

/* Focus ring — sharp, no glow */
*:focus-visible {
  outline: 2px solid var(--ring);
  outline-offset: 2px;
}

/* Address / hash mono shortcut */
.mono { font-family: var(--font-mono); }
.eyebrow {
  font-family: var(--font-mono);
  font-size: 0.6875rem;     /* 11px */
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--faint);
}

/* Token-driven utility shortcuts (kept compatible with existing class usage) */
@layer utilities {
  .bg-card { background-color: var(--card); color: var(--card-foreground); }
  .bg-popover { background-color: var(--popover); color: var(--popover-foreground); }
  .bg-primary { background-color: var(--primary); color: var(--primary-foreground); }
  .bg-secondary { background-color: var(--secondary); color: var(--secondary-foreground); }
  .bg-muted { background-color: var(--muted); color: var(--muted-foreground); }
  .bg-accent { background-color: var(--accent); color: var(--accent-foreground); }
  .bg-destructive { background-color: var(--destructive); color: var(--destructive-foreground); }
  .bg-navy { background-color: var(--navy); color: var(--navy-foreground); }

  .text-foreground { color: var(--foreground); }
  .text-primary { color: var(--primary); }
  .text-muted-foreground { color: var(--muted-foreground); }
  .text-faint { color: var(--faint); }

  .border-border { border-color: var(--border); }
  .border-strong { border-color: var(--border-strong); }

  .ring-ring { --tw-ring-color: var(--ring); }
}

```

### `frontend/src/app/layout.tsx`

```tsx
import type { Metadata } from "next";
import { cookies } from 'next/headers';
import { Inter, IBM_Plex_Mono } from 'next/font/google';
import { LanguageProvider } from '@/contexts/LanguageContext';
import { AuthProvider } from '@/contexts/AuthContext';
import "./globals.css";

const inter = Inter({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-inter',
  display: 'swap',
});

const plexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-plex-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: "ORGON — Институциональное мульти-подписное хранение криптоактивов",
  description: "Multi-signature кастоди для бирж, брокеров и банков. M-of-N подписи, регулируемый KYC/AML, белый-лейбл и B2B API.",
  keywords: ["crypto custody", "multi-signature wallet", "digital assets", "Kyrgyzstan", "ORGON", "blockchain security"],
  authors: [{ name: "ASYSTEM" }],
  openGraph: {
    title: "ORGON — Институциональное хранение криптоактивов",
    description: "Multi-signature кастоди для бирж, брокеров и банков. Регулируемый KYC/AML, белый-лейбл, B2B API.",
    url: "https://orgon.asystem.kg",
    siteName: "ORGON",
    type: "website",
    locale: "ru_RU",
  },
  twitter: {
    card: "summary_large_image",
    title: "ORGON · Institutional Custody",
    description: "Multi-signature crypto custody for exchanges, brokers and banks.",
  },
  robots: { index: true, follow: true },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const cookieStore = await cookies();
  const locale = (cookieStore.get('NEXT_LOCALE')?.value || 'ru') as 'ru' | 'en' | 'ky';
  // Default theme is light. Dark only if user explicitly selected it.
  const theme = cookieStore.get('orgon_theme')?.value === 'dark' ? 'dark' : 'light';

  return (
    <html
      lang={locale}
      className={`${inter.variable} ${plexMono.variable} ${theme === 'dark' ? 'dark' : ''}`}
      suppressHydrationWarning
    >
      <body className="bg-background text-foreground antialiased transition-colors duration-200">
        <AuthProvider>
          <LanguageProvider initialLocale={locale}>
            {children}
          </LanguageProvider>
        </AuthProvider>
      </body>
    </html>
  );
}

```

### `frontend/src/app/AppShell.tsx`

```tsx
"use client";

import { AceternitySidebar } from "@/components/layout/AceternitySidebar";
import { TooltipProvider } from "@/components/common/TooltipProvider";
import { ToastProvider } from "@/components/providers/ToastProvider";
import { SidebarProvider } from "@/components/aceternity/sidebar";
import { ReactNode, useState } from "react";
import { useToastEvents } from "@/hooks/useToastEvents";

export function AppShell({ children }: { children: ReactNode }) {
  useToastEvents();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <TooltipProvider>
      <ToastProvider />
      <SidebarProvider open={sidebarOpen} setOpen={setSidebarOpen}>
        <div className="flex min-h-screen w-full bg-background text-foreground overflow-x-hidden">
          <AceternitySidebar />
          <main className="flex min-h-screen flex-1 flex-col overflow-x-hidden">
            {children}
          </main>
        </div>
      </SidebarProvider>
    </TooltipProvider>
  );
}

```

### `frontend/src/middleware.ts`

```ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Public routes that don't require authentication
  const publicRoutes = ['/', '/login', '/register', '/features', '/pricing', '/about', '/forgot-password', '/reset-password'];
  const isPublicRoute = publicRoutes.some(route => pathname === route || pathname.startsWith(route + '/'));
  
  // Check if user has access token
  const accessToken = request.cookies.get('orgon_access_token')?.value;
  
  // If user is not authenticated and trying to access protected route
  if (!accessToken && !isPublicRoute) {
    return NextResponse.redirect(new URL('/', request.url));
  }
  
  // If user is authenticated and trying to access login/register, redirect to dashboard
  if (accessToken && (pathname === '/login' || pathname === '/register')) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public assets
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\.png|.*\\.jpg|.*\\.jpeg|.*\\.svg).*)',
  ],
};

```

### `frontend/next.config.ts`

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker
  output: 'standalone',

  // Skip TypeScript/ESLint errors during build
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
  
  // Performance optimizations
  compress: true,
  poweredByHeader: false,
  reactStrictMode: true,
  
  images: {
    formats: ['image/avif', 'image/webp'],
  },
  
  // Force cache invalidation on every build
  generateBuildId: async () => {
    return `build-${Date.now()}`;
  },
  
  // Allow cross-origin requests from production domain
  allowedDevOrigins: ['orgon.asystem.kg'],
  
  // Rewrites for API proxying
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8890';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;

```


# 2. UI atoms

### `frontend/src/components/ui/Button.tsx`

```tsx
import * as React from 'react';
import { cn } from '@/lib/utils';

export type ButtonVariant =
  | 'primary'      // crimson, brand action
  | 'secondary'    // border, neutral
  | 'ghost'        // no border, hover quiet
  | 'navy'         // navy block, white text — for popular/feature CTAs
  | 'destructive'  // crimson, dangerous
  | 'success';     // green
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
  children: React.ReactNode;
}

const SIZE: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-10 px-5 text-sm',
  lg: 'h-12 px-6 text-[15px]',
};

const VARIANT: Record<ButtonVariant, string> = {
  primary:
    'bg-primary text-primary-foreground border border-primary hover:opacity-90 active:opacity-80',
  secondary:
    'bg-transparent text-foreground border border-strong hover:bg-muted',
  ghost:
    'bg-transparent text-foreground border border-transparent hover:bg-muted',
  navy:
    'bg-navy text-navy-foreground border border-navy hover:opacity-90 active:opacity-80',
  destructive:
    'bg-destructive text-destructive-foreground border border-destructive hover:opacity-90',
  success:
    'bg-success text-success-foreground border border-success hover:opacity-90',
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading = false, fullWidth = false, className, disabled, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2',
          'font-medium tracking-tight',
          'transition-colors duration-150',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
          SIZE[size],
          VARIANT[variant],
          fullWidth && 'w-full',
          loading && 'cursor-wait',
          className,
        )}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <svg className="-ml-0.5 h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
            <path d="M4 12a8 8 0 0 1 8-8" stroke="currentColor" strokeWidth="3" />
          </svg>
        )}
        {children}
      </button>
    );
  },
);

Button.displayName = 'Button';

export default Button;

```

### `frontend/src/components/ui/Card.tsx`

```tsx
import * as React from 'react';
import { cn } from '@/lib/utils';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** visual surface — default is muted card, navy is for popular/feature blocks, plain has no border */
  surface?: 'default' | 'navy' | 'plain';
  hover?: boolean;
  padding?: boolean;
  children?: React.ReactNode;
}

export function Card({ surface = 'default', hover, padding = true, className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        surface === 'navy' && 'bg-navy text-navy-foreground border border-transparent',
        surface === 'default' && 'bg-card text-card-foreground border border-border',
        surface === 'plain' && 'bg-transparent text-foreground',
        padding && 'p-6',
        hover && 'transition-colors hover:border-strong',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  eyebrow?: React.ReactNode;
}

export function CardHeader({ title, subtitle, action, eyebrow, className, children, ...props }: CardHeaderProps) {
  return (
    <div className={cn('flex items-start justify-between gap-4 px-5 py-4 border-b border-border', className)} {...props}>
      <div>
        {eyebrow && <div className="eyebrow mb-1">{eyebrow}</div>}
        {title && <h3 className="text-[15px] font-medium tracking-tight text-foreground">{title}</h3>}
        {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
        {children}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function CardBody({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('px-5 py-4', className)} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('flex items-center justify-end gap-2 px-5 py-3 border-t border-border bg-muted', className)} {...props}>
      {children}
    </div>
  );
}

export default Card;

```

### `frontend/src/components/ui/Input.tsx`

```tsx
import * as React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  fullWidth?: boolean;
  /** Render label as eyebrow (mono uppercase) — default true for Crimson Ledger */
  eyebrowLabel?: boolean;
  /** Use mono font in the input itself (for emails, addresses, hashes) */
  mono?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, fullWidth = true, eyebrowLabel = true, mono = false, className, ...props }, ref) => {
    return (
      <div className={cn(fullWidth && 'w-full')}>
        {label && (
          <label
            htmlFor={props.id}
            className={cn(
              'block mb-1.5',
              eyebrowLabel
                ? 'eyebrow'
                : 'text-xs font-medium text-muted-foreground',
            )}
          >
            {label}
          </label>
        )}

        <input
          ref={ref}
          className={cn(
            'block w-full h-10 px-3 py-2',
            'bg-card text-foreground placeholder:text-faint',
            'border border-border',
            'transition-colors duration-150',
            'focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            mono && 'font-mono text-[13px]',
            error && 'border-destructive focus:border-destructive focus:ring-destructive/20',
            className,
          )}
          {...props}
        />

        {error && (
          <p className="mt-1.5 text-xs text-destructive">{error}</p>
        )}

        {helperText && !error && (
          <p className="mt-1.5 text-xs text-muted-foreground">{helperText}</p>
        )}
      </div>
    );
  },
);

Input.displayName = 'Input';

export default Input;

```

### `frontend/src/components/ui/Badge.tsx`

```tsx
import * as React from 'react';
import { cn } from '@/lib/utils';

export type BadgeVariant = 'primary' | 'success' | 'warning' | 'danger' | 'gray' | 'navy' | 'outline';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  /** Mono uppercase letter-spaced — Crimson Ledger default */
  mono?: boolean;
  children: React.ReactNode;
}

const VARIANT: Record<BadgeVariant, string> = {
  primary: 'bg-primary text-primary-foreground border-primary',
  success: 'bg-success text-success-foreground border-success',
  warning: 'bg-warning text-warning-foreground border-warning',
  danger: 'bg-destructive text-destructive-foreground border-destructive',
  gray: 'bg-muted text-muted-foreground border-border',
  navy: 'bg-navy text-navy-foreground border-navy',
  outline: 'bg-transparent text-foreground border-strong',
};

export function Badge({ variant = 'gray', mono = true, className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 border',
        mono ? 'font-mono text-[10px] tracking-wider uppercase' : 'text-[11px] font-medium',
        VARIANT[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}

export default Badge;

```

### `frontend/src/components/ui/primitives.tsx`

```tsx
/**
 * ORGON · Crimson Ledger primitives
 * Small typographic / inline atoms reused across the redesign.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

// ─────────────────────────────────────────────────────────
// Eyebrow — mono uppercase label, optionally prefixed with "──"
// ─────────────────────────────────────────────────────────
export interface EyebrowProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Show the leading `─── ` decorative dash */
  dash?: boolean;
  /** Override default `text-faint` color (e.g. `text-primary`) */
  tone?: 'faint' | 'primary' | 'foreground' | 'muted';
}

export function Eyebrow({ dash = false, tone = 'faint', className, children, ...props }: EyebrowProps) {
  const toneClass =
    tone === 'primary' ? 'text-primary'
    : tone === 'foreground' ? 'text-foreground'
    : tone === 'muted' ? 'text-muted-foreground'
    : 'text-faint';
  return (
    <div
      className={cn(
        'font-mono text-[11px] tracking-[0.12em] uppercase',
        toneClass,
        className,
      )}
      {...props}
    >
      {dash && <span aria-hidden="true">─── </span>}
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// Mono — inline monospace span for addresses, hashes, IDs
// ─────────────────────────────────────────────────────────
export interface MonoProps extends React.HTMLAttributes<HTMLSpanElement> {
  size?: 'xs' | 'sm' | 'md';
  /** Truncate middle: 0xAB12··EF34 */
  truncate?: boolean;
  /** Number of chars at start when truncating (default 6) */
  startChars?: number;
  /** Number of chars at end when truncating (default 4) */
  endChars?: number;
  children: React.ReactNode;
}

export function Mono({ size = 'sm', truncate, startChars = 6, endChars = 4, className, children, ...props }: MonoProps) {
  let content: React.ReactNode = children;
  if (truncate && typeof children === 'string' && children.length > startChars + endChars + 2) {
    content = `${children.slice(0, startChars)}··${children.slice(-endChars)}`;
  }
  const sizeClass = size === 'xs' ? 'text-[10px]' : size === 'md' ? 'text-[13px]' : 'text-[11px]';
  return (
    <span className={cn('font-mono tracking-tight', sizeClass, className)} {...props}>
      {content}
    </span>
  );
}

// ─────────────────────────────────────────────────────────
// BigNum — tabular-nums, tight letter-spacing for large numbers
// ─────────────────────────────────────────────────────────
export interface BigNumProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'xxl';
  weight?: 'normal' | 'medium' | 'semibold';
  children: React.ReactNode;
}

export function BigNum({ size = 'md', weight = 'medium', className, children, ...props }: BigNumProps) {
  const sizeClass =
    size === 'sm' ? 'text-base'
    : size === 'md' ? 'text-2xl'
    : size === 'lg' ? 'text-[28px]'
    : size === 'xl' ? 'text-[36px]'
    : 'text-[48px]';
  const weightClass =
    weight === 'normal' ? 'font-normal'
    : weight === 'semibold' ? 'font-semibold'
    : 'font-medium';
  return (
    <div
      className={cn(
        'tabular leading-tight tracking-[-0.02em]',
        sizeClass,
        weightClass,
        className,
      )}
      style={{ fontVariantNumeric: 'tabular-nums', fontFeatureSettings: '"tnum"' }}
      {...props}
    >
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// StatusDot — 6×6 colored dot for status pills
// ─────────────────────────────────────────────────────────
export type StatusKind = 'confirmed' | 'sent' | 'pending' | 'rejected' | 'success' | 'warning' | 'danger' | 'neutral';

const STATUS_CLASSES: Record<StatusKind, string> = {
  confirmed: 'bg-success',
  success: 'bg-success',
  sent: 'bg-foreground',
  pending: 'bg-warning',
  warning: 'bg-warning',
  rejected: 'bg-destructive',
  danger: 'bg-destructive',
  neutral: 'bg-faint',
};

export interface StatusDotProps {
  kind: StatusKind;
  /** Pending shows a small square instead of circle (Crimson Ledger convention) */
  shape?: 'auto' | 'circle' | 'square';
  className?: string;
}

export function StatusDot({ kind, shape = 'auto', className }: StatusDotProps) {
  const isSquare = shape === 'square' || (shape === 'auto' && (kind === 'pending' || kind === 'warning'));
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-block w-1.5 h-1.5 shrink-0',
        isSquare ? '' : 'rounded-full',
        STATUS_CLASSES[kind],
        className,
      )}
    />
  );
}

// ─────────────────────────────────────────────────────────
// StatusPill — StatusDot + uppercase mono label
// ─────────────────────────────────────────────────────────
export interface StatusPillProps {
  kind: StatusKind;
  label: string;
  className?: string;
}

export function StatusPill({ kind, label, className }: StatusPillProps) {
  const colorClass =
    kind === 'confirmed' || kind === 'success' ? 'text-success'
    : kind === 'pending' || kind === 'warning' ? 'text-warning'
    : kind === 'rejected' || kind === 'danger' ? 'text-destructive'
    : kind === 'sent' ? 'text-foreground'
    : 'text-faint';

  return (
    <span className={cn('inline-flex items-center gap-1.5 font-mono text-[10px] tracking-[0.06em] uppercase', colorClass, className)}>
      <StatusDot kind={kind} />
      {label}
    </span>
  );
}

// ─────────────────────────────────────────────────────────
// Divider — horizontal rule using border token
// ─────────────────────────────────────────────────────────
export function Divider({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('h-px w-full bg-border', className)} {...props} />;
}

```

### `frontend/src/components/ui/NetworkGraph.tsx`

```tsx
/**
 * NetworkGraph — multi-signature signers laid out around a central hub.
 *
 *   ● = signed (filled with primary color)
 *   ○ = pending (ring only)
 *
 * Signer addresses can be either email or blockchain address — we just
 * use the first 2 letters of the cleaned-up local part as initials.
 * If an explicit `initials` is provided, it wins.
 */

'use client';

import * as React from 'react';

export interface SignerNode {
  /** Email, blockchain address, or any unique identifier */
  address: string;
  /** Whether this signer has signed yet */
  state: 'signed' | 'pending' | 'rejected';
  /** Display name (full) — optional, used for labels next to graph */
  name?: string;
  /** Override auto-derived initials */
  initials?: string;
  /** Timestamp when signed (ISO or pre-formatted) */
  time?: string | null;
}

export interface NetworkGraphProps {
  signers: SignerNode[];
  size?: number;
  className?: string;
  /** Ring color for pending nodes — defaults to current border-strong */
  ringColor?: string;
  /** Color for signed nodes / connecting lines — defaults to primary */
  accentColor?: string;
  /** Label color */
  labelColor?: string;
}

/** Pull the first two letters of the "local" part of an email/address */
export function deriveInitials(addressOrName: string): string {
  if (!addressOrName) return '··';
  const cleaned = addressOrName.split('@')[0].replace(/^0x/i, '').replace(/[^a-zA-Zа-яА-ЯёЁ]/g, '');
  if (cleaned.length === 0) return addressOrName.slice(0, 2).toUpperCase();
  return cleaned.slice(0, 2).toUpperCase();
}

export function NetworkGraph({
  signers,
  size = 220,
  className,
  ringColor = 'var(--border-strong)',
  accentColor = 'var(--primary)',
  labelColor = 'var(--foreground)',
}: NetworkGraphProps) {
  const n = signers.length;
  if (n === 0) return null;

  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.36;

  const nodes = signers.map((s, i) => {
    const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
    return {
      ...s,
      initials: s.initials ?? deriveInitials(s.name ?? s.address),
      x: cx + Math.cos(angle) * r,
      y: cy + Math.sin(angle) * r,
    };
  });

  const nodeR = size * 0.085;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      role="img"
      aria-label="Multi-signature signer network"
    >
      {/* edges hub → node */}
      {nodes.map((node, i) => (
        <line
          key={`edge-${i}`}
          x1={cx}
          y1={cy}
          x2={node.x}
          y2={node.y}
          stroke={node.state === 'signed' ? accentColor : ringColor}
          strokeWidth={node.state === 'signed' ? 1.2 : 0.6}
          strokeDasharray={node.state === 'signed' ? '0' : '2 3'}
        />
      ))}

      {/* central hub */}
      <circle cx={cx} cy={cy} r={size * 0.06} fill={labelColor} />
      <circle cx={cx} cy={cy} r={size * 0.10} fill="none" stroke={ringColor} strokeWidth={0.5} />

      {/* signer nodes */}
      {nodes.map((node, i) => (
        <g key={`node-${i}`}>
          <circle
            cx={node.x}
            cy={node.y}
            r={nodeR}
            fill={node.state === 'signed' ? accentColor : 'transparent'}
            stroke={node.state === 'signed' ? accentColor : ringColor}
            strokeWidth={1.2}
          />
          <text
            x={node.x}
            y={node.y + size * 0.026}
            textAnchor="middle"
            fontSize={size * 0.06}
            fontFamily="ui-monospace, 'IBM Plex Mono', monospace"
            fontWeight={600}
            fill={node.state === 'signed' ? '#ffffff' : labelColor}
          >
            {node.initials}
          </text>
        </g>
      ))}
    </svg>
  );
}

export default NetworkGraph;

```

### `frontend/src/components/ui/Sparkline.tsx`

```tsx
/**
 * Sparkline — minimalistic 1px line chart with optional fill underneath.
 * Token-driven: defaults to var(--primary) for stroke.
 */

import * as React from 'react';

export interface SparklineProps {
  points: number[];
  width?: number;
  height?: number;
  strokeWidth?: number;
  /** CSS color or token. Default: `currentColor` so the parent can color it */
  stroke?: string;
  /** Fill below the line. Default: matching stroke at 10% alpha */
  fill?: string | null;
  className?: string;
  ariaLabel?: string;
}

export function Sparkline({
  points,
  width = 120,
  height = 36,
  strokeWidth = 1.2,
  stroke = 'currentColor',
  fill,
  className,
  ariaLabel,
}: SparklineProps) {
  if (!points || points.length < 2) {
    return null;
  }

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const step = width / (points.length - 1);

  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${(i * step).toFixed(2)} ${(height - ((p - min) / range) * height).toFixed(2)}`)
    .join(' ');

  const area = `${path} L ${width} ${height} L 0 ${height} Z`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role="img"
      aria-label={ariaLabel ?? 'Trend sparkline'}
    >
      {fill !== null && (
        <path d={area} fill={fill ?? stroke} fillOpacity={fill ? 1 : 0.1} />
      )}
      <path
        d={path}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default Sparkline;

```

### `frontend/src/components/ui/TxFlow.tsx`

```tsx
/**
 * TxFlow — schematic flow:  WALLET ──● {M/N} ╌╌╌▶ CHAIN
 * Used in Hero / Features sections to explain multi-signature flow at a glance.
 * Pure SVG, token-driven via currentColor + CSS variable refs.
 */

import * as React from 'react';

export interface TxFlowProps {
  width?: number;
  height?: number;
  threshold?: string;
  walletLabel?: string;
  chainLabel?: string;
  className?: string;
  /** Override CSS-var-based colors */
  accent?: string;
  muted?: string;
  fg?: string;
}

export function TxFlow({
  width = 360,
  height = 96,
  threshold = '2/3',
  walletLabel = 'WALLET',
  chainLabel = 'CHAIN',
  className,
  accent = 'var(--primary)',
  muted = 'var(--border-strong)',
  fg = 'var(--foreground)',
}: TxFlowProps) {
  const cy = height / 2;
  const left = { x: 8, w: 76, h: 36 };
  const right = { x: width - 84, w: 76, h: 36 };
  const hubX = width / 2;
  const hubR = 16;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role="img"
      aria-label="Multi-signature transaction flow"
    >
      <defs>
        <pattern id="orgon-tx-dotgrid" width={8} height={8} patternUnits="userSpaceOnUse">
          <circle cx={1} cy={1} r={0.6} fill={muted} opacity={0.5} />
        </pattern>
      </defs>

      {/* Background dot grid */}
      <rect x={0} y={0} width={width} height={height} fill="url(#orgon-tx-dotgrid)" opacity={0.4} />

      {/* Wallet block (outline) */}
      <rect x={left.x} y={cy - left.h / 2} width={left.w} height={left.h} fill="none" stroke={fg} strokeWidth={0.8} />
      <text
        x={left.x + left.w / 2}
        y={cy + 3.5}
        textAnchor="middle"
        fontSize={9}
        fontFamily="ui-monospace, 'IBM Plex Mono', monospace"
        fill={fg}
      >
        {walletLabel}
      </text>

      {/* Solid arrow into hub */}
      <line x1={left.x + left.w} y1={cy} x2={hubX - hubR} y2={cy} stroke={accent} strokeWidth={1.2} />
      <circle cx={hubX - hubR - 2} cy={cy} r={2} fill={accent} />

      {/* Hub circle with threshold label */}
      <circle cx={hubX} cy={cy} r={hubR} fill="none" stroke={accent} strokeWidth={1} />
      <text
        x={hubX}
        y={cy + 3.5}
        textAnchor="middle"
        fontSize={9}
        fontFamily="ui-monospace, 'IBM Plex Mono', monospace"
        fill={accent}
        fontWeight={600}
      >
        {threshold}
      </text>

      {/* Dashed arrow hub → chain */}
      <line
        x1={hubX + hubR}
        y1={cy}
        x2={right.x}
        y2={cy}
        stroke={accent}
        strokeWidth={1.2}
        strokeDasharray="3 2"
      />

      {/* Chain block (filled) */}
      <rect x={right.x} y={cy - right.h / 2} width={right.w} height={right.h} fill={fg} />
      <text
        x={right.x + right.w / 2}
        y={cy + 3.5}
        textAnchor="middle"
        fontSize={9}
        fontFamily="ui-monospace, 'IBM Plex Mono', monospace"
        fill="var(--background)"
      >
        {chainLabel}
      </text>
    </svg>
  );
}

export default TxFlow;

```


# 3. Layout shell

### `frontend/src/components/layout/PublicHeader.tsx`

```tsx
"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import { Icon } from "@/lib/icons";
import { Button } from "@/components/ui/Button";
import { ThemeToggle } from "./ThemeToggle";
import { cn } from "@/lib/utils";

interface NavLink {
  href: string;
  label: string;
  external?: boolean;
}

const NAV: NavLink[] = [
  { href: "/", label: "Главная" },
  { href: "/features", label: "Возможности" },
  { href: "/pricing", label: "Тарифы" },
  { href: "https://orgon-preview-api.asystem.kg/api/redoc", label: "Документация", external: true },
  { href: "/about", label: "О компании" },
];

export function PublicHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-background/85 backdrop-blur-md border-b border-border">
      <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10">
        <div className="flex h-16 items-center justify-between">
          {/* Brand */}
          <Link href="/" className="flex items-center gap-3 text-foreground">
            <Image src="/orgon-icon.png" alt="ORGON" width={32} height={32} className="shrink-0" priority />
            <div className="hidden sm:flex flex-col leading-tight">
              <span className="font-mono text-[10px] tracking-[0.18em] text-faint">ASYSTEM</span>
              <span className="font-medium text-[15px] tracking-[0.06em]">ORGON</span>
            </div>
          </Link>

          {/* Desktop nav */}
          <ul className="hidden md:flex items-center gap-7">
            {NAV.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  target={link.external ? "_blank" : undefined}
                  rel={link.external ? "noopener noreferrer" : undefined}
                  className="text-[13px] font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                  {link.label}
                  {link.external && (
                    <Icon icon="solar:arrow-right-up-linear" className="inline-block ml-1 text-[12px]" />
                  )}
                </Link>
              </li>
            ))}
          </ul>

          {/* Desktop CTA */}
          <div className="hidden md:flex items-center gap-2">
            <ThemeToggle />
            <Link href="/login">
              <Button variant="ghost" size="sm">Войти</Button>
            </Link>
            <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
              <Button variant="primary" size="sm">
                Запросить демо
                <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
              </Button>
            </a>
          </div>

          {/* Mobile burger */}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="md:hidden inline-flex items-center justify-center w-10 h-10 border border-border text-foreground"
            aria-label="Toggle menu"
          >
            <Icon icon={open ? "solar:close-circle-linear" : "solar:hamburger-menu-linear"} className="text-[20px]" />
          </button>
        </div>

        {/* Mobile drawer */}
        <div className={cn("md:hidden overflow-hidden transition-[max-height]", open ? "max-h-[500px]" : "max-h-0")}>
          <div className="py-4 border-t border-border space-y-1">
            {NAV.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                target={link.external ? "_blank" : undefined}
                rel={link.external ? "noopener noreferrer" : undefined}
                onClick={() => setOpen(false)}
                className="block px-2 py-2 text-[14px] text-foreground hover:bg-muted"
              >
                {link.label}
                {link.external && <Icon icon="solar:arrow-right-up-linear" className="inline-block ml-1 text-[12px]" />}
              </Link>
            ))}
            <div className="pt-4 mt-4 border-t border-border space-y-2">
              <Link href="/login" onClick={() => setOpen(false)}>
                <Button variant="secondary" size="sm" fullWidth>Войти</Button>
              </Link>
              <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request" onClick={() => setOpen(false)}>
                <Button variant="primary" size="sm" fullWidth>Запросить демо</Button>
              </a>
              <div className="pt-2 flex justify-center">
                <ThemeToggle />
              </div>
            </div>
          </div>
        </div>
      </nav>
    </header>
  );
}

```

### `frontend/src/components/layout/PublicFooter.tsx`

```tsx
import Link from "next/link";
import Image from "next/image";

const PRODUCT = [
  { href: "/features", label: "Возможности" },
  { href: "/pricing", label: "Тарифы" },
  { href: "https://orgon-preview-api.asystem.kg/api/redoc", label: "Документация", external: true },
  { href: "/dashboard", label: "Панель управления" },
];

const COMPANY = [
  { href: "/about", label: "О компании" },
  { href: "https://asystem.ai", label: "ASYSTEM", external: true },
  { href: "mailto:sales@orgon.asystem.kg", label: "sales@orgon.asystem.kg" },
];

const LEGAL = [
  { href: "/privacy", label: "Конфиденциальность" },
  { href: "/terms", label: "Условия" },
];

export function PublicFooter() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-border bg-muted/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div className="col-span-2">
            <Link href="/" className="inline-flex items-center gap-3 text-foreground">
              <Image src="/orgon-icon.png" alt="ORGON" width={32} height={32} />
              <div className="flex flex-col leading-tight">
                <span className="font-mono text-[10px] tracking-[0.18em] text-faint">ASYSTEM</span>
                <span className="font-medium text-[15px] tracking-[0.06em]">ORGON</span>
              </div>
            </Link>
            <p className="mt-5 text-[13px] text-muted-foreground max-w-md leading-relaxed">
              Институциональное мульти-подписное хранение криптоактивов. Для бирж,
              брокеров, банков и финтех-компаний.
            </p>
          </div>

          <FooterCol title="Продукт" items={PRODUCT} />
          <FooterCol title="Компания" items={COMPANY} />
        </div>

        <div className="mt-12 pt-6 border-t border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="font-mono text-[11px] tracking-[0.08em] text-faint">
            © {year} ASYSTEM · ORGON. Все права защищены.
          </div>
          <ul className="flex gap-5">
            {LEGAL.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="font-mono text-[11px] tracking-[0.08em] text-muted-foreground hover:text-foreground"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({ title, items }: { title: string; items: { href: string; label: string; external?: boolean }[] }) {
  return (
    <div>
      <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-faint mb-4">{title}</div>
      <ul className="space-y-2.5">
        {items.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              target={item.external ? "_blank" : undefined}
              rel={item.external ? "noopener noreferrer" : undefined}
              className="text-[13px] text-muted-foreground hover:text-foreground transition-colors"
            >
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

```

### `frontend/src/components/layout/Header.tsx`

```tsx
"use client";

import { useWebSocket } from "@/contexts/WebSocketContext";
import { Icon } from "@/lib/icons";
import { useSidebar } from "@/components/aceternity/sidebar";
import { OrganizationSwitcher } from "@/components/organizations/OrganizationSwitcher";
import { ThemeToggle } from "./ThemeToggle";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";

export function Header({ title }: { title: string }) {
  const { connected } = useWebSocket();
  const { setOpen } = useSidebar();
  const { user } = useAuth();

  const initials = (user?.full_name || user?.email || "··")
    .split(/[\s@]/)[0]
    .slice(0, 2)
    .toUpperCase();

  return (
    <header className="sticky top-0 z-30 h-14 sm:h-16 bg-background/90 backdrop-blur-md border-b border-border">
      <div className="h-full flex items-center justify-between px-3 sm:px-6">
        {/* Left cluster */}
        <div className="flex items-center gap-3 sm:gap-5 min-w-0">
          <button
            onClick={() => setOpen(true)}
            className="md:hidden inline-flex items-center justify-center w-9 h-9 border border-border text-foreground"
            aria-label="Open menu"
          >
            <Icon icon="solar:hamburger-menu-linear" className="text-[18px]" />
          </button>

          <div className="flex flex-col min-w-0">
            <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-faint hidden sm:block">
              ORGON / {title}
            </div>
            <h1 className="text-[15px] font-medium tracking-tight text-foreground truncate">{title}</h1>
          </div>

          <div className="hidden md:block h-6 w-px bg-border" />

          <div className="hidden md:block">
            <OrganizationSwitcher />
          </div>

          {/* Connection status */}
          <div
            className={cn(
              "hidden lg:inline-flex items-center gap-2 px-2.5 py-1 border font-mono text-[10px] tracking-[0.08em] uppercase",
              connected
                ? "border-success/40 text-success bg-success/5"
                : "border-border text-faint",
            )}
          >
            <span className={cn("relative flex h-1.5 w-1.5", connected && "")}>
              {connected && (
                <span className="absolute inline-flex h-full w-full rounded-full bg-success opacity-50 animate-ping" />
              )}
              <span className={cn("relative inline-flex h-1.5 w-1.5 rounded-full", connected ? "bg-success" : "bg-faint")} />
            </span>
            {connected ? "Sync · Live" : "Offline"}
          </div>
        </div>

        {/* Right cluster */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Search ⌘K placeholder (functional later) */}
          <div className="hidden lg:flex items-center gap-2 h-9 px-3 border border-border text-faint min-w-[220px]">
            <Icon icon="solar:magnifer-linear" className="text-[14px]" />
            <span className="text-[12px]">Поиск</span>
            <span className="ml-auto font-mono text-[10px] tracking-tight">⌘K</span>
          </div>

          <ThemeToggle />

          <div className="inline-flex items-center justify-center w-9 h-9 bg-primary text-primary-foreground font-mono text-[11px] font-semibold">
            {initials}
          </div>
        </div>
      </div>
    </header>
  );
}

```

### `frontend/src/components/layout/AceternitySidebar.tsx`

```tsx
"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useTranslations } from "@/hooks/useTranslations";
import { Icon } from "@/lib/icons";
import { useSidebar } from "@/components/aceternity/sidebar";
import { useAuth } from "@/contexts/AuthContext";
import { ProfileCard } from "./ProfileCard";

type Role = "all" | "admin" | "signer" | "viewer";

interface NavItem {
  href: string;
  /** i18n key under `navigation.*` namespace */
  label: string;
  icon: string;
  activeIcon: string;
  roles: Role[];
}

interface NavGroup {
  /** i18n key under `navigation.groups.*`; falls back to literal */
  label: string;
  items: NavItem[];
}

const NAV: NavGroup[] = [
  {
    label: "workspace",
    items: [
      { href: "/dashboard",    label: "dashboard",    icon: "solar:widget-linear",                  activeIcon: "solar:widget-bold",                  roles: ["all"] },
      { href: "/wallets",      label: "wallets",      icon: "solar:wallet-linear",                  activeIcon: "solar:wallet-bold",                  roles: ["all"] },
      { href: "/transactions", label: "transactions", icon: "solar:transfer-horizontal-linear",     activeIcon: "solar:transfer-horizontal-bold",     roles: ["all"] },
      { href: "/signatures",   label: "signatures",   icon: "solar:pen-linear",                     activeIcon: "solar:pen-bold",                     roles: ["admin", "signer"] },
      { href: "/scheduled",    label: "scheduled",    icon: "solar:calendar-linear",                activeIcon: "solar:calendar-bold",                roles: ["admin", "signer"] },
      { href: "/contacts",     label: "contacts",     icon: "solar:user-linear",                    activeIcon: "solar:user-bold",                    roles: ["admin", "signer"] },
      { href: "/fiat",         label: "fiat",         icon: "solar:banknote-linear",                activeIcon: "solar:banknote-bold",                roles: ["admin", "signer"] },
    ],
  },
  {
    label: "organization",
    items: [
      { href: "/organizations", label: "organizations", icon: "solar:buildings-linear",     activeIcon: "solar:buildings-bold",     roles: ["all"] },
      { href: "/partner",       label: "partner",       icon: "solar:hand-shake-linear",    activeIcon: "solar:hand-shake-bold",    roles: ["admin"] },
      { href: "/billing",       label: "billing",       icon: "solar:card-linear",          activeIcon: "solar:card-bold",          roles: ["admin"] },
      { href: "/compliance",    label: "compliance",    icon: "solar:shield-check-linear",  activeIcon: "solar:shield-check-bold",  roles: ["admin"] },
    ],
  },
  {
    label: "insights",
    items: [
      { href: "/analytics", label: "analytics", icon: "solar:chart-linear",         activeIcon: "solar:chart-bold",         roles: ["all"] },
      { href: "/audit",     label: "audit",     icon: "solar:history-linear",       activeIcon: "solar:history-bold",       roles: ["admin", "viewer"] },
      { href: "/reports",   label: "reports",   icon: "solar:document-text-linear", activeIcon: "solar:document-text-bold", roles: ["admin", "viewer"] },
    ],
  },
  {
    label: "platform",
    items: [
      { href: "/users",                   label: "users",     icon: "solar:users-group-rounded-linear", activeIcon: "solar:users-group-rounded-bold", roles: ["admin"] },
      { href: "/networks",                label: "networks",  icon: "solar:global-linear",              activeIcon: "solar:global-bold",              roles: ["admin"] },
      { href: "/settings/keys",           label: "apiKeys",   icon: "solar:key-linear",                 activeIcon: "solar:key-bold",                 roles: ["admin"] },
      { href: "/settings/webhooks",       label: "webhooks",  icon: "solar:bolt-linear",                activeIcon: "solar:bolt-bold",                roles: ["admin"] },
      { href: "/settings/system",         label: "system",    icon: "solar:server-linear",              activeIcon: "solar:server-bold",              roles: ["admin"] },
      { href: "/documents",               label: "documents", icon: "solar:document-linear",            activeIcon: "solar:document-bold",            roles: ["all"] },
    ],
  },
  {
    label: "account",
    items: [
      { href: "/profile",  label: "profile",  icon: "solar:user-id-linear",          activeIcon: "solar:user-id-bold",          roles: ["all"] },
      { href: "/settings", label: "settings", icon: "solar:settings-linear",         activeIcon: "solar:settings-bold",         roles: ["all"] },
      { href: "/support",  label: "support",  icon: "solar:chat-round-linear",       activeIcon: "solar:chat-round-bold",       roles: ["all"] },
      { href: "/help",     label: "help",     icon: "solar:question-circle-linear",  activeIcon: "solar:question-circle-bold",  roles: ["all"] },
    ],
  },
];

const COLLAPSED_W = 64;
const EXPANDED_W = 240;

export function AceternitySidebar() {
  const t = useTranslations("navigation");
  const pathname = usePathname();
  const { open, hovered, setHovered } = useSidebar();
  const { user } = useAuth();

  const isExpanded = hovered || open;
  const userRole = (user?.role || "viewer") as Role;

  const groups = NAV.map((g) => ({
    ...g,
    items: g.items.filter((i) => i.roles.includes("all") || i.roles.includes(userRole)),
  })).filter((g) => g.items.length > 0);

  return (
    <motion.aside
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      animate={{ width: isExpanded ? EXPANDED_W : COLLAPSED_W }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      className="hidden md:flex shrink-0 flex-col bg-sidebar text-sidebar-foreground border-r border-sidebar-border"
    >
      <SidebarLogo isExpanded={isExpanded} />

      <nav className="flex-1 overflow-y-auto overflow-x-hidden py-2">
        {groups.map((group, gi) => (
          <div key={gi} className="px-3 pt-3 pb-1">
            {isExpanded && (
              <div className="px-2 pb-2 font-mono text-[10px] tracking-[0.16em] uppercase text-faint">
                {t(`groups.${group.label}`)}
              </div>
            )}
            <ul className="flex flex-col gap-px">
              {group.items.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/" && pathname.startsWith(item.href + "/")) ||
                  (item.href !== "/" && pathname === item.href);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      title={!isExpanded ? t(item.label) : undefined}
                      className={cn(
                        "group flex items-center gap-3 h-9 px-2",
                        "border-l-2 transition-colors",
                        isActive
                          ? "border-primary bg-sidebar-accent text-foreground"
                          : "border-transparent text-muted-foreground hover:text-foreground hover:bg-sidebar-accent",
                      )}
                    >
                      <Icon
                        icon={isActive ? item.activeIcon : item.icon}
                        className={cn("text-[18px] shrink-0", isActive && "text-primary")}
                      />
                      {isExpanded && (
                        <span className="text-[13px] font-medium tracking-tight whitespace-nowrap overflow-hidden">
                          {t(item.label)}
                        </span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-sidebar-border">
        <ProfileCard collapsed={!isExpanded} />
      </div>
    </motion.aside>
  );
}

function SidebarLogo({ isExpanded }: { isExpanded: boolean }) {
  return (
    <Link
      href="/dashboard"
      className="flex items-center gap-3 px-4 h-16 border-b border-sidebar-border text-foreground"
    >
      <Image
        src="/orgon-icon.png"
        alt="ORGON"
        width={32}
        height={32}
        className="shrink-0"
        priority
      />
      <motion.div
        initial={false}
        animate={{ opacity: isExpanded ? 1 : 0, width: isExpanded ? "auto" : 0 }}
        transition={{ duration: 0.18, ease: "easeOut" }}
        className="overflow-hidden whitespace-nowrap"
      >
        <div className="font-mono text-[10px] tracking-[0.18em] text-faint leading-tight">ASYSTEM</div>
        <div className="font-medium text-[14px] tracking-[0.06em] leading-tight">ORGON</div>
      </motion.div>
    </Link>
  );
}

export { SidebarLogo };

```

### `frontend/src/components/layout/ThemeToggle.tsx`

```tsx
"use client";

/**
 * ThemeToggle — switches between light and dark, persists to `orgon_theme`
 * cookie (read by RootLayout on next request).
 *
 * On mount it syncs from cookie / system preference so SSR mismatch is
 * avoided. Mutating `document.documentElement.classList` directly so the
 * change is instant; the cookie is only consulted on next full request.
 */

import * as React from "react";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";

type Theme = "light" | "dark";
const COOKIE = "orgon_theme";

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const found = document.cookie.split("; ").find((c) => c.startsWith(name + "="));
  return found ? decodeURIComponent(found.split("=").slice(1).join("=")) : null;
}

function writeCookie(name: string, value: string, maxAgeDays = 365) {
  if (typeof document === "undefined") return;
  const maxAge = maxAgeDays * 24 * 60 * 60;
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}; samesite=lax`;
}

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (theme === "dark") root.classList.add("dark");
  else root.classList.remove("dark");
}

export function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = React.useState<Theme>("light");

  // Sync from current DOM class on mount (it was set by SSR via cookie)
  React.useEffect(() => {
    const initial: Theme = document.documentElement.classList.contains("dark") ? "dark" : "light";
    setTheme(initial);
  }, []);

  const toggle = React.useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === "dark" ? "light" : "dark";
      applyTheme(next);
      writeCookie(COOKIE, next);
      return next;
    });
  }, []);

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      className={cn(
        "inline-flex items-center justify-center w-9 h-9 border border-border",
        "text-muted-foreground hover:text-foreground hover:border-strong",
        "transition-colors",
        className,
      )}
    >
      <Icon
        icon={theme === "dark" ? "solar:sun-linear" : "solar:moon-linear"}
        className="text-[16px]"
      />
    </button>
  );
}

export default ThemeToggle;

```

### `frontend/src/components/providers/ToastProvider.tsx`

```tsx
"use client";

/**
 * ToastProvider — react-hot-toast wired to Crimson Ledger CSS tokens.
 * Uses CSS variables so light/dark switch automatically without a re-mount.
 */

import { Toaster } from "react-hot-toast";

export function ToastProvider() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: "var(--card)",
          color: "var(--card-foreground)",
          border: "1px solid var(--border)",
          padding: "12px 16px",
          borderRadius: "0",
          boxShadow: "var(--shadow-md)",
          fontSize: "13px",
          fontFamily: "var(--font-sans)",
        },
        success: {
          iconTheme: {
            primary: "var(--success)",
            secondary: "var(--success-foreground)",
          },
        },
        error: {
          iconTheme: {
            primary: "var(--destructive)",
            secondary: "var(--destructive-foreground)",
          },
        },
        loading: {
          iconTheme: {
            primary: "var(--primary)",
            secondary: "var(--primary-foreground)",
          },
        },
      }}
    />
  );
}

```


# 4. Public pages

### `frontend/src/app/(public)/layout.tsx`

```tsx
import { PublicHeader } from '@/components/layout/PublicHeader';
import { PublicFooter } from '@/components/layout/PublicFooter';

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <PublicHeader />
      <main className="flex-1">
        {children}
      </main>
      <PublicFooter />
    </div>
  );
}

```

### `frontend/src/app/(public)/page.tsx [LANDING]`

```tsx
"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Eyebrow, Mono, BigNum, Divider } from "@/components/ui/primitives";
import { Badge } from "@/components/ui/Badge";
import { NetworkGraph, type SignerNode } from "@/components/ui/NetworkGraph";
import { TxFlow } from "@/components/ui/TxFlow";
import { Icon } from "@/lib/icons";

const HERO_SIGNERS: SignerNode[] = [
  { address: "cfo@example", initials: "АБ", state: "signed" },
  { address: "ceo@example", initials: "ДС", state: "signed" },
  { address: "coo@example", initials: "ТО", state: "pending" },
  { address: "cto@example", initials: "АЖ", state: "pending" },
  { address: "cro@example", initials: "НИ", state: "pending" },
];

export default function LandingPage() {
  return (
    <>
      <Hero />
      <Pillars />
      <Numbers />
      <FlowSection />
      <BottomCTA />
    </>
  );
}

function Hero() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-16 lg:py-24 grid lg:grid-cols-[1.15fr_0.85fr] gap-10 lg:gap-12">
        <div>
          <Eyebrow dash tone="primary">Институциональное хранение криптоактивов</Eyebrow>

          <h1 className="mt-7 font-medium tracking-[-0.035em] leading-[1.02] text-foreground text-[44px] sm:text-[56px] lg:text-[72px]">
            Совместная подпись<br />корпоративного капитала
          </h1>

          <p className="mt-7 max-w-[480px] text-[15px] sm:text-[16px] leading-[1.55] text-muted-foreground">
            ORGON — multi-signature кастоди для бирж, брокеров и банков. Пороги
            M-of-N подписей, регулируемые KYC/AML потоки, белый-лейбл и B2B API.
          </p>

          <div className="mt-9 flex flex-wrap gap-3">
            <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
              <Button variant="primary" size="lg">
                Запросить демо
                <Icon icon="solar:arrow-right-linear" className="text-[15px]" />
              </Button>
            </a>
            <Link href="/pricing">
              <Button variant="secondary" size="lg">Смотреть тарифы</Button>
            </Link>
          </div>

          <div className="mt-14 pt-7 border-t border-border">
            <Eyebrow>Нам доверяют</Eyebrow>
            <p className="mt-3 text-[14px] text-muted-foreground max-w-md leading-[1.55]">
              Используется обменниками и финтех-компаниями Кыргызстана для
              совместного управления корпоративными криптоактивами.
            </p>
          </div>
        </div>

        {/* Right: light demo block — multi-sig in action */}
        <div className="bg-card border border-border p-7 lg:p-8 self-start">
          <div className="flex items-start justify-between gap-3">
            <div>
              <Eyebrow>WALLET · TREASURY-COLD</Eyebrow>
              <Mono size="md" className="mt-1 text-foreground">0x4f2a··b81c</Mono>
            </div>
            <Badge variant="primary">2 / 5 SIGNED</Badge>
          </div>

          <div className="mt-6 mb-2 flex justify-center">
            <NetworkGraph
              signers={HERO_SIGNERS}
              size={260}
              accentColor="var(--primary)"
              ringColor="var(--border-strong)"
              labelColor="var(--foreground)"
            />
          </div>

          <Divider className="mt-4" />

          <dl className="mt-4 space-y-2">
            <div className="flex justify-between font-mono text-[11px]">
              <dt className="uppercase tracking-[0.10em] text-faint">Amount</dt>
              <dd className="text-foreground">0.482 BTC · $45 720</dd>
            </div>
            <div className="flex justify-between font-mono text-[11px]">
              <dt className="uppercase tracking-[0.10em] text-faint">Destination</dt>
              <dd className="text-foreground">TWmh8N··aLpQ</dd>
            </div>
            <div className="flex justify-between font-mono text-[11px]">
              <dt className="uppercase tracking-[0.10em] text-faint">Network</dt>
              <dd className="text-foreground">Tron mainnet</dd>
            </div>
          </dl>
        </div>
      </div>
    </section>
  );
}

const PILLARS = [
  {
    tag: "01 / Кастоди",
    title: "Multi-signature",
    body: "Пороги M-of-N. Аппаратные ключи Ledger и Trezor. Географически распределённые подписанты. Никакой single-point-of-failure.",
    icon: "solar:shield-network-bold",
  },
  {
    tag: "02 / Compliance",
    title: "KYC · KYB · AML",
    body: "Регулируемые потоки идентификации, очередь ревью, AML-алерты в реальном времени. Соответствие FATF Travel Rule.",
    icon: "solar:document-text-bold",
  },
  {
    tag: "03 / Интеграции",
    title: "Белый-лейбл и API",
    body: "Полноценный B2B API, webhooks, fiat on/off-ramp, кастомный брендинг под ваш домен. Работает в фоне у вашего клиента.",
    icon: "solar:global-bold",
  },
];

function Pillars() {
  return (
    <section className="border-b border-border bg-muted/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-24">
        <div className="max-w-2xl">
          <Eyebrow dash tone="primary">Платформа</Eyebrow>
          <h2 className="mt-5 text-[36px] lg:text-[48px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground">
            Три столпа<br />институциональной кастоди
          </h2>
        </div>

        <div className="mt-14 grid md:grid-cols-3 gap-px bg-border border border-border">
          {PILLARS.map((p) => (
            <article key={p.tag} className="bg-card p-8 lg:p-10">
              <Eyebrow tone="primary">{p.tag}</Eyebrow>
              <Icon icon={p.icon} className="text-[40px] text-foreground mt-6" />
              <h3 className="mt-6 text-[22px] font-medium tracking-tight text-foreground">{p.title}</h3>
              <p className="mt-3 text-[14px] leading-[1.6] text-muted-foreground">{p.body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

const KPIS = [
  { label: "Поддерживаемые сети", value: "7+", sub: "TRX · BSC · ETH · POL · BTC" },
  { label: "Пороги подписей", value: "M-of-N", sub: "до 7-of-15" },
  { label: "Языки интерфейса", value: "3", sub: "RU · EN · KY" },
  { label: "Time-to-live", value: "< 5 мин", sub: "от регистрации до первого кошелька" },
];

function Numbers() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-16 lg:py-20">
        <Eyebrow dash tone="primary">Цифры</Eyebrow>
        <div className="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-px bg-border border border-border">
          {KPIS.map((k) => (
            <div key={k.label} className="bg-card p-6 lg:p-8">
              <Eyebrow>{k.label}</Eyebrow>
              <BigNum size="xl" className="mt-2">{k.value}</BigNum>
              <Mono size="xs" className="mt-2 text-muted-foreground block">{k.sub}</Mono>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FlowSection() {
  return (
    <section className="border-b border-border bg-muted/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-24 grid lg:grid-cols-2 gap-14 items-center">
        <div>
          <Eyebrow dash tone="primary">Как это работает</Eyebrow>
          <h2 className="mt-5 text-[32px] lg:text-[40px] font-medium tracking-[-0.025em] leading-[1.1] text-foreground">
            Транзакция требует согласия команды
          </h2>
          <p className="mt-5 text-[15px] leading-[1.6] text-muted-foreground max-w-lg">
            Любой исходящий перевод нужно подтвердить минимум M из N
            подписантов. Без достаточного количества подписей — транзакция
            не уходит в сеть. Никаких единоличных действий с балансом.
          </p>
          <ol className="mt-7 space-y-3 text-[14px]">
            {[
              "Оператор инициирует исходящую транзакцию",
              "Запрос приходит каждому подписанту в realtime",
              "По достижении порога — broadcast в blockchain",
              "Аудит-лог сохраняет всю историю подписей",
            ].map((step, i) => (
              <li key={i} className="flex gap-3">
                <span className="font-mono text-[11px] text-faint mt-0.5">0{i + 1}</span>
                <span className="text-foreground">{step}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="bg-card border border-border p-8 lg:p-10 self-start">
          <Eyebrow>Поток транзакции</Eyebrow>
          <div className="mt-6 flex justify-center">
            <TxFlow width={420} height={120} threshold="3 / 5" />
          </div>
        </div>
      </div>
    </section>
  );
}

function BottomCTA() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-24">
        <div className="bg-card border-l-4 border-l-primary border-t border-r border-b border-border p-10 lg:p-16 grid lg:grid-cols-[1.4fr_1fr] gap-10 items-center">
          <div>
            <Eyebrow tone="primary">Готовы начать</Eyebrow>
            <h2 className="mt-4 text-[32px] lg:text-[44px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground">
              Подключите ORGON<br />за один разговор
            </h2>
            <p className="mt-4 text-muted-foreground text-[15px] leading-[1.55] max-w-xl">
              Покажем платформу, обсудим интеграцию с вашей системой,
              согласуем условия. Без обязательств.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
              <Button variant="primary" size="lg" fullWidth>
                Запросить демо
                <Icon icon="solar:arrow-right-linear" className="text-[15px]" />
              </Button>
            </a>
            <Link href="/pricing">
              <Button variant="secondary" size="lg" fullWidth>Сравнить тарифы</Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

```

### `frontend/src/app/(public)/features/page.tsx`

```tsx
"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";

interface Feature {
  tag: string;
  icon: string;
  title: string;
  description: string;
  details: string[];
}

const FEATURES: Feature[] = [
  {
    tag: "01 / Кастоди",
    icon: "solar:shield-network-bold",
    title: "Мульти-подписная безопасность",
    description:
      "Требуйте несколько подтверждений на каждую исходящую транзакцию. Настраиваемые пороги M-of-N исключают единую точку отказа.",
    details: [
      "Пороги до 7-of-15",
      "Поддержка аппаратных кошельков (Ledger, Trezor)",
      "Иерархические права и роли",
      "Географически распределённые подписанты",
    ],
  },
  {
    tag: "02 / Расписание",
    icon: "solar:calendar-mark-bold",
    title: "Планирование транзакций",
    description:
      "Регулярные платежи и автоматические переводы. Cron-выражения с пред-проверкой подписей до момента исполнения.",
    details: [
      "Cron-выражения для гибкости",
      "Повторяющиеся платежи",
      "Отложенное исполнение",
      "Автоматическая отмена просроченного",
    ],
  },
  {
    tag: "03 / Аналитика",
    icon: "solar:chart-2-bold",
    title: "Аналитика и метрики",
    description:
      "Отслеживайте балансы, объёмы транзакций и активность подписантов. Экспорт под регулятора и собственная BI.",
    details: [
      "Графики баланса и объёма",
      "Статистика по подписям",
      "Распределение токенов и сетей",
      "Экспорт CSV и JSON",
    ],
  },
  {
    tag: "04 / Адресная книга",
    icon: "solar:book-2-bold",
    title: "Контакты и адреса",
    description:
      "Сохраняйте проверенные адреса контрагентов, помечайте избранное, ведите категории — меньше человеческих ошибок при отправках.",
    details: [
      "Категории и избранное",
      "Поиск по имени и адресу",
      "Проверка checksum перед отправкой",
      "Импорт / экспорт списка",
    ],
  },
  {
    tag: "05 / Аудит",
    icon: "solar:document-text-bold",
    title: "Журнал аудита",
    description:
      "Полная история всех действий: кто, что, когда. Неизменяемый лог под FATF Travel Rule и внутренний контроль.",
    details: [
      "Полный history по каждому ресурсу",
      "Фильтрация по пользователям и действиям",
      "Точные timestamps",
      "Экспорт CSV для регулятора",
    ],
  },
  {
    tag: "06 / Сети",
    icon: "solar:global-bold",
    title: "Поддержка сетей",
    description:
      "Tron, BNB Chain, Ethereum, Polygon, BTC. Кросс-чейн совместимость через Safina Pay интеграцию.",
    details: [
      "Tron (TRC-20, USDT)",
      "EVM-сети: ETH, BSC, Polygon",
      "Bitcoin (BIP-32 кошельки)",
      "Автоматическая комиссия",
    ],
  },
];

export default function FeaturesPage() {
  return (
    <>
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-24 text-center">
          <Eyebrow dash tone="primary" className="!justify-center">Возможности платформы</Eyebrow>
          <h1 className="mt-6 text-[44px] sm:text-[56px] lg:text-[64px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground">
            Всё что нужно<br />для институциональной кастоди
          </h1>
          <p className="mt-6 max-w-2xl mx-auto text-[15px] leading-[1.6] text-muted-foreground">
            Шесть областей, которые мы выстроили под требования бирж, банков и финтех-команд.
          </p>
        </div>
      </section>

      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-12 lg:py-16">
          <div className="space-y-px bg-border border border-border">
            {FEATURES.map((feature, i) => {
              const reversed = i % 2 === 1;
              return (
                <article
                  key={feature.tag}
                  className="bg-card grid lg:grid-cols-2 gap-px"
                >
                  <div className={`p-10 lg:p-14 ${reversed ? "lg:order-2" : ""}`}>
                    <Eyebrow tone="primary">{feature.tag}</Eyebrow>
                    <h2 className="mt-5 text-[28px] sm:text-[32px] font-medium tracking-tight text-foreground">
                      {feature.title}
                    </h2>
                    <p className="mt-4 text-[15px] leading-[1.6] text-muted-foreground">
                      {feature.description}
                    </p>
                    <ul className="mt-6 space-y-2.5">
                      {feature.details.map((d) => (
                        <li key={d} className="flex items-start gap-3 text-[14px]">
                          <Icon icon="solar:check-circle-bold" className="text-success text-[16px] shrink-0 mt-0.5" />
                          <span className="text-foreground">{d}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div
                    className={`p-10 lg:p-14 flex items-center justify-center bg-muted/40 min-h-[280px] ${
                      reversed ? "lg:order-1" : ""
                    }`}
                  >
                    <Icon icon={feature.icon} className="text-[160px] text-foreground/20" />
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="border-b border-border bg-muted/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 text-center">
          <Eyebrow dash tone="primary" className="!justify-center">Готовы попробовать</Eyebrow>
          <h2 className="mt-5 text-[32px] sm:text-[40px] font-medium tracking-[-0.025em] leading-[1.1] text-foreground">
            Покажем платформу за 30 минут
          </h2>
          <p className="mt-4 max-w-xl mx-auto text-[15px] text-muted-foreground leading-[1.6]">
            Демо под ваш кейс — обменник, биржа, банк или fintech.
          </p>
          <div className="mt-8 flex justify-center gap-3 flex-wrap">
            <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
              <Button variant="primary" size="lg">
                Запросить демо
                <Icon icon="solar:arrow-right-linear" className="text-[15px]" />
              </Button>
            </a>
            <Link href="/pricing">
              <Button variant="secondary" size="lg">Смотреть тарифы</Button>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

```

### `frontend/src/app/(public)/pricing/page.tsx`

```tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Eyebrow, BigNum, Mono } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";

interface Plan {
  id: string;
  name: string;
  slug: string;
  description: string;
  monthly_price: string;
  yearly_price: string;
  currency: string;
  features: Record<string, unknown>;
  sort_order: number;
  is_active: boolean;
  margin_min?: string | null;
}

const FEATURE_LABELS: Record<string, string> = {
  max_wallets: "Кошельков",
  max_transactions: "Транзакций / мес",
  tx_commission: "Комиссия за транзакцию",
  crypto_acquiring: "Крипто-эквайринг",
  kyc_price: "KYC за пользователя ($)",
  basic_support: "Базовая поддержка",
  priority_support: "Приоритетная поддержка",
  dedicated_support: "Выделенная поддержка",
  dedicated_manager: "Персональный менеджер",
  api_access: "API доступ",
  white_label: "White-label",
  sla_24_7: "SLA 24/7",
  unlimited_wallets: "Неограниченные кошельки",
  unlimited_transactions: "Неограниченные транзакции",
};

function formatPrice(amount: string, currency: string): string {
  const n = Number(amount);
  if (Number.isNaN(n)) return amount;
  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(n)} ${currency}`;
}

function describeFeature(key: string, value: unknown): string {
  const label = FEATURE_LABELS[key] ?? key;
  if (typeof value === "boolean") return label;
  if (typeof value === "number") return `${label}: ${new Intl.NumberFormat("ru-RU").format(value)}`;
  return `${label}: ${value}`;
}

export default function PricingPage() {
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [billing, setBilling] = useState<"monthly" | "yearly">("monthly");

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/v1/billing/plans`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: Plan[]) => {
        if (cancelled) return;
        const active = (Array.isArray(data) ? data : [])
          .filter((p) => p.is_active)
          .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
        setPlans(active);
      })
      .catch((e) => !cancelled && setError(e.message ?? "Не удалось загрузить тарифы"));
    return () => {
      cancelled = true;
    };
  }, []);

  const yearlySavings = useMemo(() => {
    if (!plans) return null;
    const start = plans.find((p) => p.slug === "start") ?? plans[0];
    if (!start) return null;
    const monthly12 = Number(start.monthly_price) * 12;
    const yearly = Number(start.yearly_price);
    if (!monthly12 || !yearly) return null;
    const pct = Math.round((1 - yearly / monthly12) * 100);
    return pct > 0 ? pct : null;
  }, [plans]);

  return (
    <>
      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 pt-20 pb-12 text-center">
          <Eyebrow dash tone="primary" className="!justify-center">Тарифы</Eyebrow>
          <h1 className="mt-6 text-[44px] sm:text-[56px] lg:text-[64px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground">
            Прозрачные тарифы<br />для команд любого масштаба
          </h1>
          <p className="mt-6 max-w-2xl mx-auto text-[15px] sm:text-[16px] leading-[1.6] text-muted-foreground">
            Цены в KGS. Меняйте план в любой момент. Скидка 10% при годовой
            оплате. Enterprise — индивидуальные условия по договору.
          </p>

          <div className="mt-10 inline-flex border border-strong p-0.5">
            {(["monthly", "yearly"] as const).map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => setBilling(opt)}
                className={cn(
                  "px-6 h-9 text-[13px] font-medium transition-colors flex items-center gap-2",
                  billing === opt ? "bg-foreground text-background" : "text-foreground hover:bg-muted",
                )}
              >
                {opt === "monthly" ? "Помесячно" : "За год"}
                {opt === "yearly" && yearlySavings !== null && (
                  <span className={cn("font-mono text-[10px] tracking-wider", billing === opt ? "text-background" : "text-primary")}>
                    −{yearlySavings}%
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* PLAN GRID */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-14">
          {!plans && !error && (
            <div className="text-center text-muted-foreground py-20">Загрузка тарифов…</div>
          )}
          {error && (
            <div className="mx-auto max-w-md border border-destructive/40 bg-destructive/5 p-6 text-center text-destructive">
              {error}
            </div>
          )}
          {plans && (
            <div className="grid lg:grid-cols-3 gap-px bg-border border border-border">
              {plans.map((plan, i) => {
                const featured = plan.slug === "business";
                const price = billing === "monthly" ? plan.monthly_price : plan.yearly_price;
                const features = Object.entries(plan.features ?? {}).map(([k, v]) => describeFeature(k, v));
                return (
                  <article
                    key={plan.id}
                    className={cn(
                      "p-8 lg:p-10 relative flex flex-col bg-card text-card-foreground",
                      featured && "ring-2 ring-primary -m-px",
                    )}
                  >
                    {featured && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 font-mono text-[10px] tracking-[0.16em] uppercase text-primary-foreground bg-primary px-3 py-1">
                        Популярный
                      </div>
                    )}
                    <div className="font-mono text-[11px] tracking-[0.12em] uppercase text-primary">
                      0{i + 1} / {plan.name.toUpperCase()}
                    </div>
                    <h2 className="mt-6 text-[32px] font-medium tracking-[-0.02em] text-foreground">
                      {plan.name}
                    </h2>
                    <p className="mt-2 text-[13px] leading-[1.5] text-muted-foreground">
                      {plan.description}
                    </p>

                    <div className="mt-7">
                      <div className="flex items-baseline gap-2">
                        <BigNum size="xxl" className="text-foreground">
                          {new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(Number(price))}
                        </BigNum>
                        <span className="font-mono text-[12px] text-muted-foreground">
                          {plan.currency}
                        </span>
                      </div>
                      <Mono size="sm" className="mt-1 block text-muted-foreground">
                        {billing === "monthly" ? "/ месяц" : "/ год"}
                        {plan.margin_min ? ` · комиссия от ${plan.margin_min}%` : ""}
                      </Mono>
                    </div>

                    {plan.slug === "enterprise" ? (
                      <a
                        href="mailto:sales@orgon.asystem.kg?subject=ORGON%20Enterprise%20enquiry"
                        className="mt-8"
                      >
                        <Button variant="primary" fullWidth size="md">
                          Связаться с продажами
                          <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
                        </Button>
                      </a>
                    ) : (
                      <Link href="/register" className="mt-8">
                        <Button variant={featured ? "primary" : "secondary"} fullWidth size="md">
                          Выбрать план
                          <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
                        </Button>
                      </Link>
                    )}

                    <ul className="mt-8 pt-7 border-t border-border space-y-3">
                      {features.length === 0 && (
                        <li className="text-[13px] text-muted-foreground">
                          Свяжитесь с нами для подробностей
                        </li>
                      )}
                      {features.map((f) => (
                        <li key={f} className="flex items-start gap-2.5">
                          <Icon
                            icon="solar:check-circle-bold"
                            className="text-[16px] shrink-0 mt-0.5 text-success"
                          />
                          <span className="text-[13px] leading-[1.5] text-foreground">
                            {f}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* CTA */}
      <section className="border-b border-border bg-muted/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 text-center">
          <Eyebrow dash tone="primary" className="!justify-center">Не уверены</Eyebrow>
          <h2 className="mt-5 text-[28px] sm:text-[36px] font-medium tracking-[-0.025em] leading-[1.1] text-foreground">
            Подберём план под ваши объёмы
          </h2>
          <p className="mt-4 max-w-xl mx-auto text-[15px] text-muted-foreground leading-[1.6]">
            Расскажите про ваш кейс — биржа, обменник, банк или fintech — и
            покажем, как ORGON встраивается в вашу инфраструктуру.
          </p>
          <a
            href="mailto:sales@orgon.asystem.kg?subject=ORGON%20pricing%20enquiry"
            className="inline-block mt-8"
          >
            <Button variant="primary" size="lg">
              <Icon icon="solar:letter-bold" className="text-[16px]" />
              Написать в продажи
            </Button>
          </a>
        </div>
      </section>
    </>
  );
}

```

### `frontend/src/app/(public)/about/page.tsx`

```tsx
"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Eyebrow, BigNum } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";

const VALUES = [
  {
    icon: "solar:shield-check-bold",
    title: "Безопасность прежде всего",
    desc: "Мульти-подпись, аппаратные ключи и полный аудит. Никаких компромиссов в защите средств клиента.",
  },
  {
    icon: "solar:eye-bold",
    title: "Прозрачность",
    desc: "Каждое действие логируется и доступно для проверки. История подписей не редактируется.",
  },
  {
    icon: "solar:user-check-bold",
    title: "Простота",
    desc: "Сложные функции не должны быть сложными в использовании. Интерфейс под профессионалов.",
  },
  {
    icon: "solar:rocket-2-bold",
    title: "Развитие",
    desc: "Постоянное улучшение на основе обратной связи от партнёров — бирж, банков, регуляторов.",
  },
];

const TIMELINE = [
  { year: "2024", event: "Основание ASYSTEM", desc: "Запуск технологической компании в Бишкеке" },
  { year: "2025", event: "Разработка ORGON", desc: "Закрытое тестирование с пилотными партнёрами" },
  { year: "2026", event: "Production launch", desc: "Выход платформы на рынок Центральной Азии" },
];

export default function AboutPage() {
  return (
    <>
      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-28 grid lg:grid-cols-[1.2fr_0.8fr] gap-12 items-end">
          <div>
            <Eyebrow dash tone="primary">О компании</Eyebrow>
            <h1 className="mt-6 text-[44px] sm:text-[56px] lg:text-[64px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground">
              Институциональная<br />криптоинфраструктура<br />в Центральной Азии
            </h1>
          </div>
          <p className="text-[15px] leading-[1.7] text-muted-foreground">
            ORGON — продукт компании ASYSTEM из Бишкека. Мы строим
            инфраструктуру, которая позволяет биржам, брокерам и банкам
            работать с криптоактивами под институциональным контролем —
            без компромиссов в безопасности и без прихоти регуляторики.
          </p>
        </div>
      </section>

      {/* VALUES */}
      <section className="border-b border-border bg-muted/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20">
          <Eyebrow dash tone="primary">Принципы</Eyebrow>
          <h2 className="mt-5 text-[36px] lg:text-[44px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground max-w-2xl">
            Четыре принципа, на которых строим продукт
          </h2>

          <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-px bg-border border border-border">
            {VALUES.map((v) => (
              <div key={v.title} className="bg-card p-7 lg:p-8">
                <Icon icon={v.icon} className="text-[28px] text-primary" />
                <h3 className="mt-5 text-[16px] font-medium tracking-tight text-foreground">{v.title}</h3>
                <p className="mt-2 text-[13px] leading-[1.55] text-muted-foreground">{v.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TIMELINE */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20">
          <Eyebrow dash tone="primary">Хронология</Eyebrow>
          <h2 className="mt-5 text-[32px] lg:text-[40px] font-medium tracking-[-0.025em] leading-[1.1] text-foreground">
            От идеи до институционального продукта
          </h2>

          <div className="mt-14 grid md:grid-cols-3 gap-px bg-border border border-border">
            {TIMELINE.map((t) => (
              <div key={t.year} className="bg-card p-8">
                <BigNum size="xl" className="text-primary">{t.year}</BigNum>
                <div className="mt-4 text-[16px] font-medium tracking-tight text-foreground">{t.event}</div>
                <p className="mt-1 text-[13px] text-muted-foreground leading-[1.55]">{t.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CONTACT CTA */}
      <section className="border-b border-border bg-muted/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 grid md:grid-cols-2 gap-12 items-center">
          <div>
            <Eyebrow dash tone="primary">Контакты</Eyebrow>
            <h2 className="mt-5 text-[28px] sm:text-[36px] font-medium tracking-[-0.025em] leading-[1.1] text-foreground">
              Свяжитесь с нами напрямую
            </h2>
            <ul className="mt-6 space-y-3 text-[14px]">
              <li className="flex items-center gap-3">
                <Icon icon="solar:letter-bold" className="text-[18px] text-primary" />
                <a href="mailto:sales@orgon.asystem.kg" className="text-foreground hover:text-primary">
                  sales@orgon.asystem.kg
                </a>
              </li>
              <li className="flex items-center gap-3">
                <Icon icon="solar:map-point-bold" className="text-[18px] text-primary" />
                <span className="text-foreground">Бишкек, Кыргызстан</span>
              </li>
              <li className="flex items-center gap-3">
                <Icon icon="solar:global-bold" className="text-[18px] text-primary" />
                <a
                  href="https://asystem.ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-foreground hover:text-primary"
                >
                  asystem.ai
                </a>
              </li>
            </ul>
          </div>
          <div className="flex flex-col gap-3">
            <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
              <Button variant="primary" size="lg" fullWidth>
                Запросить демо
                <Icon icon="solar:arrow-right-linear" className="text-[15px]" />
              </Button>
            </a>
            <Link href="/pricing">
              <Button variant="secondary" size="lg" fullWidth>Смотреть тарифы</Button>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

```

### `frontend/src/app/(public)/login/page.tsx`

```tsx
"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "@/hooks/useTranslations";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Eyebrow, Mono } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { Icon } from "@/lib/icons";

const DEMO_ACCOUNTS = [
  { email: "demo-admin@orgon.io",  role: "Admin",  blurb: "полный доступ",        icon: "solar:shield-user-bold" },
  { email: "demo-signer@orgon.io", role: "Signer", blurb: "подписание транзакций", icon: "solar:pen-new-square-bold" },
  { email: "demo-viewer@orgon.io", role: "Viewer", blurb: "только просмотр",       icon: "solar:eye-bold" },
];

const DEMO_PASSWORD = "demo2026";

export default function LoginPage() {
  const t = useTranslations("auth.login");
  const t2fa = useTranslations("settings.twofa");
  const tc = useTranslations("common");
  const router = useRouter();
  const { login: authLogin } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [twoFACode, setTwoFACode] = useState("");
  const [step, setStep] = useState<"credentials" | "2fa">("credentials");
  const [tempToken, setTempToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function performLogin(emailValue: string, passwordValue: string) {
    setError("");
    setLoading(true);
    try {
      const response = await api.login(emailValue, passwordValue);
      if (response.requires_2fa) {
        setTempToken(response.temp_token);
        setStep("2fa");
        setLoading(false);
        return;
      }
      await authLogin(response);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Login failed. Please check your credentials.");
      setLoading(false);
    }
  }

  function handleCredentialsSubmit(e: FormEvent) {
    e.preventDefault();
    performLogin(email, password);
  }

  function handleQuickLogin(quickEmail: string) {
    setEmail(quickEmail);
    setPassword(DEMO_PASSWORD);
    performLogin(quickEmail, DEMO_PASSWORD);
  }

  async function handle2FASubmit(e: FormEvent) {
    e.preventDefault();
    if (twoFACode.length !== 6) {
      setError(t2fa("errors.invalidCode"));
      return;
    }
    setError("");
    setLoading(true);
    try {
      const response = await api.verify2FA(tempToken, twoFACode);
      await authLogin(response);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || t2fa("errors.verificationFailed"));
      setTwoFACode("");
      setLoading(false);
    }
  }

  function handleBackToCredentials() {
    setStep("credentials");
    setTempToken("");
    setTwoFACode("");
    setError("");
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      {/* LEFT — light brand panel, paper */}
      <aside className="hidden lg:flex flex-col justify-between bg-muted border-r border-border p-14 relative overflow-hidden">
        <Link href="/" className="inline-flex items-center gap-3 relative z-10 text-foreground">
          <Image src="/orgon-icon.png" alt="ORGON" width={36} height={36} priority />
          <div className="flex flex-col leading-tight">
            <span className="font-mono text-[10px] tracking-[0.18em] text-faint">ASYSTEM</span>
            <span className="font-medium text-[16px] tracking-[0.06em] text-foreground">ORGON</span>
          </div>
        </Link>

        {/* Decorative concentric ring (crimson, low-opacity) */}
        <svg
          width={460}
          height={460}
          viewBox="0 0 460 460"
          className="absolute -top-20 -right-32 pointer-events-none"
          aria-hidden="true"
        >
          <circle cx={230} cy={230} r={220} fill="none" stroke="var(--primary)" strokeWidth={1.2} opacity={0.10} />
          <circle cx={230} cy={230} r={155} fill="none" stroke="var(--primary)" strokeWidth={1.2} opacity={0.12} />
          <circle cx={230} cy={230} r={95}  fill="none" stroke="var(--primary)" strokeWidth={1.2} opacity={0.16} />
          <circle cx={230} cy={230} r={35}  fill="var(--primary)" opacity={0.10} />
        </svg>

        <div className="relative z-10 max-w-lg">
          <Eyebrow tone="primary" dash>Институциональное кастоди</Eyebrow>
          <h2 className="mt-5 text-[40px] xl:text-[48px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground">
            «Деньги в надёжных руках. Всегда — вместе.»
          </h2>
          <Mono size="md" className="mt-5 block text-muted-foreground">
            ASYSTEM · ORGON · институциональная мульти-подписная кастоди
          </Mono>
        </div>

        <div className="relative z-10 grid grid-cols-3 gap-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint">
          <div>M-of-N подписи</div>
          <div>FATF Travel Rule</div>
          <div>White-label API</div>
        </div>
      </aside>

      {/* RIGHT — auth card */}
      <main className="flex flex-col justify-center px-6 py-12 sm:px-10 lg:px-16">
        <div className="lg:hidden mb-8">
          <Link href="/" className="inline-flex items-center gap-3 text-foreground">
            <Image src="/orgon-icon.png" alt="ORGON" width={32} height={32} priority />
            <span className="font-medium text-[15px] tracking-[0.06em]">ORGON</span>
          </Link>
        </div>

        {step === "credentials" && (
          <div className="max-w-[420px] w-full">
            <h1 className="text-[28px] font-medium tracking-[-0.02em] text-foreground">
              {t("title")}
            </h1>
            <p className="mt-2 text-[14px] text-muted-foreground">{t("subtitle")}</p>

            <form onSubmit={handleCredentialsSubmit} className="mt-8 space-y-5">
              {error && (
                <div className="p-3 border border-destructive/40 bg-destructive/5 text-[13px] text-destructive">
                  {error}
                </div>
              )}

              <Input
                type="email"
                label={t("emailLabel")}
                placeholder={t("emailPlaceholder")}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                autoFocus
                mono
              />

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="eyebrow">{t("passwordLabel")}</label>
                  <Link href="/forgot-password" className="text-[11px] font-mono tracking-[0.04em] text-primary hover:underline">
                    {t("forgotPassword")}
                  </Link>
                </div>
                <input
                  type="password"
                  placeholder="● ● ● ● ● ● ● ●"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="block w-full h-10 px-3 py-2 bg-card text-foreground placeholder:text-faint border border-border focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 font-mono text-[13px]"
                />
              </div>

              <Button type="submit" loading={loading} fullWidth size="md">
                {t("signInButton")}
                <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
              </Button>
            </form>

            <div className="mt-6 text-[13px] text-muted-foreground">
              {t("noAccount")}{" "}
              <Link href="/register" className="text-primary hover:underline font-medium">
                {t("signUpLink")}
              </Link>
            </div>

            {/* Demo accounts */}
            <div className="mt-10 pt-8 border-t border-border">
              <Eyebrow>{t("quickLoginTitle")}</Eyebrow>
              <ul className="mt-4 space-y-2">
                {DEMO_ACCOUNTS.map((d) => (
                  <li key={d.email}>
                    <button
                      type="button"
                      disabled={loading}
                      onClick={() => handleQuickLogin(d.email)}
                      className="w-full flex items-center justify-between gap-3 px-4 py-3 bg-card border border-border text-left hover:border-strong transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <Icon icon={d.icon} className="text-[18px] text-primary shrink-0" />
                        <div className="min-w-0">
                          <div className="text-[13px] font-medium text-foreground truncate">
                            {d.role} · {d.blurb}
                          </div>
                          <Mono size="xs" className="text-muted-foreground truncate block">{d.email}</Mono>
                        </div>
                      </div>
                      <Icon icon="solar:arrow-right-linear" className="text-[14px] text-faint shrink-0" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {step === "2fa" && (
          <div className="max-w-[420px] w-full">
            <Icon icon="solar:shield-check-bold" className="text-[40px] text-primary" />
            <h1 className="mt-4 text-[28px] font-medium tracking-[-0.02em] text-foreground">
              {t2fa("verificationCode")}
            </h1>
            <p className="mt-2 text-[14px] text-muted-foreground">{t2fa("enterCode")}</p>

            <form onSubmit={handle2FASubmit} className="mt-8 space-y-5">
              {error && (
                <div className="p-3 border border-destructive/40 bg-destructive/5 text-[13px] text-destructive">
                  {error}
                </div>
              )}

              <Input
                type="text"
                label={t2fa("verificationCode")}
                placeholder="000000"
                value={twoFACode}
                onChange={(e) => setTwoFACode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                maxLength={6}
                required
                autoFocus
                mono
              />

              <div className="flex gap-3">
                <Button type="button" variant="secondary" onClick={handleBackToCredentials} fullWidth>
                  <Icon icon="solar:arrow-left-linear" className="text-[14px]" />
                  {tc("back")}
                </Button>
                <Button type="submit" loading={loading} disabled={twoFACode.length !== 6} fullWidth>
                  {t2fa("verify")}
                </Button>
              </div>
            </form>

            <div className="mt-8 p-4 bg-muted text-[12px] text-muted-foreground whitespace-pre-line">
              {t2fa("backupCodeHelp")}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

```

### `frontend/src/app/(public)/register/page.tsx`

```tsx
"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "@/hooks/useTranslations";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Eyebrow } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";

const ROLES = [
  { value: "viewer", icon: "solar:eye-bold",          desc: "Просмотр данных без права действия" },
  { value: "signer", icon: "solar:pen-new-square-bold", desc: "Подписание транзакций" },
  { value: "admin",  icon: "solar:shield-user-bold",  desc: "Полный доступ к управлению" },
];

export default function RegisterPage() {
  const t = useTranslations("auth.register");
  const router = useRouter();
  const { register } = useAuth();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    fullName: "",
    role: "viewer",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (formData.password !== formData.confirmPassword) {
      setError(t("errors.passwordMismatch"));
      return;
    }
    if (formData.password.length < 8) {
      setError(t("errors.passwordTooShort"));
      return;
    }

    setLoading(true);
    try {
      await register(formData.email, formData.password, formData.fullName, formData.role);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || t("errors.emailExists"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      {/* LEFT — light brand panel */}
      <aside className="hidden lg:flex flex-col justify-between bg-muted border-r border-border p-14 relative overflow-hidden">
        <Link href="/" className="inline-flex items-center gap-3 relative z-10 text-foreground">
          <Image src="/orgon-icon.png" alt="ORGON" width={36} height={36} priority />
          <div className="flex flex-col leading-tight">
            <span className="font-mono text-[10px] tracking-[0.18em] text-faint">ASYSTEM</span>
            <span className="font-medium text-[16px] tracking-[0.06em] text-foreground">ORGON</span>
          </div>
        </Link>

        <div className="relative z-10 max-w-lg">
          <Eyebrow tone="primary" dash>Создание аккаунта</Eyebrow>
          <h2 className="mt-5 text-[40px] xl:text-[44px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground">
            Подключитесь к ORGON
          </h2>
          <p className="mt-4 text-muted-foreground text-[15px] leading-[1.55]">
            После регистрации сможете создать первую организацию и пригласить
            подписантов. Полный доступ к B2B API сразу после KYB-верификации.
          </p>
        </div>

        <ul className="relative z-10 space-y-2 text-[12px] font-mono tracking-[0.04em] text-faint">
          <li>· Multi-signature M-of-N до 7-of-15</li>
          <li>· White-label под собственный домен</li>
          <li>· FATF-совместимый аудит-лог</li>
        </ul>
      </aside>

      {/* RIGHT — form */}
      <main className="flex flex-col justify-center px-6 py-12 sm:px-10 lg:px-16">
        <div className="lg:hidden mb-8">
          <Link href="/" className="inline-flex items-center gap-3 text-foreground">
            <Image src="/orgon-icon.png" alt="ORGON" width={32} height={32} priority />
            <span className="font-medium text-[15px] tracking-[0.06em]">ORGON</span>
          </Link>
        </div>

        <div className="max-w-[480px] w-full">
          <h1 className="text-[28px] font-medium tracking-[-0.02em] text-foreground">
            {t("title")}
          </h1>
          <p className="mt-2 text-[14px] text-muted-foreground">{t("subtitle")}</p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {error && (
              <div className="p-3 border border-destructive/40 bg-destructive/5 text-[13px] text-destructive">
                {error}
              </div>
            )}

            <Input
              type="text"
              label={t("fullNameLabel")}
              placeholder={t("fullNamePlaceholder")}
              value={formData.fullName}
              onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
              required
              autoFocus
            />

            <Input
              type="email"
              label={t("emailLabel")}
              placeholder={t("emailPlaceholder")}
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              autoComplete="email"
              mono
            />

            <Input
              type="password"
              label={t("passwordLabel")}
              placeholder={t("passwordPlaceholder")}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
              autoComplete="new-password"
              helperText="Минимум 8 символов"
              mono
            />

            <Input
              type="password"
              label={t("confirmPasswordLabel")}
              placeholder={t("confirmPasswordPlaceholder")}
              value={formData.confirmPassword}
              onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
              required
              autoComplete="new-password"
              mono
            />

            <div>
              <div className="eyebrow mb-2">{t("roleLabel")}</div>
              <div className="grid grid-cols-3 gap-px bg-border border border-border">
                {ROLES.map((r) => {
                  const selected = formData.role === r.value;
                  return (
                    <button
                      key={r.value}
                      type="button"
                      onClick={() => setFormData({ ...formData, role: r.value })}
                      className={cn(
                        "p-4 flex flex-col items-start gap-2 text-left transition-colors",
                        selected ? "bg-primary text-primary-foreground" : "bg-card hover:bg-muted",
                      )}
                    >
                      <Icon icon={r.icon} className="text-[20px]" />
                      <div>
                        <div className="text-[12px] font-medium uppercase tracking-[0.05em]">
                          {t(`roles.${r.value}`)}
                        </div>
                        <div
                          className={cn(
                            "mt-1 text-[11px] leading-[1.4]",
                            selected ? "text-primary-foreground/85" : "text-muted-foreground",
                          )}
                        >
                          {r.desc}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <label className="flex items-start gap-3 text-[12px] text-muted-foreground">
              <input
                type="checkbox"
                required
                className="mt-0.5 accent-primary"
              />
              <span>
                {t("termsAgree")}{" "}
                <Link href="/terms" className="text-primary hover:underline">
                  {t("termsOfService")}
                </Link>
                {" "}{t("and")}{" "}
                <Link href="/privacy" className="text-primary hover:underline">
                  {t("privacyPolicy")}
                </Link>
              </span>
            </label>

            <Button type="submit" loading={loading} fullWidth size="md">
              {t("createButton")}
              <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
            </Button>
          </form>

          <div className="mt-6 text-[13px] text-muted-foreground">
            {t("alreadyHaveAccount")}{" "}
            <Link href="/login" className="text-primary hover:underline font-medium">
              {t("signInLink")}
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}

```

### `frontend/src/app/(public)/forgot-password/page.tsx`

```tsx
"use client";

import { useState, FormEvent } from "react";
import { useTranslations } from "@/hooks/useTranslations";
import Link from "next/link";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";

export default function ForgotPasswordPage() {
  const t = useTranslations("auth.forgotPassword");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || t("errors.serverError"));
      }
      setSent(true);
    } catch (err: any) {
      setError(err.message || t("errors.serverError"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md border border-border bg-card p-8 sm:p-10">
        <Eyebrow dash tone="primary">Восстановление доступа</Eyebrow>
        <h1 className="mt-5 text-[28px] font-medium tracking-[-0.02em] text-foreground">
          {t("title")}
        </h1>
        <p className="mt-2 text-[14px] text-muted-foreground">{t("subtitle")}</p>

        {sent ? (
          <div className="mt-8 space-y-6">
            <div className="p-4 border border-success/40 bg-success/5 text-[13px] text-success">
              <Icon icon="solar:check-circle-bold" className="text-[18px] inline-block mr-2" />
              {t("success")}
            </div>
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 text-[13px] text-primary hover:underline font-medium"
            >
              <Icon icon="solar:arrow-left-linear" className="text-[14px]" />
              {t("backToLogin")}
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {error && (
              <div className="p-3 border border-destructive/40 bg-destructive/5 text-[13px] text-destructive">
                {error}
              </div>
            )}

            <Input
              type="email"
              label={t("emailLabel")}
              placeholder={t("emailPlaceholder")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              autoComplete="email"
              mono
            />

            <Button type="submit" loading={loading} fullWidth size="md">
              {t("submitButton")}
              <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
            </Button>

            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground"
            >
              <Icon icon="solar:arrow-left-linear" className="text-[14px]" />
              {t("backToLogin")}
            </Link>
          </form>
        )}
      </div>
    </div>
  );
}

```

### `frontend/src/app/(public)/reset-password/page.tsx`

```tsx
"use client";

import { useState, FormEvent, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "@/hooks/useTranslations";
import Link from "next/link";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";

function ResetPasswordForm() {
  const t = useTranslations("auth.resetPassword");
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 8) return setError(t("errors.passwordTooShort"));
    if (password !== confirmPassword) return setError(t("errors.passwordMismatch"));
    if (!token) return setError(t("errors.invalidToken"));

    setLoading(true);
    try {
      const res = await fetch("/api/auth/reset-password/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || t("errors.serverError"));
      }
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || t("errors.serverError"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md border border-border bg-card p-8 sm:p-10">
        <Eyebrow dash tone="primary">Новый пароль</Eyebrow>
        <h1 className="mt-5 text-[28px] font-medium tracking-[-0.02em] text-foreground">
          {t("title")}
        </h1>
        <p className="mt-2 text-[14px] text-muted-foreground">{t("subtitle")}</p>

        {success ? (
          <div className="mt-8 space-y-6">
            <div className="p-4 border border-success/40 bg-success/5 text-[13px] text-success">
              <Icon icon="solar:check-circle-bold" className="text-[18px] inline-block mr-2" />
              {t("success")}
            </div>
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 text-[13px] text-primary hover:underline font-medium"
            >
              <Icon icon="solar:arrow-left-linear" className="text-[14px]" />
              Войти
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {error && (
              <div className="p-3 border border-destructive/40 bg-destructive/5 text-[13px] text-destructive">
                {error}
              </div>
            )}
            {!token && !error && (
              <div className="p-3 border border-warning/40 bg-warning/5 text-[13px] text-warning">
                {t("errors.invalidToken")}
              </div>
            )}

            <Input
              type="password"
              label={t("passwordLabel")}
              placeholder={t("passwordPlaceholder")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoFocus
              autoComplete="new-password"
              mono
              helperText="Минимум 8 символов"
            />

            <Input
              type="password"
              label={t("confirmPasswordLabel")}
              placeholder={t("confirmPasswordPlaceholder")}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
              mono
            />

            <Button type="submit" loading={loading} disabled={!token} fullWidth size="md">
              {t("submitButton")}
              <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="font-mono text-[12px] text-faint">Загрузка…</div>
        </div>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}

```


# 5. Authenticated core pages

### `frontend/src/app/(authenticated)/layout.tsx`

```tsx
import { AppShell } from '../AppShell';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { WebSocketProvider } from '@/contexts/WebSocketContext';

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <WebSocketProvider><AppShell><ErrorBoundary>{children}</ErrorBoundary></AppShell></WebSocketProvider>;
}

```

### `frontend/src/app/(authenticated)/dashboard/page.tsx`

```tsx
"use client";

import useSWR from "swr";
import { useEffect } from "react";
import Link from "next/link";
import { useTranslations } from "@/hooks/useTranslations";
import { Header } from "@/components/layout/Header";
import { Eyebrow, BigNum, Mono, StatusPill } from "@/components/ui/primitives";
import { Sparkline } from "@/components/ui/Sparkline";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { useWebSocket } from "@/contexts/WebSocketContext";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";

interface Stats {
  total_wallets?: number;
  total_balance_usd?: string | number;
  transactions_24h?: number;
  pending_signatures?: number;
  networks_active?: number;
  last_sync?: string | null;
}

interface RecentItem {
  id?: number | string;
  tx_unid?: string;
  tx_hash?: string | null;
  wallet_name?: string;
  status?: string;
  amount_decimal?: string | number;
  value?: string | number;
  token?: string | null;
  to_address?: string;
  to_addr?: string;
  network?: number | string;
  created_at?: string;
  info?: string;
}

interface AlertItem {
  id?: number | string;
  severity?: "high" | "medium" | "low" | string;
  title?: string;
  message?: string;
  created_at?: string;
}

const STATUS_TO_KIND: Record<string, "confirmed" | "pending" | "sent" | "rejected"> = {
  confirmed: "confirmed",
  pending: "pending",
  sent: "sent",
  rejected: "rejected",
};

function formatTime(iso?: string): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
  } catch {
    return iso.slice(11, 16);
  }
}

function formatNumber(n?: string | number, fractionDigits = 0): string {
  const v = typeof n === "string" ? Number(n) : n ?? 0;
  if (Number.isNaN(v)) return "—";
  return new Intl.NumberFormat("ru-RU", { minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits }).format(v);
}

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const { lastEvent } = useWebSocket();

  const { data: stats, error: statsError, mutate: mutateStats } = useSWR<Stats>(
    "/api/dashboard/stats",
    api.getDashboardStats,
    { refreshInterval: 30000 },
  );
  const { data: recent, mutate: mutateRecent } = useSWR<RecentItem[]>(
    "/api/dashboard/recent",
    () => api.getDashboardRecent(20),
    { refreshInterval: 30000 },
  );
  const { data: alerts, mutate: mutateAlerts } = useSWR<AlertItem[]>(
    "/api/dashboard/alerts",
    api.getDashboardAlerts,
    { refreshInterval: 60000 },
  );

  useEffect(() => {
    if (!lastEvent) return;
    const t = lastEvent.type as string;
    if (
      t === "transaction.created" ||
      t === "transaction.confirmed" ||
      t === "transaction.failed" ||
      t === "balance.updated" ||
      t === "wallet.created" ||
      t === "sync.completed"
    ) {
      mutateStats();
      mutateRecent();
      mutateAlerts();
    }
  }, [lastEvent, mutateStats, mutateRecent, mutateAlerts]);

  const recentList: RecentItem[] = Array.isArray(recent) ? recent : [];
  const alertList: AlertItem[] = Array.isArray(alerts) ? alerts : [];
  const balanceUsd = stats?.total_balance_usd ?? "0.00";

  return (
    <>
      <Header title={t("title")} />

      <div className="px-4 sm:px-6 lg:px-10 py-8 space-y-8">
        {statsError && (
          <div className="border border-destructive/40 bg-destructive/5 p-4 text-[13px] text-destructive">
            Не удалось загрузить данные. Повторите позже.
          </div>
        )}

        {/* KPI grid */}
        <section>
          <Eyebrow dash>Сводка</Eyebrow>
          <div className="mt-4 grid grid-cols-2 lg:grid-cols-5 gap-px bg-border border border-border">
            <KpiTile label="Общий баланс" value={`$ ${formatNumber(balanceUsd, 2)}`} sub="USD эквивалент" big />
            <KpiTile label="Кошельки" value={String(stats?.total_wallets ?? "—")} sub="всего" />
            <KpiTile label="Транзакции, 24ч" value={String(stats?.transactions_24h ?? "—")} sub="за последние 24 часа" />
            <KpiTile label="Ожидают подписи" value={String(stats?.pending_signatures ?? "—")} sub="требуют действия" accent />
            <KpiTile label="Сети" value={String(stats?.networks_active ?? "—")} sub="активные" />
          </div>
        </section>

        {/* Two-column: recent activity (wide) + sparkline & alerts (narrow) */}
        <section className="grid lg:grid-cols-[1.6fr_1fr] gap-6">
          {/* Recent transactions */}
          <div className="border border-border bg-card">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div>
                <Eyebrow>Последние транзакции</Eyebrow>
                <h3 className="mt-1 text-[14px] font-medium tracking-tight text-foreground">
                  {recentList.length > 0 ? `${recentList.length} записей` : "—"}
                </h3>
              </div>
              <Link href="/transactions">
                <Button variant="ghost" size="sm">
                  Все транзакции
                  <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
                </Button>
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-[12px] border-collapse">
                <thead>
                  <tr className="text-left">
                    <th className="px-5 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Статус</th>
                    <th className="px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Кошелёк</th>
                    <th className="px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal text-right">Сумма</th>
                    <th className="px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Получатель</th>
                    <th className="px-5 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal text-right">Время</th>
                  </tr>
                </thead>
                <tbody>
                  {recentList.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-5 py-12 text-center text-[13px] text-muted-foreground">
                        Транзакций пока нет
                      </td>
                    </tr>
                  ) : (
                    recentList.slice(0, 8).map((tx, i) => {
                      const kind = STATUS_TO_KIND[(tx.status ?? "").toLowerCase()] ?? "neutral";
                      const amount = tx.amount_decimal ?? tx.value ?? "—";
                      const dest = tx.to_address || tx.to_addr || "—";
                      return (
                        <tr key={tx.tx_unid ?? tx.id ?? i} className="border-t border-border hover:bg-muted/40">
                          <td className="px-5 py-3"><StatusPill kind={kind as any} label={tx.status ?? "—"} /></td>
                          <td className="px-3 py-3 text-foreground">
                            <Mono truncate startChars={8} endChars={4}>{tx.wallet_name ?? "—"}</Mono>
                          </td>
                          <td className="px-3 py-3 text-right tabular text-foreground">
                            {String(amount)}{" "}
                            <span className="text-muted-foreground">{tx.token ?? ""}</span>
                          </td>
                          <td className="px-3 py-3"><Mono truncate>{dest}</Mono></td>
                          <td className="px-5 py-3 text-right"><Mono size="xs" className="text-faint">{formatTime(tx.created_at)}</Mono></td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right column */}
          <div className="space-y-6">
            <div className="border border-border bg-card p-5">
              <Eyebrow>Баланс · 30Д</Eyebrow>
              <BigNum size="xl" className="mt-2">$ {formatNumber(balanceUsd, 0)}</BigNum>
              <Mono size="xs" className="mt-1 text-muted-foreground block">Авто-обновление каждые 30с</Mono>
              <div className="mt-4 text-primary">
                <Sparkline points={[6, 7, 5, 8, 7, 9, 8, 10, 9, 11, 10, 12, 11, 13, 12, 14, 13, 15]} width={300} height={64} />
              </div>
            </div>

            <div className="border border-border bg-card">
              <div className="px-5 py-4 border-b border-border flex items-center justify-between">
                <Eyebrow>Уведомления</Eyebrow>
                <Mono size="xs" className="text-faint">{alertList.length}</Mono>
              </div>
              <ul>
                {alertList.length === 0 ? (
                  <li className="px-5 py-8 text-center text-[13px] text-muted-foreground">Уведомлений нет</li>
                ) : (
                  alertList.slice(0, 4).map((a, i) => (
                    <li key={a.id ?? i} className={cn("flex items-start gap-3 px-5 py-3", i > 0 && "border-t border-border")}>
                      <span
                        className={cn(
                          "inline-block w-1.5 h-1.5 rounded-full mt-1.5 shrink-0",
                          a.severity === "high" ? "bg-destructive" : a.severity === "medium" ? "bg-warning" : "bg-faint",
                        )}
                      />
                      <div className="min-w-0">
                        <div className="text-[13px] text-foreground">{a.title ?? a.message ?? "—"}</div>
                        {a.message && a.title && (
                          <div className="text-[12px] text-muted-foreground mt-0.5">{a.message}</div>
                        )}
                      </div>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </div>
        </section>

        {/* Sync status footer */}
        {stats?.last_sync && (
          <div className="flex justify-end">
            <Mono size="xs" className="text-faint">
              Последняя синхронизация · {new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(stats.last_sync))}
            </Mono>
          </div>
        )}
      </div>
    </>
  );
}

function KpiTile({
  label,
  value,
  sub,
  big = false,
  accent = false,
}: {
  label: string;
  value: string;
  sub?: string;
  big?: boolean;
  accent?: boolean;
}) {
  return (
    <div className="bg-card p-5 lg:p-6">
      <Eyebrow>{label}</Eyebrow>
      <BigNum size={big ? "xl" : "lg"} className={cn("mt-2", accent && "text-primary")}>{value}</BigNum>
      {sub && <Mono size="xs" className="mt-2 text-muted-foreground block">{sub}</Mono>}
    </div>
  );
}

```

### `frontend/src/app/(authenticated)/wallets/page.tsx`

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "@/hooks/useTranslations";
import { Header } from "@/components/layout/Header";
import { Eyebrow, BigNum, Mono } from "@/components/ui/primitives";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/lib/icons";
import { api, API_BASE } from "@/lib/api";

interface Wallet {
  id?: number;
  name?: string;
  label?: string | null;
  network?: number;
  my_unid?: string;
  is_favorite?: boolean;
  addr?: string;
  organization_id?: string | null;
  wallet_type?: number;
  token_short_names?: string;
  created_at?: string;
}

const NETWORK_LABEL: Record<number, string> = {
  5000: "BSC",
  5010: "TRX",
  5020: "ETH",
  5030: "POL",
  5040: "BTC",
};

function networkLabel(n?: number): string {
  if (!n) return "—";
  return NETWORK_LABEL[n] ?? `NET-${n}`;
}

export default function WalletsPage() {
  const t = useTranslations("wallets");
  const router = useRouter();
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    api
      .getWallets()
      .then((data) => setWallets(Array.isArray(data) ? data : []))
      .catch((err) => setError(err.message ?? "Не удалось загрузить кошельки"))
      .finally(() => setLoading(false));
  }, []);

  function handleExport() {
    setExporting(true);
    try {
      window.open(`${API_BASE}/export/wallets/csv`, "_blank");
    } finally {
      setTimeout(() => setExporting(false), 600);
    }
  }

  const totalCount = wallets.length;
  const favCount = wallets.filter((w) => w.is_favorite).length;

  return (
    <>
      <Header title={t("title")} />

      <div className="px-4 sm:px-6 lg:px-10 py-8 space-y-6">
        {/* Top bar */}
        <div className="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <Eyebrow dash>Кошельки</Eyebrow>
            <h2 className="mt-2 text-[24px] sm:text-[28px] font-medium tracking-[-0.02em] text-foreground">
              {totalCount > 0 ? `${totalCount} ${pluralize(totalCount, ["кошелёк", "кошелька", "кошельков"])}` : "Нет кошельков"}
              {favCount > 0 && (
                <span className="ml-3 text-[14px] text-muted-foreground font-normal">
                  · {favCount} в избранном
                </span>
              )}
            </h2>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" size="md" onClick={handleExport} disabled={exporting || loading || totalCount === 0} loading={exporting}>
              <Icon icon="solar:download-linear" className="text-[15px]" />
              {t("exportButton")}
            </Button>
            <Button variant="primary" size="md" onClick={() => router.push("/wallets/new")}>
              <Icon icon="solar:add-circle-linear" className="text-[15px]" />
              Создать кошелёк
            </Button>
          </div>
        </div>

        {error && (
          <div className="border border-destructive/40 bg-destructive/5 p-4 text-[13px] text-destructive">
            {error}
          </div>
        )}

        {/* Wallet table */}
        <div className="border border-border bg-card overflow-x-auto">
          <table className="w-full text-[13px] border-collapse">
            <thead>
              <tr className="border-b border-border text-left">
                <Th className="px-5">Название</Th>
                <Th>Сеть</Th>
                <Th>Тип</Th>
                <Th>Адрес</Th>
                <Th>Токены</Th>
                <Th className="text-right pr-5">UNID</Th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center text-muted-foreground">
                    Загрузка…
                  </td>
                </tr>
              ) : wallets.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-16 text-center">
                    <Icon icon="solar:wallet-linear" className="text-[48px] text-faint" />
                    <p className="mt-3 text-[14px] text-muted-foreground">Кошельков пока нет</p>
                    <Link href="/wallets/new" className="inline-block mt-4">
                      <Button variant="primary" size="sm">Создать первый</Button>
                    </Link>
                  </td>
                </tr>
              ) : (
                wallets.map((w) => {
                  const displayName = w.label?.trim() || w.name || "—";
                  return (
                    <tr key={w.id ?? w.my_unid} className="border-b border-border last:border-b-0 hover:bg-muted/40">
                      <td className="px-5 py-3.5">
                        <Link
                          href={`/wallets/${encodeURIComponent(w.name ?? "")}`}
                          className="flex items-center gap-2 text-foreground hover:text-primary"
                        >
                          {w.is_favorite && (
                            <Icon icon="solar:star-bold" className="text-warning text-[14px] shrink-0" />
                          )}
                          <span className="font-medium truncate max-w-xs">{displayName}</span>
                        </Link>
                      </td>
                      <td className="px-3 py-3.5">
                        <Badge variant="outline">{networkLabel(w.network)}</Badge>
                      </td>
                      <td className="px-3 py-3.5">
                        <Mono size="xs" className="text-muted-foreground">
                          {w.wallet_type === 1 ? "MULTI-SIG" : "STANDARD"}
                        </Mono>
                      </td>
                      <td className="px-3 py-3.5">
                        <Mono truncate>{w.addr ?? "—"}</Mono>
                      </td>
                      <td className="px-3 py-3.5 text-muted-foreground">
                        <Mono size="xs" truncate startChars={20} endChars={0}>{w.token_short_names ?? "—"}</Mono>
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <Mono truncate>{w.my_unid ?? "—"}</Mono>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <th className={`px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal ${className}`}>
      {children}
    </th>
  );
}

function pluralize(n: number, forms: [string, string, string]): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 19) return forms[2];
  if (mod10 === 1) return forms[0];
  if (mod10 >= 2 && mod10 <= 4) return forms[1];
  return forms[2];
}

```

### `frontend/src/app/(authenticated)/transactions/page.tsx`

```tsx
"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import useSWR from "swr";
import { useRouter } from "next/navigation";
import { useTranslations } from "@/hooks/useTranslations";
import { Header } from "@/components/layout/Header";
import { Eyebrow, Mono, StatusPill } from "@/components/ui/primitives";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/lib/icons";
import { api, API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Tx {
  id?: number;
  tx_unid?: string;
  tx_hash?: string | null;
  wallet_name?: string;
  status?: string;
  amount_decimal?: string | number;
  value?: string | number;
  token?: string | null;
  to_address?: string;
  to_addr?: string;
  network?: number;
  fee?: string | number;
  created_at?: string;
  info?: string;
}

const STATUS_OPTIONS = [
  { value: "", label: "Все" },
  { value: "confirmed", label: "Подтверждены" },
  { value: "pending", label: "В обработке" },
  { value: "sent", label: "Отправлены" },
  { value: "rejected", label: "Отклонены" },
];

function formatTime(iso?: string): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return new Intl.DateTimeFormat("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d);
  } catch {
    return iso;
  }
}

export default function TransactionsPage() {
  const t = useTranslations("transactions");
  const router = useRouter();

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [exporting, setExporting] = useState(false);

  const { data: transactions, error, isLoading } = useSWR<Tx[]>(
    ["/api/transactions/filtered", statusFilter],
    () =>
      api.getTransactionsFiltered({
        limit: 100,
        offset: 0,
        status: statusFilter || undefined,
      }),
    { refreshInterval: 30000 },
  );

  const txs: Tx[] = Array.isArray(transactions) ? transactions : [];

  const counts = useMemo(() => {
    const map: Record<string, number> = { "": txs.length, confirmed: 0, pending: 0, sent: 0, rejected: 0 };
    txs.forEach((tx) => {
      const s = (tx.status ?? "").toLowerCase();
      if (s in map) map[s]++;
    });
    return map;
  }, [txs]);

  function handleExport() {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      window.open(`${API_BASE}/export/transactions/csv?${params}`, "_blank");
    } finally {
      setTimeout(() => setExporting(false), 600);
    }
  }

  return (
    <>
      <Header title={t("title")} />

      <div className="px-4 sm:px-6 lg:px-10 py-8 space-y-6">
        {/* Top bar */}
        <div className="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <Eyebrow dash>Транзакции</Eyebrow>
            <h2 className="mt-2 text-[24px] sm:text-[28px] font-medium tracking-[-0.02em] text-foreground">
              {txs.length > 0 ? `${txs.length} записей` : "Нет записей"}
            </h2>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button variant="secondary" size="md" onClick={handleExport} disabled={exporting || isLoading || txs.length === 0} loading={exporting}>
              <Icon icon="solar:download-linear" className="text-[15px]" />
              Экспорт CSV
            </Button>
            <Button variant="primary" size="md" onClick={() => router.push("/transactions/new")}>
              <Icon icon="solar:add-circle-linear" className="text-[15px]" />
              Новая транзакция
            </Button>
          </div>
        </div>

        {/* Filter chips */}
        <div className="flex gap-1.5 flex-wrap">
          {STATUS_OPTIONS.map((opt) => {
            const active = statusFilter === opt.value;
            const count = counts[opt.value] ?? 0;
            return (
              <button
                key={opt.value || "all"}
                type="button"
                onClick={() => setStatusFilter(opt.value)}
                className={cn(
                  "h-8 inline-flex items-center gap-2 px-3 border font-mono text-[11px] tracking-[0.04em] transition-colors",
                  active
                    ? "bg-foreground text-background border-foreground"
                    : "bg-card text-muted-foreground border-border hover:border-strong hover:text-foreground",
                )}
              >
                {opt.label}
                <span className={cn("text-[10px]", active ? "text-background/60" : "text-faint")}>
                  · {count}
                </span>
              </button>
            );
          })}
        </div>

        {error && (
          <div className="border border-destructive/40 bg-destructive/5 p-4 text-[13px] text-destructive">
            Не удалось загрузить транзакции.
          </div>
        )}

        {/* Table */}
        <div className="border border-border bg-card overflow-x-auto">
          <table className="w-full text-[12px] border-collapse">
            <thead>
              <tr className="border-b border-border text-left">
                <Th className="pl-5">Hash</Th>
                <Th>Статус</Th>
                <Th>Кошелёк</Th>
                <Th>Получатель</Th>
                <Th>Токен</Th>
                <Th className="text-right">Сумма</Th>
                <Th className="text-right pr-5">Время</Th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={7} className="px-5 py-12 text-center text-muted-foreground">Загрузка…</td></tr>
              ) : txs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-16 text-center">
                    <Icon icon="solar:transfer-horizontal-linear" className="text-[48px] text-faint" />
                    <p className="mt-3 text-[14px] text-muted-foreground">Транзакций не найдено</p>
                  </td>
                </tr>
              ) : (
                txs.map((tx) => {
                  const kind = (tx.status ?? "").toLowerCase() as any;
                  const dest = tx.to_address || tx.to_addr || "—";
                  const amount = tx.amount_decimal ?? tx.value ?? "—";
                  return (
                    <tr key={tx.tx_unid ?? tx.id} className="border-b border-border last:border-b-0 hover:bg-muted/40">
                      <td className="pl-5 py-3">
                        <Link href={`/transactions/${tx.tx_unid ?? ""}`} className="text-foreground hover:text-primary">
                          <Mono>{tx.tx_hash ?? tx.tx_unid ?? "—"}</Mono>
                        </Link>
                      </td>
                      <td className="px-3 py-3"><StatusPill kind={kind} label={tx.status ?? "—"} /></td>
                      <td className="px-3 py-3 text-foreground"><Mono truncate startChars={10} endChars={4}>{tx.wallet_name ?? "—"}</Mono></td>
                      <td className="px-3 py-3"><Mono truncate>{dest}</Mono></td>
                      <td className="px-3 py-3"><Badge variant="outline">{tx.token ?? "—"}</Badge></td>
                      <td className="px-3 py-3 text-right text-foreground tabular">{String(amount)}</td>
                      <td className="pr-5 py-3 text-right"><Mono size="xs" className="text-faint">{formatTime(tx.created_at)}</Mono></td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <th className={`px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal ${className}`}>
      {children}
    </th>
  );
}

```

### `frontend/src/app/(authenticated)/signatures/page.tsx`

```tsx
"use client";

import { useState } from "react";
import useSWR from "swr";
import { useTranslations } from "@/hooks/useTranslations";
import { Header } from "@/components/layout/Header";
import { Eyebrow, BigNum, Mono, StatusPill } from "@/components/ui/primitives";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import toast from "react-hot-toast";

interface PendingSig {
  tx_unid?: string;
  wallet_name?: string;
  to_address?: string;
  to_addr?: string;
  amount?: string | number;
  amount_decimal?: string | number;
  value?: string | number;
  token?: string;
  network?: number;
  signed_count?: number;
  required_count?: number;
  threshold?: string;
  created_at?: string;
}

interface HistoryItem {
  tx_unid?: string;
  signer_address?: string;
  action?: "signed" | "rejected" | string;
  reason?: string | null;
  signed_at?: string;
}

interface SigStats {
  pending_count?: number;
  signed_last_24h?: number;
  rejected_last_24h?: number;
  total_signers?: number;
}

function formatTime(iso?: string): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export default function SignaturesPage() {
  const t = useTranslations("signatures");
  const [busy, setBusy] = useState<string | null>(null);

  const { data: pending, mutate: mutatePending } = useSWR<PendingSig[]>(
    "/api/signatures/pending",
    api.getPendingSignaturesV2,
    { refreshInterval: 30000 },
  );
  const { data: history, mutate: mutateHistory } = useSWR<HistoryItem[]>(
    "/api/signatures/history",
    () => api.getSignatureHistory(30),
    { refreshInterval: 60000 },
  );
  const { data: stats, mutate: mutateStats } = useSWR<SigStats>(
    "/api/signatures/stats",
    api.getSignatureStats,
    { refreshInterval: 60000 },
  );

  const pendingList: PendingSig[] = Array.isArray(pending) ? pending : [];
  const historyList: HistoryItem[] = Array.isArray(history) ? history : [];

  async function handleSign(txUnid: string) {
    setBusy(txUnid);
    try {
      await api.signTransactionV2(txUnid);
      toast.success(`Подписано: ${txUnid.slice(0, 8)}…`);
      mutatePending(); mutateHistory(); mutateStats();
    } catch (e: any) {
      toast.error(e?.message ?? "Ошибка подписи");
    } finally {
      setBusy(null);
    }
  }

  async function handleReject(txUnid: string) {
    const reason = window.prompt("Причина отклонения (опционально):", "") ?? "";
    setBusy(txUnid);
    try {
      await api.rejectTransactionV2(txUnid, reason);
      toast.success(`Отклонено: ${txUnid.slice(0, 8)}…`);
      mutatePending(); mutateHistory(); mutateStats();
    } catch (e: any) {
      toast.error(e?.message ?? "Ошибка отклонения");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <Header title={t("title")} />

      <div className="px-4 sm:px-6 lg:px-10 py-8 space-y-8">
        <div>
          <Eyebrow dash>Подписи</Eyebrow>
          <h2 className="mt-2 text-[24px] sm:text-[28px] font-medium tracking-[-0.02em] text-foreground">
            Очередь подписей и история
          </h2>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border border border-border">
          <StatTile label="Ожидают" value={String(stats?.pending_count ?? pendingList.length)} accent />
          <StatTile label="Подписано · 24ч" value={String(stats?.signed_last_24h ?? "—")} />
          <StatTile label="Отклонено · 24ч" value={String(stats?.rejected_last_24h ?? "—")} />
          <StatTile label="Подписантов" value={String(stats?.total_signers ?? "—")} />
        </div>

        {/* Pending queue */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <Eyebrow>Ожидают подписи</Eyebrow>
            <Mono size="xs" className="text-faint">{pendingList.length} в очереди</Mono>
          </div>

          {pendingList.length === 0 ? (
            <div className="border border-border bg-card p-12 text-center">
              <Icon icon="solar:check-circle-bold" className="text-[40px] text-success" />
              <p className="mt-3 text-[14px] text-muted-foreground">Нет ожидающих подписи транзакций</p>
            </div>
          ) : (
            <div className="space-y-3">
              {pendingList.map((p) => {
                const dest = p.to_address || p.to_addr || "—";
                const amount = p.amount_decimal ?? p.amount ?? p.value ?? "—";
                const signed = p.signed_count ?? 0;
                const required = p.required_count ?? 0;
                const pct = required > 0 ? Math.min(100, Math.round((signed / required) * 100)) : 0;
                const isBusy = busy === p.tx_unid;

                return (
                  <article key={p.tx_unid} className="border border-border bg-card p-5">
                    <div className="grid lg:grid-cols-[1.4fr_0.7fr_auto] gap-5 items-start">
                      <div>
                        <div className="flex items-center gap-3 flex-wrap">
                          <Mono size="md" className="text-foreground">{p.tx_unid?.slice(0, 12) ?? "—"}…</Mono>
                          <Badge variant="warning">PENDING</Badge>
                          {p.token && <Badge variant="outline">{p.token}</Badge>}
                        </div>
                        <div className="mt-3 flex items-center gap-6 flex-wrap text-[12px]">
                          <span className="text-muted-foreground">
                            <span className="text-faint mr-1">из</span>
                            <Mono>{p.wallet_name?.slice(0, 12) ?? "—"}…</Mono>
                          </span>
                          <span className="text-muted-foreground">
                            <span className="text-faint mr-1">к</span>
                            <Mono>{dest}</Mono>
                          </span>
                          <Mono size="xs" className="text-faint">{formatTime(p.created_at)}</Mono>
                        </div>
                      </div>

                      <div>
                        <div className="flex items-baseline justify-between">
                          <Eyebrow>Сумма</Eyebrow>
                          <Mono size="xs" className="text-faint">{required > 0 ? `${signed}/${required}` : ""}</Mono>
                        </div>
                        <BigNum size="lg" className="mt-1">{String(amount)}</BigNum>
                        <div className="mt-2 h-1 bg-muted relative">
                          <div className="absolute left-0 top-0 h-full bg-primary" style={{ width: `${pct}%` }} />
                        </div>
                      </div>

                      <div className="flex flex-col gap-2 lg:items-end">
                        <Button variant="primary" size="sm" onClick={() => handleSign(p.tx_unid!)} disabled={isBusy} loading={isBusy}>
                          <Icon icon="solar:pen-bold" className="text-[14px]" />
                          Подписать
                        </Button>
                        <Button variant="secondary" size="sm" onClick={() => handleReject(p.tx_unid!)} disabled={isBusy}>
                          <Icon icon="solar:close-circle-linear" className="text-[14px]" />
                          Отклонить
                        </Button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {/* History */}
        <section>
          <Eyebrow className="mb-3">История подписей</Eyebrow>
          <div className="border border-border bg-card overflow-x-auto">
            <table className="w-full text-[12px] border-collapse">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="pl-5 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Действие</th>
                  <th className="px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Транзакция</th>
                  <th className="px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Подписант</th>
                  <th className="px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Причина</th>
                  <th className="pr-5 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal text-right">Время</th>
                </tr>
              </thead>
              <tbody>
                {historyList.length === 0 ? (
                  <tr><td colSpan={5} className="px-5 py-12 text-center text-muted-foreground">Истории пока нет</td></tr>
                ) : (
                  historyList.map((h, i) => (
                    <tr key={i} className="border-b border-border last:border-b-0">
                      <td className="pl-5 py-3">
                        {h.action === "rejected" ? (
                          <StatusPill kind="rejected" label="Отклонил" />
                        ) : (
                          <StatusPill kind="confirmed" label="Подписал" />
                        )}
                      </td>
                      <td className="px-3 py-3"><Mono>{h.tx_unid?.slice(0, 16) ?? "—"}…</Mono></td>
                      <td className="px-3 py-3"><Mono truncate>{h.signer_address ?? "—"}</Mono></td>
                      <td className="px-3 py-3 text-muted-foreground">{h.reason ?? "—"}</td>
                      <td className="pr-5 py-3 text-right"><Mono size="xs" className="text-faint">{formatTime(h.signed_at)}</Mono></td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </>
  );
}

function StatTile({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="bg-card p-5">
      <Eyebrow>{label}</Eyebrow>
      <BigNum size="lg" className={cn("mt-2", accent && "text-primary")}>{value}</BigNum>
    </div>
  );
}

```


# 6. i18n (locales)

### `frontend/src/i18n/locales/ru.json`

```json
{
  "common": {
    "loading": "Загрузка...",
    "error": "Ошибка",
    "success": "Успешно",
    "cancel": "Отмена",
    "save": "Сохранить",
    "delete": "Удалить",
    "edit": "Редактировать",
    "create": "Создать",
    "search": "Поиск...",
    "filter": "Фильтр",
    "refresh": "Обновить",
    "close": "Закрыть",
    "back": "Назад",
    "next": "Далее",
    "submit": "Отправить",
    "reset": "Сбросить",
    "confirm": "Подтвердить",
    "yes": "Да",
    "no": "Нет",
    "all": "Все",
    "none": "Нет",
    "select": "Выбрать",
    "clear": "Очистить",
    "signIn": "Войти",
    "signOut": "Выйти",
    "profileSettings": "Настройки профиля",
    "done": "Готово"
  },
  "navigation": {
    "dashboard": "Главная",
    "wallets": "Кошельки",
    "transactions": "Транзакции",
    "scheduled": "Запланированные",
    "analytics": "Аналитика",
    "signatures": "Подписи",
    "contacts": "Адресная книга",
    "audit": "Журнал аудита",
    "networks": "Сети",
    "help": "Справка",
    "profile": "Профиль",
    "settings": "Настройки",
    "documents": "Документы",
    "organizations": "Организации",
    "billing": "Биллинг",
    "compliance": "Комплаенс",
    "users": "Пользователи",
    "reports": "Отчёты",
    "support": "Поддержка",
    "fiat": "Фиат операции",
    "partner": "Партнёр API"
  },
  "dashboard": {
    "title": "Главная",
    "welcomeMessage": "Добро пожаловать в ORGON",
    "recentActivity": "Последняя активность",
    "noActivity": "Нет недавней активности",
    "lastSync": "Последняя синхронизация",
    "stats": {
      "wallets": "Кошельки",
      "totalWallets": "Всего кошельков",
      "transactions24h": "Транзакций (24ч)",
      "pendingSignatures": "Ожидают подписи",
      "pendingSignaturesHelp": "Транзакции, ожидающие вашей подписи",
      "networks": "Сети",
      "activeNetworks": "Активные сети"
    },
    "alerts": {
      "title": "Системные оповещения",
      "allOperational": "Все системы в порядке",
      "noAlerts": "Нет оповещений",
      "pendingSignaturesPrefix": "ожидают вашей подписи",
      "failedTransactionsPrefix": "неудачных",
      "failedTransactionsSuffix": "за последние 7 дней",
      "viewDetails": "Подробнее →"
    },
    "activity": {
      "title": "Последняя активность",
      "lastEvents": "Последних {{count}} событий",
      "noActivity": "Нет недавней активности",
      "noActivityDesc": "Ваши недавние транзакции и подписи появятся здесь",
      "justNow": "Только что",
      "minutesAgo": "{{count}}м назад",
      "hoursAgo": "{{count}}ч назад",
      "daysAgo": "{{count}}д назад",
      "viewDetails": "Подробнее →",
      "viewAll": "Вся активность →"
    },
    "tokens": {
      "title": "Балансы токенов",
      "subtitle": "Агрегировано по всем кошелькам",
      "noBalances": "Нет балансов токенов"
    },
    "actions": {
      "createWallet": "Создать кошелёк",
      "send": "Отправить"
    },
    "rates": {
      "title": "Курсы криптовалют",
      "token": "Токен",
      "price": "Цена USD",
      "change24h": "Изменение 24ч",
      "noData": "Нет данных о курсах",
      "loading": "Загрузка курсов..."
    }
  },
  "auth": {
    "login": {
      "title": "Вход в ORGON",
      "subtitle": "Управляйте мультиподписными кошельками",
      "emailLabel": "Электронная почта",
      "emailPlaceholder": "admin@orgon.app",
      "passwordLabel": "Пароль",
      "passwordPlaceholder": "Введите ваш пароль",
      "rememberMe": "Запомнить меня",
      "forgotPassword": "Забыли пароль?",
      "signInButton": "Войти",
      "noAccount": "Нет аккаунта?",
      "signUpLink": "Зарегистрироваться",
      "defaultAdmin": "По умолчанию: admin@orgon.app / admin123",
      "errors": {
        "invalidCredentials": "Неверный email или пароль",
        "accountLocked": "Аккаунт заблокирован",
        "serverError": "Ошибка сервера. Попробуйте позже"
      },
      "quickLoginTitle": "Быстрый вход:",
      "quickLoginOr": "Или введите данные вручную выше",
      "testUser": "Test User",
      "adminUser": "Admin"
    },
    "register": {
      "title": "Создать аккаунт",
      "subtitle": "Присоединяйтесь к ORGON для управления кошельками",
      "fullNameLabel": "Полное имя",
      "fullNamePlaceholder": "Иван Иванов",
      "emailLabel": "Электронная почта",
      "emailPlaceholder": "you@example.com",
      "passwordLabel": "Пароль",
      "passwordPlaceholder": "Минимум 8 символов",
      "confirmPasswordLabel": "Подтвердите пароль",
      "confirmPasswordPlaceholder": "Введите пароль повторно",
      "roleLabel": "Роль",
      "roles": {
        "viewer": "Наблюдатель (только чтение)",
        "signer": "Подписант (может подписывать)",
        "admin": "Администратор (полный доступ)"
      },
      "termsAgree": "Я согласен с",
      "termsOfService": "Условиями использования",
      "and": "и",
      "privacyPolicy": "Политикой конфиденциальности",
      "createButton": "Создать аккаунт",
      "alreadyHaveAccount": "Уже есть аккаунт?",
      "signInLink": "Войти",
      "errors": {
        "emailExists": "Email уже используется",
        "passwordMismatch": "Пароли не совпадают",
        "passwordTooShort": "Пароль должен быть минимум 8 символов",
        "invalidEmail": "Неверный формат email"
      }
    },
    "logout": "Выйти",
    "profile": "Профиль",
    "profileSettings": "Настройки профиля",
    "forgotPassword": {
      "title": "Восстановление пароля",
      "subtitle": "Введите email для получения ссылки на сброс пароля",
      "emailLabel": "Электронная почта",
      "emailPlaceholder": "you@example.com",
      "submitButton": "Отправить ссылку",
      "backToLogin": "Вернуться к входу",
      "success": "Если аккаунт с таким email существует, мы отправили ссылку для сброса пароля.",
      "errors": {
        "emailRequired": "Введите email",
        "serverError": "Ошибка сервера. Попробуйте позже"
      }
    },
    "resetPassword": {
      "title": "Новый пароль",
      "subtitle": "Введите новый пароль для вашего аккаунта",
      "passwordLabel": "Новый пароль",
      "passwordPlaceholder": "Минимум 8 символов",
      "confirmPasswordLabel": "Подтвердите пароль",
      "confirmPasswordPlaceholder": "Введите пароль повторно",
      "submitButton": "Сохранить пароль",
      "success": "Пароль успешно изменён! Теперь вы можете войти.",
      "errors": {
        "passwordMismatch": "Пароли не совпадают",
        "passwordTooShort": "Пароль должен быть минимум 8 символов",
        "invalidToken": "Ссылка недействительна или истекла",
        "serverError": "Ошибка сервера. Попробуйте позже"
      }
    }
  },
  "contacts": {
    "title": "Адресная книга",
    "subtitle": "Управляйте вашими частыми получателями",
    "addContact": "Добавить контакт",
    "editContact": "Редактировать контакт",
    "deleteContact": "Удалить контакт",
    "searchPlaceholder": "Поиск по имени или адресу...",
    "noContacts": "Нет контактов",
    "noContactsFiltered": "Нет контактов, соответствующих фильтрам",
    "addFirstContact": "Добавьте ваш первый контакт",
    "deleteConfirm": "Удалить этот контакт?",
    "categories": {
      "label": "Категория",
      "all": "Все категории",
      "personal": "Личные",
      "business": "Бизнес",
      "exchange": "Биржи",
      "other": "Другое"
    },
    "favorites": "Избранное",
    "allContacts": "Все контакты",
    "fields": {
      "name": "Имя",
      "namePlaceholder": "Имя контакта",
      "address": "Адрес",
      "addressPlaceholder": "Адрес кошелька",
      "network": "Сеть",
      "networkPlaceholder": "Выберите сеть",
      "category": "Категория",
      "notes": "Заметки",
      "notesPlaceholder": "Дополнительная информация"
    },
    "actions": {
      "addToFavorites": "Добавить в избранное",
      "removeFromFavorites": "Удалить из избранного"
    }
  },
  "analytics": {
    "title": "Аналитика",
    "subtitle": "Аналитика вашей активности",
    "daysFilter": "дн",
    "days": {
      "7": "7 дней",
      "14": "14 дней",
      "30": "30 дней",
      "90": "90 дней"
    },
    "filters": {
      "title": "Период анализа"
    },
    "stats": {
      "totalWallets": "Всего кошельков",
      "active": "Активные",
      "inactive": "Неактивные",
      "totalSignatures": "Всего подписей",
      "signed": "Подписано",
      "pending": "Ожидают",
      "tokenTypes": "Типы токенов",
      "activeTokens": "Активных токенов в портфеле"
    },
    "charts": {
      "balanceHistory": "История баланса",
      "tokenDistribution": "Распределение токенов",
      "transactionVolume": "Объем транзакций",
      "signatureStats": "Статистика подписей",
      "transactionActivity": "Активность транзакций",
      "transactions": "Транзакции",
      "totalValue": "Общая сумма",
      "noData": "Нет данных",
      "network": "Сеть",
      "txCount": "транз."
    },
    "refreshButton": "Обновить аналитику",
    "loading": "Загрузка аналитики...",
    "error": "Не удалось загрузить данные аналитики",
    "retry": "Повторить"
  },
  "audit": {
    "title": "Журнал аудита",
    "subtitle": "История активности и системные события",
    "searchPlaceholder": "Поиск в логах...",
    "searchButton": "Поиск",
    "clearFilters": "Очистить",
    "noLogs": "Логи не найдены",
    "stats": {
      "totalEvents": "Всего событий",
      "last24h": "За последние 24 часа",
      "actionTypes": "Типы действий"
    },
    "filters": {
      "allActions": "Все действия",
      "allResources": "Все ресурсы",
      "resources": {
        "transaction": "Транзакция",
        "wallet": "Кошелёк",
        "signature": "Подпись",
        "contact": "Контакт",
        "user": "Пользователь"
      },
      "fromDate": "С даты",
      "toDate": "По дату",
      "selectFromDate": "Выберите начальную дату",
      "selectToDate": "Выберите конечную дату"
    },
    "actions": {
      "create": "Создание",
      "update": "Обновление",
      "delete": "Удаление",
      "sign": "Подпись",
      "reject": "Отклонение",
      "view": "Просмотр"
    },
    "fields": {
      "resourceId": "ID ресурса",
      "userId": "ID пользователя",
      "ipAddress": "IP адрес",
      "userAgent": "User Agent",
      "details": "Детали"
    },
    "refreshLogs": "Обновить логи",
    "detailModal": {
      "title": "Детали записи аудита",
      "coreInfo": "Основная информация",
      "networkInfo": "Сетевая информация",
      "logId": "ID записи"
    }
  },
  "scheduled": {
    "title": "Запланированные транзакции",
    "subtitle": "Управляйте автоматическими платежами",
    "noTransactions": "Нет запланированных транзакций",
    "filters": {
      "title": "Фильтры по статусу",
      "pending": "Ожидают",
      "sent": "Отправлены",
      "failed": "Ошибка",
      "cancelled": "Отменены"
    },
    "fields": {
      "token": "Токен",
      "value": "Сумма",
      "recipient": "Получатель",
      "scheduledAt": "Запланировано на",
      "recurrence": "Повторение",
      "nextRun": "Следующий запуск",
      "sentAt": "Отправлено",
      "transactionId": "ID транзакции",
      "error": "Ошибка",
      "info": "Информация"
    },
    "actions": {
      "cancel": "Отменить",
      "cancelConfirm": "Отменить эту запланированную транзакцию?",
      "cancelFailed": "Не удалось отменить транзакцию"
    },
    "status": {
      "pending": "Ожидает",
      "sent": "Отправлено",
      "failed": "Ошибка",
      "cancelled": "Отменено"
    }
  },
  "settings": {
    "title": "Настройки",
    "systemStatus": {
      "title": "Статус системы",
      "orgonBackend": "ORGON Backend",
      "safinaApi": "Safina API",
      "lastSync": "Последняя синхронизация"
    },
    "authentication": {
      "title": "Аутентификация",
      "subtitle": "Bearer токен для доступа к API",
      "placeholder": "Введите токен администратора",
      "saveButton": "Сохранить токен"
    },
    "keyManagement": {
      "title": "Управление ключами",
      "link": "Управление EC ключами для подписи"
    },
    "twofa": {
      "title": "Двухфакторная аутентификация",
      "description": "Добавьте дополнительный уровень безопасности к вашему аккаунту",
      "setupTitle": "Настройка 2FA",
      "enabled": "Включено",
      "enable": "Включить 2FA",
      "disable": "Отключить 2FA",
      "verify": "Проверить",
      "download": "Скачать",
      "scanQR": "Отсканируйте QR-код в приложении Google Authenticator или Authy",
      "manualEntry": "Или введите ключ вручную:",
      "verificationCode": "Код подтверждения",
      "enterCode": "Введите 6-значный код из вашего приложения",
      "enterCodeToDisable": "Введите код подтверждения для отключения 2FA",
      "saveBackupCodes": "Сохраните резервные коды",
      "backupCodesWarning": "Сохраните эти коды в безопасном месте. Они понадобятся если вы потеряете доступ к приложению аутентификации.",
      "backupCodesTotal": "Всего кодов",
      "backupCodesRemaining": "Осталось кодов",
      "regenerateBackupCodes": "Создать новые резервные коды",
      "whyEnable": "Зачем включать 2FA?",
      "securityBenefit": "Двухфакторная аутентификация защищает ваш аккаунт даже если кто-то узнает ваш пароль.",
      "prompts": {
        "enterCode": "Введите код подтверждения из приложения для создания новых резервных кодов:"
      },
      "errors": {
        "setupFailed": "Не удалось начать настройку 2FA",
        "invalidCode": "Неверный код. Код должен содержать 6 цифр.",
        "verificationFailed": "Неверный код подтверждения",
        "disableFailed": "Не удалось отключить 2FA",
        "regenerateFailed": "Не удалось создать новые резервные коды"
      },
      "backupCodeHelp": "Потеряли приложение аутентификации?\nИспользуйте один из резервных кодов."
    },
    "sections": {
      "profile": "Профиль",
      "security": "Безопасность",
      "apiKeys": "API Ключи",
      "notifications": "Уведомления",
      "theme": "Тема",
      "language": "Язык",
      "limits": "Лимиты",
      "backup": "Резервное копирование",
      "about": "О программе"
    },
    "profile": {
      "title": "Настройки профиля",
      "changeAvatar": "Изменить аватар",
      "fullName": "Полное имя",
      "email": "Email адрес",
      "role": "Роль",
      "saveChanges": "Сохранить изменения"
    },
    "security": {
      "title": "Настройки безопасности",
      "twoFactor": "Двухфакторная аутентификация",
      "twoFactorDesc": "Добавьте дополнительный уровень защиты",
      "changePassword": "Изменить пароль",
      "currentPassword": "Текущий пароль",
      "newPassword": "Новый пароль",
      "confirmPassword": "Подтвердите новый пароль",
      "updatePassword": "Обновить пароль",
      "activeSessions": "Активные сессии",
      "activeSessionsCount": "активных сессий",
      "logoutAllSessions": "Выйти из всех сессий"
    },
    "apiKeys": {
      "title": "API Ключи",
      "createNew": "Создать новый ключ",
      "revoke": "Отозвать",
      "created": "Создан",
      "lastUsed": "Последнее использование"
    },
    "notifications": {
      "title": "Настройки уведомлений",
      "email": "Email уведомления",
      "emailDesc": "Получать уведомления на email",
      "push": "Push уведомления",
      "pushDesc": "Получать push уведомления в браузере",
      "telegram": "Telegram уведомления",
      "telegramDesc": "Получать уведомления через Telegram бота",
      "transactions": "Уведомления о транзакциях",
      "transactionsDesc": "Уведомлять о новых транзакциях",
      "security": "Уведомления о безопасности",
      "securityDesc": "Уведомлять о событиях безопасности",
      "weekly": "Еженедельный отчет",
      "weeklyDesc": "Отправлять еженедельную сводку активности"
    },
    "theme": {
      "title": "Тема оформления",
      "light": "Светлая",
      "dark": "Темная",
      "auto": "Авто"
    },
    "language": {
      "title": "Язык интерфейса"
    },
    "limits": {
      "title": "Лимиты аккаунта",
      "wallets": "Кошельки",
      "monthlyVolume": "Месячный объем",
      "transaction": "Лимиты транзакций",
      "maxTransactionSize": "Макс. размер транзакции",
      "upgrade": "Улучшить тариф"
    },
    "backup": {
      "title": "Экспорт данных и резервное копирование",
      "description": "Экспортируйте данные для резервного копирования или миграции",
      "exportWallets": "Экспорт кошельков",
      "exportWalletsDesc": "Скачать адреса кошельков и метаданные",
      "exportTransactions": "Экспорт транзакций",
      "exportTransactionsDesc": "Скачать историю транзакций в CSV",
      "exportContacts": "Экспорт контактов",
      "exportContactsDesc": "Скачать адресную книгу в JSON"
    },
    "about": {
      "title": "О программе ORGON",
      "version": "Версия",
      "backend": "Статус Backend",
      "safinaApi": "Статус Safina API",
      "lastSync": "Последняя синхронизация",
      "documentation": "Документация",
      "website": "Веб-сайт",
      "support": "Поддержка",
      "rights": "Все права защищены."
    }
  },
  "profile": {
    "title": "Профиль",
    "description": "Управление вашим профилем и настройками безопасности",
    "memberSince": "Пользователь с",
    "password": {
      "title": "Пароль",
      "description": "Изменение пароля для входа в систему",
      "change": "Изменить пароль",
      "cancel": "Отмена",
      "current": "Текущий пароль",
      "new": "Новый пароль",
      "confirm": "Подтвердите новый пароль",
      "save": "Сохранить пароль",
      "mismatch": "Пароли не совпадают",
      "tooShort": "Пароль должен содержать минимум 8 символов",
      "success": "Пароль успешно изменен",
      "failed": "Не удалось изменить пароль"
    },
    "sessions": {
      "title": "Активные сессии",
      "description": "Управление устройствами с доступом к вашему аккаунту",
      "current": "Текущая сессия",
      "mobile": "Мобильное устройство",
      "desktop": "Компьютер",
      "lastActive": "Последняя активность",
      "revoke": "Завершить",
      "confirmRevoke": "Вы уверены, что хотите завершить эту сессию?",
      "noSessions": "Нет активных сессий"
    },
    "language": {
      "title": "Язык интерфейса",
      "description": "Выберите предпочитаемый язык для интерфейса ORGON",
      "active": "Активный"
    },
    "theme": {
      "title": "Тема оформления",
      "description": "Настройте внешний вид интерфейса ORGON",
      "light": "Светлая",
      "dark": "Темная",
      "system": "Системная",
      "active": "Активная"
    }
  },
  "wallets": {
    "title": "Кошельки",
    "count": "{{count}} кошельков",
    "exportButton": "Экспорт CSV",
    "exporting": "Экспорт...",
    "table": {
      "favorite": "Избранное",
      "name": "Имя / Метка",
      "address": "Адрес",
      "network": "Сеть",
      "tokens": "Токены",
      "info": "Информация",
      "pending": "Ожидает...",
      "noWallets": "Кошельки не найдены. Создайте первый кошелёк."
    }
  },
  "transactions": {
    "title": "Транзакции",
    "count": "{{count}} транзакций",
    "filtered": "(отфильтровано)",
    "exportButton": "Экспорт CSV",
    "exporting": "Экспорт...",
    "failedToLoad": "Не удалось загрузить транзакции",
    "table": {
      "unid": "UNID",
      "to": "Кому",
      "amount": "Сумма",
      "status": "Статус",
      "txHash": "TX Hash",
      "date": "Дата",
      "noTransactions": "Транзакции не найдены"
    },
    "filters": {
      "title": "Фильтры",
      "wallet": "Кошелёк",
      "allWallets": "Все кошельки",
      "status": "Статус",
      "allStatuses": "Все статусы",
      "network": "Сеть",
      "allNetworks": "Все сети",
      "fromDate": "С даты",
      "toDate": "До даты",
      "applyButton": "Применить фильтры",
      "clearButton": "Очистить"
    },
    "statuses": {
      "pending": "Ожидает",
      "signed": "Подписано",
      "confirmed": "Подтверждено",
      "rejected": "Отклонено",
      "failed": "Ошибка"
    },
    "feeEstimate": {
      "title": "Оценка комиссии",
      "estimating": "Расчёт комиссии...",
      "fee": "Комиссия",
      "total": "Итого",
      "error": "Не удалось рассчитать комиссию"
    },
    "addressValidation": {
      "valid": "Адрес валиден",
      "invalid": "Невалидный адрес",
      "validating": "Проверка адреса..."
    }
  },
  "networks": {
    "title": "Сети",
    "id": "ID",
    "supportedTokens": "Поддерживаемые токены"
  },
  "signatures": {
    "title": "Подписи",
    "notifications": {
      "signed": "Транзакция {txId}... успешно подписана",
      "rejected": "Транзакция {txId}... отклонена",
      "signFailed": "Не удалось подписать транзакцию",
      "rejectFailed": "Не удалось отклонить транзакцию",
      "loadFailed": "Не удалось загрузить подписи. Попробуйте снова."
    },
    "stats": {
      "title": "Статистика подписей",
      "pendingNow": "Ожидают сейчас",
      "signed24h": "Подписано (24ч)",
      "rejected24h": "Отклонено (24ч)",
      "totalSigned": "Всего подписано"
    },
    "pending": {
      "title": "Ожидают подписи",
      "count": "({{count}})",
      "table": {
        "token": "Токен",
        "to": "Кому",
        "value": "Сумма",
        "age": "Возраст",
        "progress": "Прогресс",
        "actions": "Действия",
        "signButton": "Подписать",
        "signing": "Подписание...",
        "rejectButton": "Отклонить",
        "loadStatusButton": "Загрузить статус",
        "noSignatures": "Нет транзакций, ожидающих подписи"
      },
      "rejectDialog": {
        "title": "Отклонить транзакцию",
        "reasonLabel": "Причина отклонения",
        "reasonPlaceholder": "Введите причину...",
        "cancelButton": "Отмена",
        "confirmButton": "Отклонить"
      }
    },
    "history": {
      "title": "Последняя история",
      "table": {
        "transaction": "Транзакция",
        "action": "Действие",
        "signer": "Подписант",
        "timestamp": "Время",
        "reason": "Причина",
        "noHistory": "История подписей пуста"
      },
      "actions": {
        "signed": "Подписано",
        "rejected": "Отклонено"
      }
    }
  },
  "metadata": {
    "title": "ORGON - Управление кошельками",
    "description": "Управление криптовалютными кошельками через Safina Pay"
  },
  "organizations": {
    "title": "Организации",
    "newOrganization": "Новая организация",
    "selectOrganization": "Выбрать организацию",
    "manageOrganizations": "Управление организациями",
    "allOrganizations": "Все организации",
    "overview": "Обзор",
    "members": "Участники",
    "settings": "Настройки",
    "details": "Детали организации",
    "addMember": "Добавить участника",
    "maxWallets": "Макс. кошельков",
    "maxVolume": "Макс. объем",
    "kycRequired": "Требуется KYC",
    "created": "Создано",
    "status": {
      "active": "Активна",
      "suspended": "Приостановлена",
      "closed": "Закрыта"
    },
    "license": {
      "free": "Бесплатная",
      "pro": "Профессиональная",
      "enterprise": "Корпоративная"
    },
    "role": {
      "admin": "Администратор",
      "operator": "Оператор",
      "viewer": "Наблюдатель"
    }
  },
  "billing": {
    "title": "Биллинг и подписки",
    "currentPlan": "Текущий план",
    "month": "месяц",
    "year": "год",
    "renewalDate": "Дата продления",
    "autoRenew": "Автопродление",
    "enabled": "Включено",
    "disabled": "Выключено",
    "upgradePlan": "Улучшить план",
    "cancelSubscription": "Отменить подписку",
    "noSubscription": "Нет активной подписки",
    "choosePlan": "Выберите план",
    "outstandingBalance": "Задолженность",
    "totalSpend": "Всего потрачено",
    "recentInvoices": "Последние счета",
    "invoiceNumber": "Счёт №",
    "issueDate": "Дата выставления",
    "dueDate": "Срок оплаты",
    "amount": "Сумма",
    "status": "Статус",
    "actions": "Действия",
    "payNow": "Оплатить",
    "paid": "Оплачено",
    "noInvoices": "Счетов пока нет",
    "paymentHistory": "История платежей",
    "noPayments": "Платежей пока нет",
    "select": "Выбрать",
    "cancelConfirm": "Вы уверены что хотите отменить подписку?"
  },
  "compliance": {
    "title": "Комплаенс и регуляторика",
    "kycRecords": "KYC записи",
    "amlAlerts": "AML оповещения",
    "reports": "Отчёты",
    "recentKYC": "Последние KYC записи",
    "noKYC": "KYC записей пока нет",
    "amlAlertsTitle": "AML оповещения",
    "noAlerts": "Оповещений нет",
    "reportsTitle": "Отчёты для регулятора",
    "noReports": "Отчётов пока нет"
  },
  "branding": {
    "title": "Брендинг и White Label",
    "logo": "Логотип",
    "logoUrl": "URL логотипа",
    "colors": "Цвета",
    "primaryColor": "Основной цвет",
    "secondaryColor": "Вторичный цвет",
    "accentColor": "Акцентный цвет",
    "platformInfo": "Информация о платформе",
    "platformName": "Название платформы",
    "tagline": "Слоган",
    "supportEmail": "Email поддержки",
    "preview": "Предпросмотр",
    "previewButton": "Основная кнопка",
    "previewSecondary": "Вторичная кнопка"
  }
}
```

### `frontend/src/i18n/locales/en.json`

```json
{
  "common": {
    "loading": "Loading...",
    "error": "Error",
    "success": "Success",
    "cancel": "Cancel",
    "save": "Save",
    "delete": "Delete",
    "edit": "Edit",
    "create": "Create",
    "search": "Search...",
    "filter": "Filter",
    "refresh": "Refresh",
    "close": "Close",
    "back": "Back",
    "next": "Next",
    "submit": "Submit",
    "reset": "Reset",
    "confirm": "Confirm",
    "yes": "Yes",
    "no": "No",
    "all": "All",
    "none": "None",
    "select": "Select",
    "clear": "Clear",
    "signIn": "Sign In",
    "signOut": "Sign Out",
    "profileSettings": "Profile Settings",
    "done": "Done"
  },
  "navigation": {
    "dashboard": "Dashboard",
    "wallets": "Wallets",
    "transactions": "Transactions",
    "scheduled": "Scheduled",
    "analytics": "Analytics",
    "signatures": "Signatures",
    "contacts": "Address Book",
    "audit": "Audit Log",
    "networks": "Networks",
    "profile": "Profile",
    "settings": "Settings",
    "documents": "Documents",
    "organizations": "Organizations",
    "billing": "Billing",
    "compliance": "Compliance",
    "users": "Users",
    "reports": "Reports",
    "support": "Support",
    "fiat": "Fiat Operations",
    "partner": "Partner API"
  },
  "dashboard": {
    "title": "Dashboard",
    "welcomeMessage": "Welcome to ORGON",
    "recentActivity": "Recent Activity",
    "noActivity": "No recent activity",
    "lastSync": "Last sync",
    "stats": {
      "wallets": "Wallets",
      "totalWallets": "Total Wallets",
      "transactions24h": "Transactions (24h)",
      "pendingSignatures": "Pending Signatures",
      "pendingSignaturesHelp": "Transactions awaiting your signature",
      "networks": "Networks",
      "activeNetworks": "Active Networks"
    },
    "alerts": {
      "title": "System Alerts",
      "allOperational": "All Systems Operational",
      "noAlerts": "No alerts at this time",
      "pendingSignatures": "{count, plural, one {# transaction awaits} other {# transactions await}} your signature",
      "failedTransactions": "{count, plural, one {# failed transaction} other {# failed transactions}} in last 7 days",
      "viewDetails": "View details →"
    },
    "activity": {
      "title": "Recent Activity",
      "lastEvents": "Last {count, plural, one {# event} other {# events}}",
      "noActivity": "No Recent Activity",
      "noActivityDesc": "Your recent transactions and signatures will appear here",
      "justNow": "Just now",
      "minutesAgo": "{{count}}m ago",
      "hoursAgo": "{{count}}h ago",
      "daysAgo": "{{count}}d ago",
      "viewDetails": "View details →",
      "viewAll": "View all activity →"
    },
    "tokens": {
      "title": "Token Balances",
      "subtitle": "Aggregated across wallets",
      "noBalances": "No token balances"
    },
    "actions": {
      "createWallet": "Create Wallet",
      "send": "Send"
    },
    "rates": {
      "title": "Crypto Rates",
      "token": "Token",
      "price": "Price USD",
      "change24h": "24h Change",
      "noData": "No rate data",
      "loading": "Loading rates..."
    }
  },
  "auth": {
    "login": {
      "title": "Welcome to ORGON",
      "subtitle": "Sign in to manage your multi-signature wallets",
      "emailLabel": "Email",
      "emailPlaceholder": "admin@orgon.app",
      "passwordLabel": "Password",
      "passwordPlaceholder": "Enter your password",
      "rememberMe": "Remember me",
      "forgotPassword": "Forgot password?",
      "signInButton": "Sign In",
      "noAccount": "Don't have an account?",
      "signUpLink": "Sign up",
      "defaultAdmin": "Default admin: admin@orgon.app / admin123",
      "errors": {
        "invalidCredentials": "Incorrect email or password",
        "accountLocked": "Account is locked",
        "serverError": "Server error. Please try again later"
      },
      "quickLoginTitle": "Quick Login:",
      "quickLoginOr": "Or enter credentials manually above",
      "testUser": "Test User",
      "adminUser": "Admin"
    },
    "register": {
      "title": "Create Account",
      "subtitle": "Join ORGON to manage multi-signature wallets",
      "fullNameLabel": "Full Name",
      "fullNamePlaceholder": "John Doe",
      "emailLabel": "Email",
      "emailPlaceholder": "you@example.com",
      "passwordLabel": "Password",
      "passwordPlaceholder": "At least 8 characters",
      "confirmPasswordLabel": "Confirm Password",
      "confirmPasswordPlaceholder": "Re-enter your password",
      "roleLabel": "Role",
      "roles": {
        "viewer": "Viewer (Read-only)",
        "signer": "Signer (Can sign transactions)",
        "admin": "Admin (Full access)"
      },
      "termsAgree": "I agree to the",
      "termsOfService": "Terms of Service",
      "and": "and",
      "privacyPolicy": "Privacy Policy",
      "createButton": "Create Account",
      "alreadyHaveAccount": "Already have an account?",
      "signInLink": "Sign in",
      "errors": {
        "emailExists": "Email already in use",
        "passwordMismatch": "Passwords do not match",
        "passwordTooShort": "Password must be at least 8 characters",
        "invalidEmail": "Invalid email format"
      }
    },
    "logout": "Logout",
    "profile": "Profile",
    "profileSettings": "Profile Settings",
    "forgotPassword": {
      "title": "Reset Password",
      "subtitle": "Enter your email to receive a password reset link",
      "emailLabel": "Email",
      "emailPlaceholder": "you@example.com",
      "submitButton": "Send Reset Link",
      "backToLogin": "Back to Login",
      "success": "If an account with that email exists, we sent a password reset link.",
      "errors": {
        "emailRequired": "Enter your email",
        "serverError": "Server error. Try again later"
      }
    },
    "resetPassword": {
      "title": "New Password",
      "subtitle": "Enter a new password for your account",
      "passwordLabel": "New Password",
      "passwordPlaceholder": "At least 8 characters",
      "confirmPasswordLabel": "Confirm Password",
      "confirmPasswordPlaceholder": "Re-enter password",
      "submitButton": "Save Password",
      "success": "Password changed! You can now log in.",
      "errors": {
        "passwordMismatch": "Passwords do not match",
        "passwordTooShort": "Password must be at least 8 characters",
        "invalidToken": "Link is invalid or expired",
        "serverError": "Server error. Try again later"
      }
    }
  },
  "contacts": {
    "title": "Address Book",
    "subtitle": "Manage your frequent recipients",
    "addContact": "Add Contact",
    "editContact": "Edit Contact",
    "deleteContact": "Delete Contact",
    "searchPlaceholder": "Search by name or address...",
    "noContacts": "No contacts yet",
    "noContactsFiltered": "No contacts match your filters",
    "addFirstContact": "Add your first contact",
    "deleteConfirm": "Delete this contact?",
    "categories": {
      "label": "Category",
      "all": "All Categories",
      "personal": "Personal",
      "business": "Business",
      "exchange": "Exchange",
      "other": "Other"
    },
    "favorites": "Favorites",
    "allContacts": "All Contacts",
    "fields": {
      "name": "Name",
      "namePlaceholder": "Contact name",
      "address": "Address",
      "addressPlaceholder": "Wallet address",
      "network": "Network",
      "networkPlaceholder": "Select network",
      "category": "Category",
      "notes": "Notes",
      "notesPlaceholder": "Additional information"
    },
    "actions": {
      "addToFavorites": "Add to favorites",
      "removeFromFavorites": "Remove from favorites"
    }
  },
  "analytics": {
    "title": "Analytics",
    "subtitle": "Insights into your wallet activity",
    "daysFilter": "d",
    "days": {
      "7": "7 days",
      "14": "14 days",
      "30": "30 days",
      "90": "90 days"
    },
    "filters": {
      "title": "Analysis Period"
    },
    "stats": {
      "totalWallets": "Total Wallets",
      "active": "Active",
      "inactive": "Inactive",
      "totalSignatures": "Total Signatures",
      "signed": "Signed",
      "pending": "Pending",
      "tokenTypes": "Token Types",
      "activeTokens": "Active tokens in portfolio"
    },
    "charts": {
      "balanceHistory": "Balance History",
      "tokenDistribution": "Token Distribution",
      "transactionVolume": "Transaction Volume",
      "signatureStats": "Signature Statistics",
      "transactionActivity": "Transaction Activity",
      "transactions": "Transactions",
      "totalValue": "Total Value",
      "noData": "No data available",
      "network": "Network",
      "txCount": "tx"
    },
    "refreshButton": "Refresh Analytics",
    "loading": "Loading analytics...",
    "error": "Failed to load analytics data",
    "retry": "Retry"
  },
  "audit": {
    "title": "Audit Log",
    "subtitle": "Activity history and system events",
    "searchPlaceholder": "Search logs...",
    "searchButton": "Search",
    "clearFilters": "Clear",
    "noLogs": "No logs found",
    "stats": {
      "totalEvents": "Total Events",
      "last24h": "Last 24 Hours",
      "actionTypes": "Action Types"
    },
    "filters": {
      "allActions": "All Actions",
      "allResources": "All Resources",
      "resources": {
        "transaction": "Transaction",
        "wallet": "Wallet",
        "signature": "Signature",
        "contact": "Contact",
        "user": "User"
      },
      "fromDate": "From Date",
      "toDate": "To Date",
      "selectFromDate": "Select start date",
      "selectToDate": "Select end date"
    },
    "actions": {
      "create": "Create",
      "update": "Update",
      "delete": "Delete",
      "sign": "Sign",
      "reject": "Reject",
      "view": "View"
    },
    "fields": {
      "resourceId": "Resource ID",
      "userId": "User ID",
      "ipAddress": "IP Address",
      "userAgent": "User Agent",
      "details": "Details"
    },
    "refreshLogs": "Refresh Logs",
    "detailModal": {
      "title": "Audit Log Details",
      "coreInfo": "Core Information",
      "networkInfo": "Network Information",
      "logId": "Log ID"
    }
  },
  "scheduled": {
    "title": "Scheduled Transactions",
    "subtitle": "Manage your automated payments",
    "noTransactions": "No scheduled transactions",
    "filters": {
      "title": "Status Filters",
      "pending": "Pending",
      "sent": "Sent",
      "failed": "Failed",
      "cancelled": "Cancelled"
    },
    "fields": {
      "token": "Token",
      "value": "Amount",
      "recipient": "Recipient",
      "scheduledAt": "Scheduled At",
      "recurrence": "Recurrence",
      "nextRun": "Next Run",
      "sentAt": "Sent At",
      "transactionId": "Transaction ID",
      "error": "Error",
      "info": "Info"
    },
    "actions": {
      "cancel": "Cancel",
      "cancelConfirm": "Cancel this scheduled transaction?",
      "cancelFailed": "Failed to cancel transaction"
    },
    "status": {
      "pending": "Pending",
      "sent": "Sent",
      "failed": "Failed",
      "cancelled": "Cancelled"
    }
  },
  "settings": {
    "title": "Settings",
    "systemStatus": {
      "title": "System Status",
      "orgonBackend": "ORGON Backend",
      "safinaApi": "Safina API",
      "lastSync": "Last Sync"
    },
    "authentication": {
      "title": "Authentication",
      "subtitle": "Bearer token for API access",
      "placeholder": "Enter admin token",
      "saveButton": "Save Token"
    },
    "keyManagement": {
      "title": "Key Management",
      "link": "Manage EC signing keys"
    },
    "twofa": {
      "title": "Two-Factor Authentication",
      "description": "Add an extra layer of security to your account",
      "setupTitle": "2FA Setup",
      "enabled": "Enabled",
      "enable": "Enable 2FA",
      "disable": "Disable 2FA",
      "verify": "Verify",
      "download": "Download",
      "scanQR": "Scan this QR code in Google Authenticator or Authy",
      "manualEntry": "Or enter the key manually:",
      "verificationCode": "Verification Code",
      "enterCode": "Enter the 6-digit code from your authenticator app",
      "enterCodeToDisable": "Enter verification code to disable 2FA",
      "saveBackupCodes": "Save your backup codes",
      "backupCodesWarning": "Save these codes in a safe place. You'll need them if you lose access to your authenticator app.",
      "backupCodesTotal": "Total Codes",
      "backupCodesRemaining": "Remaining Codes",
      "regenerateBackupCodes": "Generate New Backup Codes",
      "whyEnable": "Why enable 2FA?",
      "securityBenefit": "Two-factor authentication protects your account even if someone knows your password.",
      "prompts": {
        "enterCode": "Enter verification code from your app to generate new backup codes:"
      },
      "errors": {
        "setupFailed": "Failed to start 2FA setup",
        "invalidCode": "Invalid code. Code must be 6 digits.",
        "verificationFailed": "Invalid verification code",
        "disableFailed": "Failed to disable 2FA",
        "regenerateFailed": "Failed to generate new backup codes"
      },
      "backupCodeHelp": "Lost your authenticator app?\nUse one of your backup codes instead."
    },
    "sections": {
      "profile": "Profile",
      "security": "Security",
      "apiKeys": "API Keys",
      "notifications": "Notifications",
      "theme": "Theme",
      "language": "Language",
      "limits": "Limits",
      "backup": "Backup",
      "about": "About"
    },
    "profile": {
      "title": "Profile Settings",
      "changeAvatar": "Change Avatar",
      "fullName": "Full Name",
      "email": "Email Address",
      "role": "Role",
      "saveChanges": "Save Changes"
    },
    "security": {
      "title": "Security Settings",
      "twoFactor": "Two-Factor Authentication",
      "twoFactorDesc": "Add an extra layer of security to your account",
      "changePassword": "Change Password",
      "currentPassword": "Current Password",
      "newPassword": "New Password",
      "confirmPassword": "Confirm New Password",
      "updatePassword": "Update Password",
      "activeSessions": "Active Sessions",
      "activeSessionsCount": "active session(s)",
      "logoutAllSessions": "Logout all sessions"
    },
    "apiKeys": {
      "title": "API Keys",
      "createNew": "Create New API Key",
      "revoke": "Revoke",
      "created": "Created",
      "lastUsed": "Last used"
    },
    "notifications": {
      "title": "Notification Preferences",
      "email": "Email Notifications",
      "emailDesc": "Receive notifications via email",
      "push": "Push Notifications",
      "pushDesc": "Receive push notifications in browser",
      "telegram": "Telegram Notifications",
      "telegramDesc": "Receive notifications via Telegram bot",
      "transactions": "Transaction Alerts",
      "transactionsDesc": "Notify me about new transactions",
      "security": "Security Alerts",
      "securityDesc": "Notify me about security events",
      "weekly": "Weekly Report",
      "weeklyDesc": "Send weekly summary of activity"
    },
    "theme": {
      "title": "Theme Preferences",
      "light": "Light",
      "dark": "Dark",
      "auto": "Auto"
    },
    "language": {
      "title": "Language Preferences"
    },
    "limits": {
      "title": "Account Limits",
      "wallets": "Wallets",
      "monthlyVolume": "Monthly Volume",
      "transaction": "Transaction Limits",
      "maxTransactionSize": "Max transaction size",
      "upgrade": "Upgrade Plan"
    },
    "backup": {
      "title": "Data Export & Backup",
      "description": "Export your data for backup or migration purposes",
      "exportWallets": "Export Wallets",
      "exportWalletsDesc": "Download wallet addresses and metadata",
      "exportTransactions": "Export Transactions",
      "exportTransactionsDesc": "Download transaction history as CSV",
      "exportContacts": "Export Contacts",
      "exportContactsDesc": "Download address book as JSON"
    },
    "about": {
      "title": "About ORGON",
      "version": "Version",
      "backend": "Backend Status",
      "safinaApi": "Safina API Status",
      "lastSync": "Last Sync",
      "documentation": "Documentation",
      "website": "Website",
      "support": "Support",
      "rights": "All rights reserved."
    }
  },
  "profile": {
    "title": "Profile",
    "description": "Manage your profile and security settings",
    "memberSince": "Member since",
    "password": {
      "title": "Password",
      "description": "Change your login password",
      "change": "Change Password",
      "cancel": "Cancel",
      "current": "Current Password",
      "new": "New Password",
      "confirm": "Confirm New Password",
      "save": "Save Password",
      "mismatch": "Passwords do not match",
      "tooShort": "Password must be at least 8 characters",
      "success": "Password changed successfully",
      "failed": "Failed to change password"
    },
    "sessions": {
      "title": "Active Sessions",
      "description": "Manage devices with access to your account",
      "current": "Current session",
      "mobile": "Mobile device",
      "desktop": "Desktop",
      "lastActive": "Last active",
      "revoke": "Revoke",
      "confirmRevoke": "Are you sure you want to revoke this session?",
      "noSessions": "No active sessions"
    },
    "language": {
      "title": "Interface Language",
      "description": "Select your preferred language for ORGON interface",
      "active": "Active"
    },
    "theme": {
      "title": "Appearance Theme",
      "description": "Customize the look and feel of ORGON interface",
      "light": "Light",
      "dark": "Dark",
      "system": "System",
      "active": "Active"
    }
  },
  "wallets": {
    "title": "Wallets",
    "count": "{{count}} wallets",
    "exportButton": "Export CSV",
    "exporting": "Exporting...",
    "table": {
      "favorite": "Favorite",
      "name": "Name / Label",
      "address": "Address",
      "network": "Network",
      "tokens": "Tokens",
      "info": "Info",
      "pending": "Pending...",
      "noWallets": "No wallets found. Create one to get started."
    }
  },
  "transactions": {
    "title": "Transactions",
    "count": "{{count}} transactions",
    "filtered": "(filtered)",
    "exportButton": "Export CSV",
    "exporting": "Exporting...",
    "failedToLoad": "Failed to load transactions",
    "table": {
      "unid": "UNID",
      "to": "To",
      "amount": "Amount",
      "status": "Status",
      "txHash": "TX Hash",
      "date": "Date",
      "noTransactions": "No transactions found"
    },
    "filters": {
      "title": "Filters",
      "wallet": "Wallet",
      "allWallets": "All wallets",
      "status": "Status",
      "allStatuses": "All statuses",
      "network": "Network",
      "allNetworks": "All networks",
      "fromDate": "From Date",
      "toDate": "To Date",
      "applyButton": "Apply Filters",
      "clearButton": "Clear"
    },
    "statuses": {
      "pending": "Pending",
      "signed": "Signed",
      "confirmed": "Confirmed",
      "rejected": "Rejected",
      "failed": "Failed"
    },
    "feeEstimate": {
      "title": "Fee Estimate",
      "estimating": "Estimating fee...",
      "fee": "Fee",
      "total": "Total",
      "error": "Failed to estimate fee"
    },
    "addressValidation": {
      "valid": "Address is valid",
      "invalid": "Invalid address",
      "validating": "Validating address..."
    }
  },
  "networks": {
    "title": "Networks",
    "id": "ID",
    "supportedTokens": "Supported Tokens"
  },
  "signatures": {
    "title": "Signatures",
    "notifications": {
      "signed": "Transaction {txId}... signed successfully",
      "rejected": "Transaction {txId}... rejected",
      "signFailed": "Failed to sign transaction",
      "rejectFailed": "Failed to reject transaction",
      "loadFailed": "Failed to load signatures. Please try again."
    },
    "stats": {
      "title": "Signature Statistics",
      "pendingNow": "Pending Now",
      "signed24h": "Signed (24h)",
      "rejected24h": "Rejected (24h)",
      "totalSigned": "Total Signed"
    },
    "pending": {
      "title": "Pending Signatures",
      "count": "({{count}})",
      "table": {
        "token": "Token",
        "to": "To",
        "value": "Value",
        "age": "Age",
        "progress": "Progress",
        "actions": "Actions",
        "signButton": "Sign",
        "signing": "Signing...",
        "rejectButton": "Reject",
        "loadStatusButton": "Load Status",
        "noSignatures": "No transactions awaiting signature"
      },
      "rejectDialog": {
        "title": "Reject Transaction",
        "reasonLabel": "Rejection Reason",
        "reasonPlaceholder": "Enter reason...",
        "cancelButton": "Cancel",
        "confirmButton": "Reject"
      }
    },
    "history": {
      "title": "Recent History",
      "table": {
        "transaction": "Transaction",
        "action": "Action",
        "signer": "Signer",
        "timestamp": "Timestamp",
        "reason": "Reason",
        "noHistory": "Signature history is empty"
      },
      "actions": {
        "signed": "Signed",
        "rejected": "Rejected"
      }
    }
  },
  "metadata": {
    "title": "ORGON - Wallet Dashboard",
    "description": "Crypto wallet management via Safina Pay"
  },
  "organizations": {
    "title": "Organizations",
    "newOrganization": "New Organization",
    "selectOrganization": "Select Organization",
    "manageOrganizations": "Manage Organizations",
    "allOrganizations": "All Organizations",
    "overview": "Overview",
    "members": "Members",
    "settings": "Settings",
    "details": "Organization Details",
    "addMember": "Add Member",
    "maxWallets": "Max Wallets",
    "maxVolume": "Max Volume",
    "kycRequired": "KYC Required",
    "created": "Created",
    "status": {
      "active": "Active",
      "suspended": "Suspended",
      "closed": "Closed"
    },
    "license": {
      "free": "Free",
      "pro": "Pro",
      "enterprise": "Enterprise"
    },
    "role": {
      "admin": "Admin",
      "operator": "Operator",
      "viewer": "Viewer"
    }
  },
  "billing": {
    "title": "Billing & Subscriptions",
    "currentPlan": "Current Plan",
    "month": "month",
    "year": "year",
    "renewalDate": "Renewal date",
    "autoRenew": "Auto-renew",
    "enabled": "Enabled",
    "disabled": "Disabled",
    "upgradePlan": "Upgrade Plan",
    "cancelSubscription": "Cancel Subscription",
    "noSubscription": "No active subscription",
    "choosePlan": "Choose a Plan",
    "outstandingBalance": "Outstanding Balance",
    "totalSpend": "Total spend",
    "recentInvoices": "Recent Invoices",
    "invoiceNumber": "Invoice #",
    "issueDate": "Issue Date",
    "dueDate": "Due Date",
    "amount": "Amount",
    "status": "Status",
    "actions": "Actions",
    "payNow": "Pay Now",
    "paid": "Paid",
    "noInvoices": "No invoices yet",
    "paymentHistory": "Payment History",
    "noPayments": "No payments yet",
    "select": "Select",
    "cancelConfirm": "Are you sure you want to cancel your subscription?"
  },
  "compliance": {
    "title": "Compliance & Regulatory",
    "kycRecords": "KYC Records",
    "amlAlerts": "AML Alerts",
    "reports": "Reports",
    "recentKYC": "Recent KYC Records",
    "noKYC": "No KYC records yet",
    "amlAlertsTitle": "AML Alerts",
    "noAlerts": "No alerts",
    "reportsTitle": "Compliance Reports",
    "noReports": "No reports yet"
  },
  "branding": {
    "title": "Branding & White Label",
    "logo": "Logo",
    "logoUrl": "Logo URL",
    "colors": "Colors",
    "primaryColor": "Primary Color",
    "secondaryColor": "Secondary Color",
    "accentColor": "Accent Color",
    "platformInfo": "Platform Information",
    "platformName": "Platform Name",
    "tagline": "Tagline",
    "supportEmail": "Support Email",
    "preview": "Preview",
    "previewButton": "Primary Button",
    "previewSecondary": "Secondary Button"
  }
}
```

### `frontend/src/i18n/locales/ky.json`

```json
{
  "common": {
    "loading": "Жүктөлүүдө...",
    "error": "Ката",
    "success": "Ийгиликтүү",
    "cancel": "Жокко чыгаруу",
    "save": "Сактоо",
    "delete": "Өчүрүү",
    "edit": "Түзөтүү",
    "create": "Түзүү",
    "search": "Издөө...",
    "filter": "Чыпка",
    "refresh": "Жаңыртуу",
    "close": "Жабуу",
    "back": "Артка",
    "next": "Кийинки",
    "submit": "Жөнөтүү",
    "reset": "Баштапкы абалга келтирүү",
    "confirm": "Ырастоо",
    "yes": "Ооба",
    "no": "Жок",
    "all": "Баары",
    "none": "Жок",
    "select": "Тандоо",
    "clear": "Тазалоо",
    "signIn": "Кирүү",
    "signOut": "Чыгуу",
    "profileSettings": "Профиль тууралоолору",
    "done": "Даяр"
  },
  "navigation": {
    "dashboard": "Башкы бет",
    "wallets": "Капчыктар",
    "transactions": "Операциялар",
    "scheduled": "Пландаштырылган",
    "analytics": "Аналитика",
    "signatures": "Колтамгалар",
    "contacts": "Дарек китепчеси",
    "audit": "Аудит журналы",
    "networks": "Тармактар",
    "profile": "Профиль",
    "settings": "Жөндөөлөр",
    "documents": "Документтер",
    "organizations": "Уюмдар",
    "billing": "Биллинг",
    "compliance": "Комплаенс",
    "users": "Колдонуучулар",
    "reports": "Отчёттор",
    "support": "Колдоо",
    "fiat": "Фиат операциялары",
    "partner": "Партнёр API"
  },
  "dashboard": {
    "title": "Башкы бет",
    "welcomeMessage": "ORGON'га кош келиңиз",
    "recentActivity": "Акыркы иш-чаралар",
    "noActivity": "Акыркы иш-чаралар жок",
    "lastSync": "Акыркы синхрондоштуруу",
    "stats": {
      "wallets": "Капчыктар",
      "totalWallets": "Бардык капчыктар",
      "transactions24h": "Операциялар (24с)",
      "pendingSignatures": "Күтүүдөгү колтамгалар",
      "pendingSignaturesHelp": "Сиздин колтамгаңызды күтүп турган операциялар",
      "networks": "Тармактар",
      "activeNetworks": "Активдүү тармактар"
    },
    "alerts": {
      "title": "Системдик билдирүүлөр",
      "allOperational": "Бардык системалар жакшы",
      "noAlerts": "Билдирүүлөр жок",
      "pendingSignatures": "{count, plural, one {# операция} other {# операциялар}} сиздин колтамгаңызды күтүп турат",
      "failedTransactions": "Акыркы 7 күндө {count, plural, one {# ийгиликсиз операция} other {# ийгиликсиз операциялар}}",
      "viewDetails": "Көбүрөөк →"
    },
    "activity": {
      "title": "Акыркы иш-чаралар",
      "lastEvents": "Акыркы {count, plural, one {# окуя} other {# окуялар}}",
      "noActivity": "Акыркы иш-чаралар жок",
      "noActivityDesc": "Сиздин акыркы операцияларыңыз жана колтамгаларыңыз бул жерде көрүнөт",
      "justNow": "Азыр эле",
      "minutesAgo": "{{count}}м мурун",
      "hoursAgo": "{{count}}с мурун",
      "daysAgo": "{{count}}к мурун",
      "viewDetails": "Көбүрөөк →",
      "viewAll": "Бардык иш-чаралар →"
    },
    "tokens": {
      "title": "Токендердин балансы",
      "subtitle": "Бардык капчыктар боюнча",
      "noBalances": "Токендердин балансы жок"
    },
    "actions": {
      "createWallet": "Капчык түзүү",
      "send": "Жөнөтүү"
    }
  },
  "auth": {
    "login": {
      "title": "ORGON'га кирүү",
      "subtitle": "Көп колтамгалуу капчыктарды башкаруу",
      "emailLabel": "Email",
      "emailPlaceholder": "admin@orgon.app",
      "passwordLabel": "Сырсөз",
      "passwordPlaceholder": "Сырсөзүңүздү киргизиңиз",
      "rememberMe": "Мени эстеп кал",
      "forgotPassword": "Сырсөзүңүздү унуттуңузбу?",
      "signInButton": "Кирүү",
      "noAccount": "Аккаунтуңуз жокпу?",
      "signUpLink": "Катталуу",
      "defaultAdmin": "Демейки: admin@orgon.app / admin123",
      "errors": {
        "invalidCredentials": "Туура эмес email же сырсөз",
        "accountLocked": "Аккаунт бөгөттөлгөн",
        "serverError": "Сервер катасы. Кийинчерээк аракет кылыңыз"
      },
      "quickLoginTitle": "Тез кирүү:",
      "quickLoginOr": "Же жогорудагы формада киргизиңиз",
      "testUser": "Test User",
      "adminUser": "Admin"
    },
    "register": {
      "title": "Аккаунт түзүү",
      "subtitle": "Капчыктарды башкаруу үчүн ORGON'го кошулуңуз",
      "fullNameLabel": "Толук аты",
      "fullNamePlaceholder": "Иван Иванов",
      "emailLabel": "Email",
      "emailPlaceholder": "sen@example.com",
      "passwordLabel": "Сырсөз",
      "passwordPlaceholder": "Кеминде 8 символ",
      "confirmPasswordLabel": "Сырсөздү ырастоо",
      "confirmPasswordPlaceholder": "Сырсөздү кайра киргизиңиз",
      "roleLabel": "Ролу",
      "roles": {
        "viewer": "Көрүүчү (окуу гана)",
        "signer": "Колтамга коюучу (колтамга коё алат)",
        "admin": "Администратор (толук кирүү)"
      },
      "termsAgree": "Мен макулмун",
      "termsOfService": "Колдонуу шарттары",
      "and": "жана",
      "privacyPolicy": "Купуялуулук саясаты",
      "createButton": "Аккаунт түзүү",
      "alreadyHaveAccount": "Аккаунтуңуз барбы?",
      "signInLink": "Кирүү",
      "errors": {
        "emailExists": "Email буга чейин колдонулган",
        "passwordMismatch": "Сырсөздөр дал келбейт",
        "passwordTooShort": "Сырсөз кеминде 8 символдон турушу керек",
        "invalidEmail": "Туура эмес email форматы"
      }
    },
    "logout": "Чыгуу",
    "profile": "Профиль",
    "profileSettings": "Профиль жөндөөлөрү"
  },
  "contacts": {
    "title": "Дарек китепчеси",
    "subtitle": "Көп колдонулуучу алуучуларды башкаруу",
    "addContact": "Контакт кошуу",
    "editContact": "Контактты түзөтүү",
    "deleteContact": "Контактты өчүрүү",
    "searchPlaceholder": "Аты же дареги боюнча издөө...",
    "noContacts": "Контакттар жок",
    "noContactsFiltered": "Чыпкага дал келген контакттар жок",
    "addFirstContact": "Биринчи контактыңызды кошуңуз",
    "deleteConfirm": "Бул контактты өчүрөсүзбү?",
    "categories": {
      "label": "Категория",
      "all": "Бардык категориялар",
      "personal": "Жеке",
      "business": "Бизнес",
      "exchange": "Биржалар",
      "other": "Башка"
    },
    "favorites": "Тандалмалар",
    "allContacts": "Бардык контакттар",
    "fields": {
      "name": "Аты",
      "namePlaceholder": "Контакт аты",
      "address": "Дарек",
      "addressPlaceholder": "Капчык дареги",
      "network": "Тармак",
      "networkPlaceholder": "Тармакты тандаңыз",
      "category": "Категория",
      "notes": "Эскертмелер",
      "notesPlaceholder": "Кошумча маалымат"
    },
    "actions": {
      "addToFavorites": "Тандалмаларга кошуу",
      "removeFromFavorites": "Тандалмалардан алып салуу"
    }
  },
  "analytics": {
    "title": "Аналитика",
    "subtitle": "Сиздин активдүүлүгүңүздүн аналитикасы",
    "daysFilter": "к",
    "days": {
      "7": "7 күн",
      "14": "14 күн",
      "30": "30 күн",
      "90": "90 күн"
    },
    "filters": {
      "title": "Талдоо мезгили"
    },
    "stats": {
      "totalWallets": "Бардык капчыктар",
      "active": "Активдүү",
      "inactive": "Активдүү эмес",
      "totalSignatures": "Бардык колтамгалар",
      "signed": "Колтамга коюлган",
      "pending": "Күтүүдө",
      "tokenTypes": "Токен түрлөрү",
      "activeTokens": "Портфелдеги активдүү токендер"
    },
    "charts": {
      "balanceHistory": "Баланс тарыхы",
      "tokenDistribution": "Токендердин бөлүштүрүлүшү",
      "transactionVolume": "Операциялардын көлөмү",
      "signatureStats": "Колтамгалардын статистикасы",
      "transactionActivity": "Операциялардын активдүүлүгү",
      "transactions": "Операциялар",
      "totalValue": "Жалпы сумма",
      "noData": "Маалымат жок",
      "network": "Тармак",
      "txCount": "операц."
    },
    "refreshButton": "Аналитиканы жаңыртуу",
    "loading": "Аналитика жүктөлүүдө...",
    "error": "Аналитика маалыматтарын жүктөп алуу мүмкүн эмес",
    "retry": "Кайталоо"
  },
  "audit": {
    "title": "Аудит журналы",
    "subtitle": "Активдүүлүк тарыхы жана системдик окуялар",
    "searchPlaceholder": "Логдорду издөө...",
    "searchButton": "Издөө",
    "clearFilters": "Тазалоо",
    "noLogs": "Логдор табылган жок",
    "stats": {
      "totalEvents": "Бардык окуялар",
      "last24h": "Акыркы 24 саатта",
      "actionTypes": "Аракет түрлөрү"
    },
    "filters": {
      "allActions": "Бардык аракеттер",
      "allResources": "Бардык ресурстар",
      "resources": {
        "transaction": "Операция",
        "wallet": "Капчык",
        "signature": "Колтамга",
        "contact": "Контакт",
        "user": "Колдонуучу"
      },
      "fromDate": "Датадан",
      "toDate": "Датага чейин",
      "selectFromDate": "Башталыш датасын тандаңыз",
      "selectToDate": "Аяктоо датасын тандаңыз"
    },
    "actions": {
      "create": "Түзүү",
      "update": "Жаңыртуу",
      "delete": "Өчүрүү",
      "sign": "Колтамга коюу",
      "reject": "Четке кагуу",
      "view": "Көрүү"
    },
    "fields": {
      "resourceId": "Ресурстун ID",
      "userId": "Колдонуучунун ID",
      "ipAddress": "IP дареги",
      "userAgent": "User Agent",
      "details": "Деталдар"
    },
    "refreshLogs": "Логдорду жаңыртуу",
    "detailModal": {
      "title": "Аудит жазуусунун деталдары",
      "coreInfo": "Негизги маалымат",
      "networkInfo": "Тармактык маалымат",
      "logId": "Жазуунун ID"
    }
  },
  "scheduled": {
    "title": "Пландаштырылган операциялар",
    "subtitle": "Автоматтык төлөмдөрдү башкаруу",
    "noTransactions": "Пландаштырылган операциялар жок",
    "filters": {
      "title": "Статус боюнча чыпкалар",
      "pending": "Күтүүдө",
      "sent": "Жөнөтүлгөн",
      "failed": "Ката",
      "cancelled": "Жокко чыгарылган"
    },
    "fields": {
      "token": "Токен",
      "value": "Сумма",
      "recipient": "Алуучу",
      "scheduledAt": "Пландаштырылган убакыт",
      "recurrence": "Кайталануу",
      "nextRun": "Кийинки иштөө",
      "sentAt": "Жөнөтүлгөн убакыт",
      "transactionId": "Операциянын ID",
      "error": "Ката",
      "info": "Маалымат"
    },
    "actions": {
      "cancel": "Жокко чыгаруу",
      "cancelConfirm": "Бул пландаштырылган операцияны жокко чыгарасызбы?",
      "cancelFailed": "Операцияны жокко чыгаруу мүмкүн эмес"
    },
    "status": {
      "pending": "Күтүүдө",
      "sent": "Жөнөтүлдү",
      "failed": "Ката",
      "cancelled": "Жокко чыгарылды"
    }
  },
  "settings": {
    "title": "Жөндөөлөр",
    "systemStatus": {
      "title": "Системанын статусу",
      "orgonBackend": "ORGON Backend",
      "safinaApi": "Safina API",
      "lastSync": "Акыркы синхрондоштуруу"
    },
    "authentication": {
      "title": "Аутентификация",
      "subtitle": "API кирүү үчүн Bearer токени",
      "placeholder": "Администратор токенин киргизиңиз",
      "saveButton": "Токенди сактоо"
    },
    "keyManagement": {
      "title": "Ачкычтарды башкаруу",
      "link": "EC колтамга ачкычтарын башкаруу"
    },
    "twofa": {
      "title": "Эки факторлуу аутентификация",
      "description": "Аккаунтуңузга кошумча коопсуздук деңгээлин кошуңуз",
      "setupTitle": "2FA тууралоо",
      "enabled": "Иштетилген",
      "enable": "2FA иштетүү",
      "disable": "2FA өчүрүү",
      "verify": "Текшерүү",
      "download": "Жүктөп алуу",
      "scanQR": "Бул QR кодду Google Authenticator же Authy колдонмосунда скандаңыз",
      "manualEntry": "Же ачкычты кол менен киргизиңиз:",
      "verificationCode": "Ырастоо коду",
      "enterCode": "Колдонмодон 6 сандуу кодду киргизиңиз",
      "enterCodeToDisable": "2FA өчүрүү үчүн ырастоо кодун киргизиңиз",
      "saveBackupCodes": "Камдык кодторду сактаңыз",
      "backupCodesWarning": "Бул кодторду коопсуз жерде сактаңыз. Аутентификатор колдонмосуна кирүү мүмкүнчүлүгүн жоготсоңуз керек болот.",
      "backupCodesTotal": "Бардыгы кодтор",
      "backupCodesRemaining": "Калган кодтор",
      "regenerateBackupCodes": "Жаңы камдык кодторду түзүү",
      "whyEnable": "Эмне үчүн 2FA иштетүү керек?",
      "securityBenefit": "Эки факторлуу аутентификация сыр сөзүңүздү билген адам болсо да аккаунтуңузду коргойт.",
      "prompts": {
        "enterCode": "Жаңы камдык кодторду түзүү үчүн колдонмодон ырастоо кодун киргизиңиз:"
      },
      "errors": {
        "setupFailed": "2FA тууралоону баштоо мүмкүн эмес",
        "invalidCode": "Туура эмес код. Код 6 саннан турушу керек.",
        "verificationFailed": "Туура эмес ырастоо коду",
        "disableFailed": "2FA өчүрүү мүмкүн эмес",
        "regenerateFailed": "Жаңы камдык кодторду түзүү мүмкүн эмес"
      },
      "backupCodeHelp": "Аутентификация колдонмосун жоготтуңузбу?\nКамдоо коддорунун биринин колдонуңуз."
    },
    "sections": {
      "profile": "Профиль",
      "security": "Коопсуздук",
      "apiKeys": "API Ачкычтар",
      "notifications": "Билдирмелер",
      "theme": "Тема",
      "language": "Тил",
      "limits": "Чектөөлөр",
      "backup": "Резервдик көчүрмө",
      "about": "Программа жөнүндө"
    },
    "profile": {
      "title": "Профиль жөндөөлөрү",
      "changeAvatar": "Аватарды өзгөртүү",
      "fullName": "Толук аты",
      "email": "Email дареги",
      "role": "Ролу",
      "saveChanges": "Өзгөртүүлөрдү сактоо"
    },
    "security": {
      "title": "Коопсуздук жөндөөлөрү",
      "twoFactor": "Эки факторлуу аутентификация",
      "twoFactorDesc": "Кошумча коргоо деңгээлин кошуңуз",
      "changePassword": "Сырсөздү өзгөртүү",
      "currentPassword": "Учурдагы сырсөз",
      "newPassword": "Жаңы сырсөз",
      "confirmPassword": "Жаңы сырсөздү ырастоо",
      "updatePassword": "Сырсөздү жаңыртуу",
      "activeSessions": "Активдүү сеанстар",
      "activeSessionsCount": "активдүү сеанстар",
      "logoutAllSessions": "Бардык сеанстардан чыгуу"
    },
    "apiKeys": {
      "title": "API Ачкычтар",
      "createNew": "Жаңы ачкыч түзүү",
      "revoke": "Жокко чыгаруу",
      "created": "Түзүлгөн",
      "lastUsed": "Акыркы колдонулуш"
    },
    "notifications": {
      "title": "Билдирмелер жөндөөлөрү",
      "email": "Email билдирмелер",
      "emailDesc": "Email аркылуу билдирмелерди алуу",
      "push": "Push билдирмелер",
      "pushDesc": "Браузерде push билдирмелерди алуу",
      "telegram": "Telegram билдирмелер",
      "telegramDesc": "Telegram бот аркылуу билдирмелерди алуу",
      "transactions": "Транзакциялар жөнүндө билдирүү",
      "transactionsDesc": "Жаңы транзакциялар жөнүндө билдирүү",
      "security": "Коопсуздук билдирүүлөрү",
      "securityDesc": "Коопсуздук окуялары жөнүндө билдирүү",
      "weekly": "Жума сайын отчет",
      "weeklyDesc": "Активдүүлүктүн жума сайын кыскача маалыматын жөнөтүү"
    },
    "theme": {
      "title": "Тема жөндөөлөрү",
      "light": "Жарык",
      "dark": "Караңгы",
      "auto": "Авто"
    },
    "language": {
      "title": "Интерфейс тили"
    },
    "limits": {
      "title": "Аккаунт чектөөлөрү",
      "wallets": "Капчыктар",
      "monthlyVolume": "Айлык көлөмү",
      "transaction": "Транзакция чектөөлөрү",
      "maxTransactionSize": "Макс. транзакция өлчөмү",
      "upgrade": "Тарифти жакшыртуу"
    },
    "backup": {
      "title": "Маалыматтарды экспорттоо жана резервдик көчүрмө",
      "description": "Резервдик көчүрмө же миграция үчүн маалыматтарды экспорттоо",
      "exportWallets": "Капчыктарды экспорттоо",
      "exportWalletsDesc": "Капчык даректерин жана метамаалыматтарын жүктөп алуу",
      "exportTransactions": "Транзакцияларды экспорттоо",
      "exportTransactionsDesc": "Транзакциялардын тарыхын CSV форматында жүктөп алуу",
      "exportContacts": "Байланыштарды экспорттоо",
      "exportContactsDesc": "Даректер китепчесин JSON форматында жүктөп алуу"
    },
    "about": {
      "title": "ORGON программасы жөнүндө",
      "version": "Версия",
      "backend": "Backend абалы",
      "safinaApi": "Safina API абалы",
      "lastSync": "Акыркы синхрондоштуруу",
      "documentation": "Документация",
      "website": "Веб-сайт",
      "support": "Колдоо",
      "rights": "Бардык укуктар корголгон."
    }
  },
  "profile": {
    "title": "Профиль",
    "description": "Профилиңизди жана коопсуздук параметрлерин башкаруу",
    "memberSince": "Колдонуучу",
    "password": {
      "title": "Сырсөз",
      "description": "Кирүү сырсөзүн өзгөртүү",
      "change": "Сырсөздү өзгөртүү",
      "cancel": "Жокко чыгаруу",
      "current": "Учурдагы сырсөз",
      "new": "Жаңы сырсөз",
      "confirm": "Жаңы сырсөздү ырастаңыз",
      "save": "Сырсөздү сактоо",
      "mismatch": "Сырсөздөр дал келбейт",
      "tooShort": "Сырсөз кеминде 8 символдон турушу керек",
      "success": "Сырсөз ийгиликтүү өзгөртүлдү",
      "failed": "Сырсөздү өзгөртүү мүмкүн болбоду"
    },
    "sessions": {
      "title": "Активдүү сеанстар",
      "description": "Аккаунтка кирүү мүмкүнчүлүгү бар түзмөктөрдү башкаруу",
      "current": "Учурдагы сеанс",
      "mobile": "Мобилдик түзмөк",
      "desktop": "Компьютер",
      "lastActive": "Акыркы активдүүлүк",
      "revoke": "Токтотуу",
      "confirmRevoke": "Сиз бул сеансты токтотууга ишенесизби?",
      "noSessions": "Активдүү сеанстар жок"
    },
    "language": {
      "title": "Интерфейс тили",
      "description": "ORGON интерфейси үчүн тилди тандаңыз",
      "active": "Активдүү"
    },
    "theme": {
      "title": "Интерфейс темасы",
      "description": "ORGON интерфейсинин көрүнүшүн тууралаңыз",
      "light": "Жарык",
      "dark": "Караңгы",
      "system": "Системалык",
      "active": "Активдүү"
    }
  },
  "wallets": {
    "title": "Капчыктар",
    "count": "{{count}} капчыктар",
    "exportButton": "Экспорт CSV",
    "exporting": "Экспорттолууда...",
    "table": {
      "favorite": "Тандалмалар",
      "name": "Аты / Белгиси",
      "address": "Дарек",
      "network": "Тармак",
      "tokens": "Токендер",
      "info": "Маалымат",
      "pending": "Күтүүдө...",
      "noWallets": "Капчыктар табылган жок. Биринчисин түзүңүз."
    }
  },
  "transactions": {
    "title": "Операциялар",
    "count": "{{count}} операциялар",
    "filtered": "(чыпкаланган)",
    "exportButton": "Экспорт CSV",
    "exporting": "Экспорттолууда...",
    "failedToLoad": "Операцияларды жүктөп алуу мүмкүн эмес",
    "table": {
      "unid": "UNID",
      "to": "Кимге",
      "amount": "Сумма",
      "status": "Статус",
      "txHash": "TX Hash",
      "date": "Дата",
      "noTransactions": "Операциялар табылган жок"
    },
    "filters": {
      "title": "Чыпкалар",
      "wallet": "Капчык",
      "allWallets": "Бардык капчыктар",
      "status": "Статус",
      "allStatuses": "Бардык статустар",
      "network": "Тармак",
      "allNetworks": "Бардык тармактар",
      "fromDate": "Башталыш дата",
      "toDate": "Аяктоо дата",
      "applyButton": "Чыпкаларды колдонуу",
      "clearButton": "Тазалоо"
    },
    "statuses": {
      "pending": "Күтүүдө",
      "signed": "Колтамга коюлган",
      "confirmed": "Ырасталган",
      "rejected": "Четке кагылган",
      "failed": "Ката"
    }
  },
  "networks": {
    "title": "Тармактар",
    "id": "ID",
    "supportedTokens": "Колдоого алынган токендер"
  },
  "signatures": {
    "title": "Колтамгалар",
    "notifications": {
      "signed": "Операция {txId}... ийгиликтүү колтамга коюлду",
      "rejected": "Операция {txId}... четке кагылды",
      "signFailed": "Операцияга колтамга коюу мүмкүн эмес",
      "rejectFailed": "Операцияны четке кагуу мүмкүн эмес",
      "loadFailed": "Колтамгаларды жүктөп алуу мүмкүн эмес. Кайра аракет кылыңыз."
    },
    "stats": {
      "title": "Колтамга статистикасы",
      "pendingNow": "Азыр күтүүдө",
      "signed24h": "Колтамга коюлган (24с)",
      "rejected24h": "Четке кагылган (24с)",
      "totalSigned": "Баары колтамга коюлган"
    },
    "pending": {
      "title": "Күтүүдөгү колтамгалар",
      "count": "({{count}})",
      "table": {
        "token": "Токен",
        "to": "Кимге",
        "value": "Суммасы",
        "age": "Жашы",
        "progress": "Прогресс",
        "actions": "Аракеттер",
        "signButton": "Колтамга коюу",
        "signing": "Колтамга коюлууда...",
        "rejectButton": "Четке кагуу",
        "loadStatusButton": "Статусту жүктөө",
        "noSignatures": "Колтамга күтүп турган операциялар жок"
      },
      "rejectDialog": {
        "title": "Операцияны четке кагуу",
        "reasonLabel": "Четке кагуу себеби",
        "reasonPlaceholder": "Себебин киргизиңиз...",
        "cancelButton": "Жокко чыгаруу",
        "confirmButton": "Четке кагуу"
      }
    },
    "history": {
      "title": "Акыркы тарых",
      "table": {
        "transaction": "Операция",
        "action": "Аракет",
        "signer": "Колтамга коюучу",
        "timestamp": "Убакыт",
        "reason": "Себеп",
        "noHistory": "Колтамгалардын тарыхы бош"
      },
      "actions": {
        "signed": "Колтамга коюлган",
        "rejected": "Четке кагылган"
      }
    }
  },
  "metadata": {
    "title": "ORGON - Капчыктарды башкаруу",
    "description": "Safina Pay аркылуу криптовалюта капчыктарын башкаруу"
  },
  "billing": {
    "title": "Эсеп жана жазылуулар",
    "currentPlan": "Учурдагы план",
    "month": "ай",
    "year": "жыл",
    "renewalDate": "Жаңылануу күнү",
    "autoRenew": "Автоматтык жаңылануу",
    "enabled": "Күйгүзүлгөн",
    "disabled": "Өчүрүлгөн",
    "upgradePlan": "Планды жогорулатуу",
    "cancelSubscription": "Жазылууну токтотуу",
    "noSubscription": "Жигердүү жазылуу жок",
    "choosePlan": "Планды тандаңыз",
    "outstandingBalance": "Карыз",
    "totalSpend": "Бардык чыгашалар",
    "recentInvoices": "Акыркы эсептер",
    "invoiceNumber": "Эсеп №",
    "issueDate": "Чыгарылган күн",
    "dueDate": "Төлөм мөөнөтү",
    "amount": "Сумма",
    "status": "Абал",
    "actions": "Аракеттер",
    "payNow": "Төлөө",
    "paid": "Төлөнгөн",
    "noInvoices": "Эсептер жок",
    "paymentHistory": "Төлөмдөр тарыхы",
    "noPayments": "Төлөмдөр жок",
    "select": "Тандоо",
    "cancelConfirm": "Жазылууну токтотууну каалайсызбы?"
  },
  "branding": {
    "title": "Брендинг жана White Label",
    "logo": "Логотип",
    "logoUrl": "Логотиптин URL",
    "colors": "Түстөр",
    "primaryColor": "Негизги түс",
    "secondaryColor": "Кошумча түс",
    "accentColor": "Акцент түсү",
    "platformInfo": "Платформа жөнүндө",
    "platformName": "Платформанын аты",
    "tagline": "Девиз",
    "supportEmail": "Колдоо email",
    "preview": "Алдын ала көрүү",
    "previewButton": "Негизги баскыч",
    "previewSecondary": "Кошумча баскыч"
  },
  "compliance": {
    "title": "Комплаенс жана жөнгө салуу",
    "kycRecords": "KYC жазуулары",
    "amlAlerts": "AML эскертүүлөр",
    "reports": "Отчёттор",
    "recentKYC": "Акыркы KYC жазуулары",
    "noKYC": "KYC жазуулары жок",
    "amlAlertsTitle": "AML эскертүүлөр",
    "noAlerts": "Эскертүүлөр жок",
    "reportsTitle": "Жөнгө салуучу үчүн отчёттор",
    "noReports": "Отчёттор жок"
  },
  "organizations": {
    "title": "Уюмдар",
    "newOrganization": "Жаңы уюм",
    "selectOrganization": "Уюмду тандаңыз",
    "manageOrganizations": "Уюмдарды башкаруу",
    "allOrganizations": "Бардык уюмдар",
    "overview": "Жалпы көрүнүш",
    "members": "Катышуучулар",
    "settings": "Жөндөөлөр",
    "details": "Уюмдун чоо-жайы",
    "addMember": "Катышуучу кошуу",
    "maxWallets": "Эң көп капчык",
    "maxVolume": "Эң көп көлөм",
    "kycRequired": "KYC милдеттүү",
    "created": "Түзүлгөн",
    "status": {
      "active": "Жигердүү",
      "suspended": "Токтотулган",
      "closed": "Жабылган"
    },
    "license": {
      "free": "Акысыз",
      "pro": "Профессионал",
      "enterprise": "Корпоративдик"
    },
    "role": {
      "admin": "Администратор",
      "operator": "Оператор",
      "viewer": "Көзөмөлчү"
    }
  }
}
```

---

# 7. Что НЕ доделано (открытые направления)

- 25+ authenticated pages получили автоматический token-sweep, но
  сохранили старую shadcn-card геометрию: `/billing`, `/audit`,
  `/analytics`, `/organizations*`, `/partner`, `/compliance/*`,
  `/settings/*`, `/profile`, `/users`, `/networks`, `/reports`,
  `/documents`, `/help`, `/support`, `/fiat`. Им нужен такой же плотный
  Crimson Ledger макет (eyebrow + KPI tiles + bordered table sections)
  вместо `<Card>` боксов с padding.
- Aceternity-компоненты ещё используются: `AnimatedModal/Input` в
  Contacts modal, `HoverBorderGradient` / `SkeletonCard` / `ButtonHover`
  на `/analytics`. Их visual conflicts с Crimson Ledger.
- Logo wordmark: SVG переписан на `fill=currentColor`, но компоненты
  ещё рендерят `orgon-icon.png` (raster) + текст "ASYSTEM / ORGON".
  Хотелось бы inline `<LogoWordmark>` компонент.
- Mobile sidebar drawer: desktop sidebar анимирует ширину 64↔240 на
  hover. Mobile сейчас `hidden md:flex` — drawer'а нет.
- Tooltip / HelpTooltip имеют hardcoded `bg-slate-950/50`.
- KYC/KYB страницы сохранили много bespoke patterns.

## Ограничения, которые нельзя нарушать

- API контракты `src/lib/api.ts` зафиксированы — shape не меняется.
- Demo-данные сидятся `backend/migrations/013_demo_data.sql` +
  `014_wallet_labels.sql`.
- Theme persistence — cookie `orgon_theme`, читается на сервере в
  `app/layout.tsx` через `await cookies()`.
- Default theme — **light**.
- i18n: ключи в трёх языках (ru/en/ky) должны быть синхронизированы.
