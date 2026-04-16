/**
 * ORGON Page Layout Standards
 * Unified layout system based on Dashboard design
 * Apply to ALL pages for consistency
 */

import { designTokens } from './design-tokens';

/**
 * Standard page layout classes
 * Use these utility functions instead of hardcoding Tailwind classes
 */
export const pageLayout = {
  /**
   * Main page container
   * Usage: <div className={pageLayout.container}>
   */
  container: 'space-y-4 p-2 sm:p-4 md:p-6 lg:p-8',

  /**
   * Page header with title and description
   * Usage: <div className={pageLayout.header.wrapper}>
   */
  header: {
    wrapper: 'space-y-2',
    title: 'text-2xl font-bold text-slate-900 dark:text-white sm:text-3xl',
    description: 'text-sm text-slate-600 dark:text-slate-400',
    subtitle: 'text-xs text-slate-500 dark:text-slate-400',
  },

  /**
   * Action bar (filters, buttons, etc.)
   * Usage: <div className={pageLayout.actionBar}>
   */
  actionBar: 'flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between',

  /**
   * Cards grid layouts
   * Usage: <div className={pageLayout.grid.cols3}>
   */
  grid: {
    cols1: 'grid gap-3 sm:gap-4 md:gap-6',
    cols2: 'grid gap-3 sm:gap-4 md:gap-6 md:grid-cols-2',
    cols3: 'grid gap-3 sm:gap-4 md:gap-6 lg:grid-cols-3',
    cols4: 'grid gap-3 sm:gap-4 md:gap-6 md:grid-cols-2 lg:grid-cols-4',
    auto: 'grid gap-3 sm:gap-4 md:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
  },

  /**
   * Stats cards layout (Dashboard-style)
   * Usage: <div className={pageLayout.stats}>
   */
  stats: 'grid gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-4',

  /**
   * Empty states
   * Usage: <div className={pageLayout.empty.wrapper}>
   */
  empty: {
    wrapper: 'flex flex-col items-center justify-center py-12 text-center',
    icon: 'mx-auto mb-4 text-6xl text-slate-400 dark:text-slate-600',
    title: 'text-lg font-semibold text-slate-900 dark:text-white',
    description: 'mt-2 text-sm text-slate-600 dark:text-slate-400',
    action: 'mt-6',
  },

  /**
   * Loading spinner
   * Usage: <div className={pageLayout.loading}>
   */
  loading: 'flex items-center justify-center py-12',

  /**
   * Error message
   * Usage: <div className={pageLayout.error}>
   */
  error: 'rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-400',

  /**
   * Success message
   * Usage: <div className={pageLayout.success}>
   */
  success: 'rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-700 dark:border-green-500/20 dark:bg-green-500/10 dark:text-green-400',

  /**
   * Warning message
   * Usage: <div className={pageLayout.warning}>
   */
  warning: 'rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-700 dark:border-yellow-500/20 dark:bg-yellow-500/10 dark:text-yellow-400',

  /**
   * Info message
   * Usage: <div className={pageLayout.info}>
   */
  info: 'rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-700 dark:border-blue-500/20 dark:bg-blue-500/10 dark:text-blue-400',
} as const;

/**
 * Standard spacing values (based on Dashboard)
 */
export const spacing = {
  // Page padding
  page: {
    mobile: 'p-2',      // 8px
    tablet: 'sm:p-4',   // 16px
    desktop: 'md:p-6',  // 24px
    desktopLg: 'lg:p-8', // 32px
    all: 'p-2 sm:p-4 md:p-6 lg:p-8',
  },

  // Card padding
  card: {
    sm: 'p-4',          // 16px
    md: 'p-6',          // 24px
    lg: 'p-8',          // 32px
  },

  // Section gaps
  gap: {
    sm: 'gap-4',        // 16px
    md: 'gap-6',        // 24px
    lg: 'gap-8',        // 32px
  },

  // Stack spacing (vertical)
  stack: {
    sm: 'space-y-4',    // 16px
    md: 'space-y-6',    // 24px
    lg: 'space-y-8',    // 32px
  },
} as const;

/**
 * Standard button styles (based on Button component)
 */
export const buttonStyles = {
  primary: 'inline-flex items-center justify-center gap-2 rounded-lg border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-slate-900',
  
  secondary: 'inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:focus:ring-offset-slate-900',
  
  danger: 'inline-flex items-center justify-center gap-2 rounded-lg border border-transparent bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-slate-900',
  
  ghost: 'inline-flex items-center justify-center gap-2 rounded-lg border border-transparent px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:text-slate-300 dark:hover:bg-slate-800 dark:focus:ring-offset-slate-900',
} as const;

/**
 * Standard badge/pill styles
 */
export const badgeStyles = {
  default: 'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium',
  
  variants: {
    blue: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    green: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    red: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    yellow: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    slate: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400',
  },
} as const;

/**
 * Standard table styles
 */
export const tableStyles = {
  wrapper: 'overflow-hidden rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900',
  table: 'min-w-full divide-y divide-slate-200 dark:divide-slate-800',
  thead: 'bg-slate-50 dark:bg-slate-800/50',
  th: 'px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400',
  tbody: 'divide-y divide-slate-200 bg-white dark:divide-slate-800 dark:bg-slate-900',
  td: 'px-4 py-3 text-sm text-slate-900 dark:text-slate-100',
  tdMuted: 'px-4 py-3 text-sm text-slate-600 dark:text-slate-400',
} as const;
