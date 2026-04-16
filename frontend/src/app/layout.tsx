import type { Metadata } from "next";
import { cookies } from 'next/headers';
import { LanguageProvider } from '@/contexts/LanguageContext';
import { AuthProvider } from '@/contexts/AuthContext';
import "./globals.css";

export const metadata: Metadata = {
  title: "ORGON - Secure Multi-Signature Wallet Management",
  description: "Protect your crypto assets with enterprise-grade security. ORGON enables teams to collaboratively manage wallets with customizable signature requirements.",
  keywords: ["crypto custody", "multi-signature wallet", "digital assets", "Kyrgyzstan", "ORGON", "blockchain security"],
  authors: [{ name: "ASYSTEM" }],
  openGraph: {
    title: "ORGON - Secure Multi-Signature Wallet Management",
    description: "Enterprise-grade crypto custody platform with multi-signature security for exchanges, banks and fintech companies.",
    url: "https://orgon.asystem.ai",
    siteName: "ORGON Platform",
    type: "website",
    locale: "ru_RU",
  },
  twitter: {
    card: "summary_large_image",
    title: "ORGON - Secure Crypto Custody",
    description: "Enterprise-grade crypto custody with multi-signature security.",
  },
  robots: { index: true, follow: true },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Read locale from cookie on server
  const cookieStore = await cookies();
  const locale = (cookieStore.get('NEXT_LOCALE')?.value || 'ru') as 'ru' | 'en' | 'ky';
  
  return (
    <html lang={locale} className="dark" suppressHydrationWarning>
      <body className="bg-slate-100 text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-200 transition-colors duration-300">
        <AuthProvider>
          <LanguageProvider initialLocale={locale}>
            {children}
          </LanguageProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
