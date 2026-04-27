'use client';

import { useState, useRef, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { SafeIcon as Icon } from '@/components/SafeIcon';

const languages = [
  { code: 'ru' as const, name: 'Русский', flag: '🇷🇺', short: 'РУ' },
  { code: 'en' as const, name: 'English', flag: '🇬🇧', short: 'EN' },
  { code: 'ky' as const, name: 'Кыргызча', flag: '🇰🇬', short: 'КЫ' },
];

export function LanguageSwitcher() {
  const { locale, setLocale } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const [isChanging, setIsChanging] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentLanguage = languages.find(lang => lang.code === locale) || languages[0];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleLanguageChange = async (code: typeof locale) => {
    if (code === locale) {
      setIsOpen(false);
      return;
    }

    setIsChanging(true);
    setLocale(code);
    
    // Small delay for visual feedback
    setTimeout(() => {
      setIsChanging(false);
      setIsOpen(false);
    }, 300);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isChanging}
        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-white text-foreground hover:bg-muted dark:border-border dark:bg-muted dark:text-slate-200 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label="Change language"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <span className="text-lg" role="img" aria-label={currentLanguage.name}>
          {currentLanguage.flag}
        </span>
        <span className="hidden sm:inline font-medium">{currentLanguage.short}</span>
        <Icon
          icon={isOpen ? "solar:alt-arrow-up-linear" : "solar:alt-arrow-down-linear"}
          className={`text-sm transition-transform ${isChanging ? 'animate-spin' : ''}`}
        />
      </button>

      {isOpen && (
        <div
          className="absolute right-0 mt-2 w-48 rounded-lg border border-border bg-white shadow-lg dark:border-border dark:bg-muted z-50 animate-in fade-in slide-in-from-top-2 duration-200"
          role="menu"
          aria-orientation="vertical"
        >
          <div className="py-1">
            {languages.map((lang) => {
              const isActive = lang.code === locale;
              return (
                <button
                  key={lang.code}
                  onClick={() => handleLanguageChange(lang.code)}
                  disabled={isChanging}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-muted dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  role="menuitem"
                >
                  <span className="text-xl" role="img" aria-label={lang.name}>
                    {lang.flag}
                  </span>
                  <span className="flex-1 font-medium text-foreground dark:text-slate-200">
                    {lang.name}
                  </span>
                  {isActive && (
                    <Icon
                      icon="solar:check-circle-bold"
                      className="text-lg text-success"
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
