'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

type Locale = 'ru' | 'en' | 'ky';

interface LanguageContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ 
  children,
  initialLocale = 'ru'
}: { 
  children: ReactNode;
  initialLocale?: Locale;
}) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);
  const router = useRouter();

  // Load locale from cookie on mount (fallback if initialLocale not provided)
  useEffect(() => {
    const savedLocale = document.cookie
      .split('; ')
      .find(row => row.startsWith('NEXT_LOCALE='))
      ?.split('=')[1] as Locale | undefined;
    
    if (savedLocale && ['ru', 'en', 'ky'].includes(savedLocale) && savedLocale !== initialLocale) {
      setLocaleState(savedLocale);
    }
  }, [initialLocale]);

  const setLocale = (newLocale: Locale) => {
    // Save to cookie (expires in 1 year)
    const maxAge = 365 * 24 * 60 * 60;
    document.cookie = `NEXT_LOCALE=${newLocale}; path=/; max-age=${maxAge}; SameSite=Lax`;
    
    setLocaleState(newLocale);
    
    // Force full page reload to ensure all components update
    // router.refresh() is not enough for i18n changes
    window.location.reload();
  };

  return (
    <LanguageContext.Provider value={{ locale, setLocale }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within LanguageProvider');
  }
  return context;
}
