import type { Metadata } from "next";
import { cookies } from 'next/headers';
import { Inter, IBM_Plex_Mono } from 'next/font/google';
import { LanguageProvider } from '@/contexts/LanguageContext';
import { AuthProvider } from '@/contexts/AuthContext';
import "./globals.css";

const inter = Inter({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-inter',
  display: 'swap',
});

const plexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-plex-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: "ORGON — Институциональное мульти-подписное хранение криптоактивов",
  description: "Multi-signature кастоди для бирж, брокеров и банков. M-of-N подписи, регулируемый KYC/AML, белый-лейбл и B2B API.",
  keywords: ["crypto custody", "multi-signature wallet", "digital assets", "Kyrgyzstan", "ORGON", "blockchain security"],
  authors: [{ name: "ASYSTEM" }],
  openGraph: {
    title: "ORGON — Институциональное хранение криптоактивов",
    description: "Multi-signature кастоди для бирж, брокеров и банков. Регулируемый KYC/AML, белый-лейбл, B2B API.",
    url: "https://orgon.asystem.kg",
    siteName: "ORGON",
    type: "website",
    locale: "ru_RU",
  },
  twitter: {
    card: "summary_large_image",
    title: "ORGON · Institutional Custody",
    description: "Multi-signature crypto custody for exchanges, brokers and banks.",
  },
  robots: { index: true, follow: true },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const cookieStore = await cookies();
  const locale = (cookieStore.get('NEXT_LOCALE')?.value || 'ru') as 'ru' | 'en' | 'ky';
  // Default theme is light. Dark only if user explicitly selected it.
  const theme = cookieStore.get('orgon_theme')?.value === 'dark' ? 'dark' : 'light';

  return (
    <html
      lang={locale}
      className={`${inter.variable} ${plexMono.variable} ${theme === 'dark' ? 'dark' : ''}`}
      suppressHydrationWarning
    >
      <body className="bg-background text-foreground antialiased transition-colors duration-200">
        <AuthProvider>
          <LanguageProvider initialLocale={locale}>
            {children}
          </LanguageProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
