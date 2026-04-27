'use client';

import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useTranslations } from '@/hooks/useTranslations';
import { Card } from '@/components/ui/Card';
import { SafeIcon as Icon } from '@/components/SafeIcon';

const languages = [
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'ky', name: 'Кыргызча', flag: '🇰🇬' },
];

const themes = [
  { id: 'light', name: 'Light', icon: 'solar:sun-bold' },
  { id: 'dark', name: 'Dark', icon: 'solar:moon-bold' },
  { id: 'system', name: 'System', icon: 'solar:monitor-bold' },
];

export function LanguageThemeSettings() {
  const { locale, setLocale } = useLanguage();
  const t = useTranslations('profile');
  const [currentTheme, setCurrentTheme] = useState('system');

  useEffect(() => {
    // Detect current theme
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark' || savedTheme === 'light') {
      setCurrentTheme(savedTheme);
    } else {
      setCurrentTheme('system');
    }
  }, []);

  const handleThemeChange = (theme: string) => {
    setCurrentTheme(theme);
    
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else if (theme === 'light') {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    } else {
      // System preference
      localStorage.removeItem('theme');
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Language Settings */}
      <Card padding>
        <h3 className="mb-4 text-lg font-semibold text-foreground">
          {t('language.title')}
        </h3>
        <p className="mb-6 text-sm text-muted-foreground">
          {t('language.description')}
        </p>
        
        <div className="grid gap-3 sm:grid-cols-3">
          {languages.map((lang) => (
            <button
              key={lang.code}
              onClick={() => setLocale(lang.code as 'ru' | 'en' | 'ky')}
              className={`flex items-center gap-3 rounded-lg border p-4 transition-all ${
                locale === lang.code
                  ? 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-900/20'
                  : 'border-border bg-white hover:border-border dark:bg-gray-800 dark:hover:border-gray-600'
              }`}
            >
              <span className="text-2xl">{lang.flag}</span>
              <div className="flex-1 text-left">
                <p className="text-sm font-medium text-foreground">
                  {lang.name}
                </p>
                {locale === lang.code && (
                  <p className="text-xs text-primary">
                    {t('language.active')}
                  </p>
                )}
              </div>
              {locale === lang.code && (
                <Icon
                  icon="solar:check-circle-bold"
                  className="text-xl text-primary"
                />
              )}
            </button>
          ))}
        </div>
      </Card>

      {/* Theme Settings */}
      <Card padding>
        <h3 className="mb-4 text-lg font-semibold text-foreground">
          {t('theme.title')}
        </h3>
        <p className="mb-6 text-sm text-muted-foreground">
          {t('theme.description')}
        </p>
        
        <div className="grid gap-3 sm:grid-cols-3">
          {themes.map((theme) => (
            <button
              key={theme.id}
              onClick={() => handleThemeChange(theme.id)}
              className={`flex items-center gap-3 rounded-lg border p-4 transition-all ${
                currentTheme === theme.id
                  ? 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-900/20'
                  : 'border-border bg-white hover:border-border dark:bg-gray-800 dark:hover:border-gray-600'
              }`}
            >
              <Icon
                icon={theme.icon}
                className={`text-2xl ${
                  currentTheme === theme.id
                    ? 'text-primary'
                    : 'text-muted-foreground'
                }`}
              />
              <div className="flex-1 text-left">
                <p className="text-sm font-medium text-foreground">
                  {t(`theme.${theme.id}`)}
                </p>
                {currentTheme === theme.id && (
                  <p className="text-xs text-primary">
                    {t('theme.active')}
                  </p>
                )}
              </div>
              {currentTheme === theme.id && (
                <Icon
                  icon="solar:check-circle-bold"
                  className="text-xl text-primary"
                />
              )}
            </button>
          ))}
        </div>
      </Card>
    </div>
  );
}
