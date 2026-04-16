'use client';

import { useLanguage } from '@/contexts/LanguageContext';
import { getMessages } from '@/i18n/messages';
import { pluralize, pluralForms } from '@/lib/pluralize';

type NestedMessages = {
  [key: string]: string | NestedMessages;
};

type TranslationParams = {
  count?: number;
  [key: string]: string | number | undefined;
};

export function useTranslations(namespace?: string) {
  const { locale } = useLanguage();
  const messages = getMessages(locale);

  return function t(key: string, params?: TranslationParams): string {
    const fullKey = namespace ? `${namespace}.${key}` : key;
    const keys = fullKey.split('.');
    
    let value: any = messages;
    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k];
      } else {
        console.warn(`Translation missing: ${fullKey} (locale: ${locale})`);
        return fullKey;
      }
    }
    
    if (typeof value !== 'string') {
      return fullKey;
    }

    // If no params, return as is
    if (!params) {
      return value;
    }

    // Handle pluralization for common words
    if (params.count !== undefined && key === 'count') {
      // Extract word from namespace (e.g., 'wallets' from 'wallets.count')
      const word = namespace as keyof typeof pluralForms;
      if (word && pluralForms[word]) {
        const forms = pluralForms[word];
        const pluralWord = pluralize(params.count, locale, forms);
        return `${params.count} ${pluralWord}`;
      }
    }

    // Replace {{variable}} with params
    let result = value;
    Object.entries(params).forEach(([paramKey, paramValue]) => {
      const regex = new RegExp(`\\{\\{${paramKey}\\}\\}`, 'g');
      result = result.replace(regex, String(paramValue));
    });

    return result;
  };
}
