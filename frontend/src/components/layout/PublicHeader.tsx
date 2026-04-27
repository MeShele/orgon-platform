"use client";

import Link from 'next/link';
import { useState } from 'react';
import { SafeIcon as Icon } from '@/components/SafeIcon';
import { Button } from '@/components/ui/Button';

export function PublicHeader() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-slate-950/80 backdrop-blur-lg">
      <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <Link href="/" className="flex items-center gap-2">
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
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex md:items-center md:gap-8">
            <Link
              href="/"
              className="text-sm font-medium text-slate-300 hover:text-white transition-colors"
            >
              Главная
            </Link>
            <Link
              href="/features"
              className="text-sm font-medium text-slate-300 hover:text-white transition-colors"
            >
              Возможности
            </Link>
            <Link
              href="/pricing"
              className="text-sm font-medium text-slate-300 hover:text-white transition-colors"
            >
              Тарифы
            </Link>
            <Link
              href="/about"
              className="text-sm font-medium text-slate-300 hover:text-white transition-colors"
            >
              О нас
            </Link>
          </div>

          {/* Desktop Auth Buttons */}
          <div className="hidden md:flex md:items-center md:gap-4">
            <Link href="/login">
              <Button variant="ghost" size="sm">
                Войти
              </Button>
            </Link>
            <Link href="/register">
              <Button variant="primary" size="sm">
                Регистрация
              </Button>
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden rounded-lg p-2 text-slate-300 hover:bg-white/10"
          >
            <Icon
              icon={mobileMenuOpen ? "solar:close-circle-linear" : "solar:hamburger-menu-linear"}
              className="text-2xl"
            />
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-white/10 py-4">
            <div className="flex flex-col gap-4">
              <Link
                href="/"
                className="text-sm font-medium text-slate-300 hover:text-white transition-colors"
                onClick={() => setMobileMenuOpen(false)}
              >
                Главная
              </Link>
              <Link
                href="/features"
                className="text-sm font-medium text-slate-300 hover:text-white transition-colors"
                onClick={() => setMobileMenuOpen(false)}
              >
                Возможности
              </Link>
              <Link
                href="/pricing"
                className="text-sm font-medium text-slate-300 hover:text-white transition-colors"
                onClick={() => setMobileMenuOpen(false)}
              >
                Тарифы
              </Link>
              <Link
                href="/about"
                className="text-sm font-medium text-slate-300 hover:text-white transition-colors"
                onClick={() => setMobileMenuOpen(false)}
              >
                О нас
              </Link>
              <div className="flex flex-col gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
                <Link href="/login" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="ghost" size="sm" fullWidth>
                    Войти
                  </Button>
                </Link>
                <Link href="/register" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="primary" size="sm" fullWidth>
                    Регистрация
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}
