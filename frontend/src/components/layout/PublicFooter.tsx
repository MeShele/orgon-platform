"use client";

import Link from 'next/link';
import { SafeIcon as Icon } from '@/components/SafeIcon';

export function PublicFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-white/5 bg-slate-950">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 sm:py-10 md:py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <img
                src="/orgon-icon.png"
                alt="ORGON"
                className="h-10 w-10 rounded-full"
              />
              <div className="flex flex-col gap-0.5">
                <img
                  src="/orgon-logo.svg"
                  alt="ASYSTEM"
                  className="h-3 invert-0"
                />
                <span className="text-[10px] font-semibold tracking-[0.2em] text-slate-400">
                  ORGON
                </span>
              </div>
            </div>
            <p className="text-sm text-slate-400 max-w-md">
              Защитите ваши криптоактивы с корпоративным уровнем безопасности. 
              Мультиподписные кошельки для команд и организаций.
            </p>
          </div>

          {/* Product */}
          <div>
            <h3 className="text-sm font-semibold text-white mb-4">
              Продукт
            </h3>
            <ul className="space-y-3">
              <li>
                <Link
                  href="/features"
                  className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
                >
                  Возможности
                </Link>
              </li>
              <li>
                <Link
                  href="/pricing"
                  className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
                >
                  Тарифы
                </Link>
              </li>
              <li>
                <Link
                  href="/dashboard"
                  className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
                >
                  Панель управления
                </Link>
              </li>
              <li>
                <Link
                  href="/register"
                  className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
                >
                  Начать работу
                </Link>
              </li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h3 className="text-sm font-semibold text-white mb-4">
              Компания
            </h3>
            <ul className="space-y-3">
              <li>
                <Link
                  href="/about"
                  className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
                >
                  О нас
                </Link>
              </li>
              <li>
                <a
                  href="https://asystem.ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
                >
                  ASYSTEM
                </a>
              </li>
              <li>
                <Link
                  href="/login"
                  className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
                >
                  Войти
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 pt-8 border-t border-slate-200 dark:border-slate-800">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
            <p className="text-sm text-slate-400">
              © {currentYear} ASYSTEM. Все права защищены.
            </p>
            <div className="flex items-center gap-6">
              <Link
                href="/privacy"
                className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
              >
                Конфиденциальность
              </Link>
              <Link
                href="/terms"
                className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
              >
                Условия
              </Link>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
