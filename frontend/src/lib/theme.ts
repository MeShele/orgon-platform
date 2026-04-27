/**
 * ORGON Design System - Centralized Theme Configuration
 * 
 * Single source of truth for colors, typography, spacing, and components.
 * Use these constants throughout the app for consistency.
 */

// ==================== Color Palette ====================

export const colors = {
  // Primary brand colors
  primary: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',  // Main primary
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
  },
  
  // Success states
  success: {
    50: '#f0fdf4',
    100: '#dcfce7',
    200: '#bbf7d0',
    300: '#86efac',
    400: '#4ade80',
    500: '#22c55e',  // Main success
    600: '#16a34a',
    700: '#15803d',
    800: '#166534',
    900: '#14532d',
  },
  
  // Warning states
  warning: {
    50: '#fefce8',
    100: '#fef9c3',
    200: '#fef08a',
    300: '#fde047',
    400: '#facc15',
    500: '#eab308',  // Main warning
    600: '#ca8a04',
    700: '#a16207',
    800: '#854d0e',
    900: '#713f12',
  },
  
  // Error/Danger states
  danger: {
    50: '#fef2f2',
    100: '#fee2e2',
    200: '#fecaca',
    300: '#fca5a5',
    400: '#f87171',
    500: '#ef4444',  // Main danger
    600: '#dc2626',
    700: '#b91c1c',
    800: '#991b1b',
    900: '#7f1d1d',
  },
  
  // Neutral/Gray scale
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  },
  
  // Dark mode specific
  dark: {
    bg: {
      primary: '#0f172a',    // Main background
      secondary: '#1e293b',  // Cards, panels
      tertiary: '#334155',   // Hover states
    },
    text: {
      primary: '#f1f5f9',    // Main text
      secondary: '#cbd5e1',  // Secondary text
      muted: '#94a3b8',      // Muted text
    },
    border: {
      primary: '#334155',
      secondary: '#1e293b',
    }
  },
  
  // Network-specific colors
  networks: {
    safina: '#3b82f6',
    ethereum: '#627eea',
    polygon: '#8247e5',
    bsc: '#f3ba2f',
    avalanche: '#e84142',
  }
} as const;

// ==================== Typography ====================

export const typography = {
  // Font families
  fontFamily: {
    sans: 'var(--font-inter), system-ui, -apple-system, sans-serif',
    mono: 'var(--font-mono), Menlo, Monaco, "Courier New", monospace',
  },
  
  // Font sizes (with line heights)
  fontSize: {
    xs: { size: '0.75rem', lineHeight: '1rem' },      // 12px
    sm: { size: '0.875rem', lineHeight: '1.25rem' },  // 14px
    base: { size: '1rem', lineHeight: '1.5rem' },     // 16px
    lg: { size: '1.125rem', lineHeight: '1.75rem' },  // 18px
    xl: { size: '1.25rem', lineHeight: '1.75rem' },   // 20px
    '2xl': { size: '1.5rem', lineHeight: '2rem' },    // 24px
    '3xl': { size: '1.875rem', lineHeight: '2.25rem' }, // 30px
    '4xl': { size: '2.25rem', lineHeight: '2.5rem' },   // 36px
    '5xl': { size: '3rem', lineHeight: '1' },           // 48px
  },
  
  // Font weights
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
} as const;

// ==================== Spacing ====================

export const spacing = {
  // Base spacing unit (4px)
  unit: 4,
  
  // Common spacing values
  xs: '0.5rem',   // 8px
  sm: '0.75rem',  // 12px
  md: '1rem',     // 16px
  lg: '1.5rem',   // 24px
  xl: '2rem',     // 32px
  '2xl': '3rem',  // 48px
  '3xl': '4rem',  // 64px
  
  // Layout spacing
  page: {
    padding: 'p-4 sm:p-6 lg:p-8',  // Responsive page padding
    gap: 'space-y-6',              // Vertical gap between sections
  },
  
  // Card spacing
  card: {
    padding: 'p-4 sm:p-6',
    gap: 'space-y-4',
  },
} as const;

// ==================== Border Radius ====================

export const borderRadius = {
  none: '0',
  sm: '0.25rem',    // 4px
  DEFAULT: '0.5rem', // 8px
  md: '0.5rem',     // 8px
  lg: '0.75rem',    // 12px
  xl: '1rem',       // 16px
  '2xl': '1.5rem',  // 24px
  full: '9999px',   // Fully rounded
} as const;

// ==================== Shadows ====================

export const shadows = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
  inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
  none: 'none',
} as const;

// ==================== Component Styles ====================

/**
 * Pre-defined component style classes.
 * Use these for consistent component styling.
 */
export const components = {
  // Button variants
  button: {
    base: 'inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed',
    
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 dark:bg-blue-500 dark:hover:bg-blue-600',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500 dark:bg-gray-700 dark:text-gray-100 dark:hover:bg-gray-600',
    success: 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500 dark:bg-green-500 dark:hover:bg-green-600',
    warning: 'bg-yellow-500 text-white hover:bg-yellow-600 focus:ring-yellow-500 dark:bg-yellow-600 dark:hover:bg-yellow-700',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500 dark:bg-red-500 dark:hover:bg-red-600',
    ghost: 'text-gray-700 hover:bg-gray-100 focus:ring-gray-500 dark:text-gray-300 dark:hover:bg-gray-800',
    
    // Sizes
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  },
  
  // Input styles
  input: {
    base: 'w-full px-4 py-2 border rounded-lg transition-colors focus:outline-none focus:ring-2',
    default: 'border-gray-300 bg-white text-gray-900 focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:focus:border-blue-400',
    error: 'border-red-300 bg-red-50 text-red-900 focus:border-red-500 focus:ring-red-500 dark:border-red-600 dark:bg-red-900/20 dark:text-red-100',
  },
  
  // Card styles
  card: {
    base: 'rounded-xl border shadow-sm transition-all',
    default: 'bg-white border-slate-200 dark:bg-slate-900/40 dark:border-slate-800 dark:shadow-none',
    hover: 'hover:border-slate-300 hover:shadow-md dark:hover:bg-slate-900/60',
    padding: 'p-4 sm:p-6',
  },
  
  // Badge styles
  badge: {
    base: 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
    primary: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    success: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
    danger: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    gray: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  },
  
  // Alert/Banner styles
  alert: {
    base: 'rounded-lg p-4 text-sm',
    info: 'bg-blue-50 border border-blue-200 text-blue-700 dark:bg-blue-900/20 dark:border-blue-500/20 dark:text-blue-300',
    success: 'bg-green-50 border border-green-200 text-green-700 dark:bg-green-900/20 dark:border-green-500/20 dark:text-green-300',
    warning: 'bg-yellow-50 border border-yellow-200 text-yellow-700 dark:bg-yellow-900/20 dark:border-yellow-500/20 dark:text-yellow-300',
    danger: 'bg-red-50 border border-red-200 text-red-700 dark:bg-red-900/20 dark:border-red-500/20 dark:text-red-300',
  },
  
  // Table styles
  table: {
    wrapper: 'overflow-x-auto rounded-lg border border-border',
    base: 'min-w-full divide-y divide-gray-200 dark:divide-gray-700',
    header: 'bg-gray-50 dark:bg-gray-800',
    headerCell: 'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400',
    body: 'bg-white divide-y divide-gray-200 dark:bg-gray-900 dark:divide-gray-700',
    cell: 'px-6 py-4 whitespace-nowrap text-sm text-foreground',
    row: 'hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors',
  },
  
  // Modal/Dialog styles
  modal: {
    overlay: 'fixed inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm z-50',
    container: 'fixed inset-0 z-50 flex items-center justify-center p-4',
    content: 'bg-card rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto',
    header: 'px-6 py-4 border-b border-border',
    body: 'px-6 py-4',
    footer: 'px-6 py-4 border-t border-border flex justify-end gap-3',
  },
} as const;

// ==================== Utility Classes ====================

/**
 * Common utility class combinations for frequent patterns.
 */
export const utils = {
  // Text styles
  text: {
    heading: 'text-foreground font-semibold',
    body: 'text-foreground',
    muted: 'text-muted-foreground',
    caption: 'text-xs text-muted-foreground',
  },
  
  // Layout
  container: 'max-w-7xl mx-auto',
  section: 'space-y-6',
  
  // Transitions
  transition: {
    default: 'transition-colors duration-200',
    all: 'transition-all duration-200',
    fast: 'transition-all duration-150',
    slow: 'transition-all duration-300',
  },
  
  // Focus states
  focus: 'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900',
} as const;

// ==================== Helper Functions ====================

/**
 * Get color with opacity (for Tailwind arbitrary values).
 * Example: getColorWithOpacity(colors.primary[500], 0.5) => 'rgb(59 130 246 / 0.5)'
 */
export function getColorWithOpacity(color: string, opacity: number): string {
  // Convert hex to rgb
  const hex = color.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  
  return `rgb(${r} ${g} ${b} / ${opacity})`;
}

/**
 * Combine class names (simple cn utility).
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

// ==================== Export Default Theme ====================

export const theme = {
  colors,
  typography,
  spacing,
  borderRadius,
  shadows,
  components,
  utils,
} as const;

export default theme;
