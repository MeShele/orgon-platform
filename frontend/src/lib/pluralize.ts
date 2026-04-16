/**
 * Pluralization utilities for Russian, English, and Kyrgyz
 */

/**
 * Get plural form for Russian language
 * Rules: 1 (один), 2-4 (два-четыре), 5-20 (пять-двадцать), 21 (двадцать один), etc.
 */
export function getPluralFormRu(count: number, forms: [string, string, string]): string {
  const absCount = Math.abs(count);
  const mod10 = absCount % 10;
  const mod100 = absCount % 100;

  if (mod100 >= 11 && mod100 <= 14) {
    return forms[2]; // many: 11-14 кошельков
  }
  if (mod10 === 1) {
    return forms[0]; // one: 1 кошелёк, 21 кошелёк
  }
  if (mod10 >= 2 && mod10 <= 4) {
    return forms[1]; // few: 2-4 кошелька, 22-24 кошелька
  }
  return forms[2]; // many: 5-20 кошельков, 25+ кошельков
}

/**
 * Get plural form for English language
 * Rules: 1 (one), 2+ (other)
 */
export function getPluralFormEn(count: number, forms: [string, string]): string {
  return Math.abs(count) === 1 ? forms[0] : forms[1];
}

/**
 * Get plural form for Kyrgyz language
 * Kyrgyz doesn't have complex plural rules like Russian
 */
export function getPluralFormKy(count: number, forms: [string, string]): string {
  // Kyrgyz typically uses same form or adds suffix
  return Math.abs(count) === 1 ? forms[0] : forms[1];
}

/**
 * Pluralize based on locale
 */
export function pluralize(
  count: number,
  locale: 'ru' | 'en' | 'ky',
  forms: { ru: [string, string, string]; en: [string, string]; ky: [string, string] }
): string {
  switch (locale) {
    case 'ru':
      return getPluralFormRu(count, forms.ru);
    case 'en':
      return getPluralFormEn(count, forms.en);
    case 'ky':
      return getPluralFormKy(count, forms.ky);
    default:
      return forms.en[1];
  }
}

/**
 * Pluralize helpers for common words
 */
export const pluralForms = {
  wallets: {
    ru: ['кошелёк', 'кошелька', 'кошельков'] as [string, string, string],
    en: ['wallet', 'wallets'] as [string, string],
    ky: ['капчык', 'капчыктар'] as [string, string],
  },
  transactions: {
    ru: ['транзакция', 'транзакции', 'транзакций'] as [string, string, string],
    en: ['transaction', 'transactions'] as [string, string],
    ky: ['операция', 'операциялар'] as [string, string],
  },
  signatures: {
    ru: ['подпись', 'подписи', 'подписей'] as [string, string, string],
    en: ['signature', 'signatures'] as [string, string],
    ky: ['кол тамга', 'кол тамгалар'] as [string, string],
  },
  events: {
    ru: ['событие', 'события', 'событий'] as [string, string, string],
    en: ['event', 'events'] as [string, string],
    ky: ['окуя', 'окуялар'] as [string, string],
  },
} as const;

/**
 * Format count with proper plural form
 * Example: formatCount(5, 'wallets', 'ru') => "5 кошельков"
 */
export function formatCount(
  count: number,
  word: keyof typeof pluralForms,
  locale: 'ru' | 'en' | 'ky'
): string {
  const forms = pluralForms[word];
  const pluralWord = pluralize(count, locale, forms);
  return `${count} ${pluralWord}`;
}
