import ruMessages from './locales/ru.json';
import enMessages from './locales/en.json';
import kyMessages from './locales/ky.json';

export type Locale = 'ru' | 'en' | 'ky';

const messages = {
  ru: ruMessages,
  en: enMessages,
  ky: kyMessages,
} as const;

export function getMessages(locale: Locale) {
  return messages[locale] || messages.ru;
}

export const locales: Locale[] = ['ru', 'en', 'ky'];
export const defaultLocale: Locale = 'ru';
