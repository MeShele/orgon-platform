'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { useTranslations } from '@/hooks/useTranslations';
import { SafeIcon as Icon } from '@/components/SafeIcon';
import { designTokens } from '@/lib/design-tokens';

interface ProfileCardProps {
  /** Collapsed sidebar mode (mobile or collapsed desktop) */
  collapsed?: boolean;
  /** Mobile mode - shows in hamburger menu */
  mobile?: boolean;
}

export function ProfileCard({ collapsed = false, mobile = false }: ProfileCardProps) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const t = useTranslations('common');
  const [menuOpen, setMenuOpen] = useState(false);

  if (!user) {
    return (
      <Link
        href="/login"
        className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 text-sm font-medium text-slate-900 transition-colors hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900/50 dark:text-white dark:hover:bg-slate-800"
      >
        <Icon icon="solar:login-2-linear" className="text-xl" />
        {!collapsed && <span>{t('signIn')}</span>}
      </Link>
    );
  }

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  const getRoleBadgeColor = (role: string) => {
    const colors = {
      admin: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
      signer: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      viewer: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400',
    };
    return colors[role as keyof typeof colors] || colors.viewer;
  };

  // Collapsed mode - only avatar
  if (collapsed) {
    return (
      <div className="relative">
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 text-blue-600 transition-all hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/50"
        >
          <Icon icon="solar:user-circle-bold" className="text-2xl" />
        </button>

        {menuOpen && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => setMenuOpen(false)}
            />
            <div className="absolute bottom-full left-0 z-50 mb-2 w-64 rounded-lg border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900">
              <div className="border-b border-slate-200 p-4 dark:border-slate-800">
                <div className="mb-2 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
                    <Icon icon="solar:user-circle-bold" className="text-2xl" />
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">
                      {user.full_name}
                    </p>
                    <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                      {user.email}
                    </p>
                  </div>
                </div>
                <span
                  className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${getRoleBadgeColor(
                    user.role
                  )}`}
                >
                  {user.role.toUpperCase()}
                </span>
              </div>

              <div className="p-2">
                <Link
                  href="/profile"
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  <Icon icon="solar:settings-linear" className="text-lg" />
                  {t('profileSettings')}
                </Link>

                <button
                  onClick={handleLogout}
                  className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                >
                  <Icon icon="solar:logout-2-linear" className="text-lg" />
                  {t('signOut')}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    );
  }

  // Full mode - card with details
  return (
    <div className="relative">
      <button
        onClick={() => setMenuOpen(!menuOpen)}
        className="w-full rounded-lg border border-slate-200 bg-white p-3 text-left transition-all hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900/50 dark:hover:bg-slate-800"
      >
        <div className="mb-2 flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
            <Icon icon="solar:user-circle-bold" className="text-2xl" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">
              {user.full_name}
            </p>
            <p className="truncate text-xs text-slate-500 dark:text-slate-400">
              {user.email}
            </p>
          </div>
          <Icon
            icon="solar:alt-arrow-up-linear"
            className={`text-lg text-slate-400 transition-transform ${
              menuOpen ? 'rotate-180' : ''
            }`}
          />
        </div>
        <span
          className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${getRoleBadgeColor(
            user.role
          )}`}
        >
          {user.role.toUpperCase()}
        </span>
      </button>

      {menuOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setMenuOpen(false)}
          />
          <div className="absolute bottom-full left-0 right-0 z-50 mb-2 rounded-lg border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900">
            <div className="p-2">
              <Link
                href="/profile"
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <Icon icon="solar:settings-linear" className="text-lg" />
                {t('profileSettings')}
              </Link>

              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
              >
                <Icon icon="solar:logout-2-linear" className="text-lg" />
                {t('signOut')}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
