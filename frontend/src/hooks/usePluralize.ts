/**
 * Hook for pluralization
 */

import { useLanguage } from '@/contexts/LanguageContext';
import { formatCount, pluralize, pluralForms } from '@/lib/pluralize';

export function usePluralize() {
  const { locale } = useLanguage();

  /**
   * Format count with proper plural form
   * Example: pluralCount(5, 'wallets') => "5 кошельков"
   */
  function pluralCount(count: number, word: keyof typeof pluralForms): string {
    return formatCount(count, word, locale);
  }

  /**
   * Get just the plural word without count
   * Example: pluralWord(5, 'wallets') => "кошельков"
   */
  function pluralWord(count: number, word: keyof typeof pluralForms): string {
    const forms = pluralForms[word];
    return pluralize(count, locale, forms);
  }

  return {
    pluralCount,
    pluralWord,
  };
}
