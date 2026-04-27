// PublicFooter v2 — link columns + legal entity + license status
// TODO: replace placeholder legal data with real ОсОО details when сделана
// регистрация / куплен domain orgon.kg.

import Link from "next/link";
import Image from "next/image";
import { Eyebrow, Mono } from "@/components/ui/primitives";
import { LogoWordmark } from "@/components/ui/LogoWordmark";

const COL_PRODUCT = [
  { href: "/features", label: "Возможности" },
  { href: "/pricing",  label: "Тарифы" },
  { href: "/about",    label: "О компании" },
  { href: "/login",    label: "Войти в кабинет" },
];

const COL_LEGAL = [
  { href: "/legal/terms",    label: "Условия использования" },
  { href: "/legal/privacy",  label: "Политика конфиденциальности" },
  { href: "/legal/aml",      label: "AML / KYC политика" },
  { href: "/legal/cookies",  label: "Cookies" },
];

const COL_SECURITY = [
  { href: "/security",            label: "Security overview" },
  { href: "/security/incident",   label: "Incident response" },
  { href: "/security/bug-bounty", label: "Bug bounty" },
  { href: "/security/audits",     label: "Аудиторские отчёты" },
];

export function PublicFooter() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-12 lg:py-16">
        {/* Brand top — icon + inline wordmark (currentColor inherits text-foreground) */}
        <Link href="/" className="inline-flex items-center gap-4 text-foreground mb-10 group">
          <Image src="/orgon-icon.png" alt="" width={32} height={32} aria-hidden />
          <LogoWordmark height={18} className="opacity-90 group-hover:opacity-100 transition-opacity" />
        </Link>

        {/* Top — link columns */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 lg:gap-12">
          <div>
            <Eyebrow>Продукт</Eyebrow>
            <ul className="mt-4 space-y-2.5">
              {COL_PRODUCT.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-[13px] text-muted-foreground hover:text-foreground transition-colors">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <Eyebrow>Безопасность</Eyebrow>
            <ul className="mt-4 space-y-2.5">
              {COL_SECURITY.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-[13px] text-muted-foreground hover:text-foreground transition-colors">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <Eyebrow>Правовое</Eyebrow>
            <ul className="mt-4 space-y-2.5">
              {COL_LEGAL.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-[13px] text-muted-foreground hover:text-foreground transition-colors">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <Eyebrow>Контакты</Eyebrow>
            <ul className="mt-4 space-y-2.5 font-mono text-[12px]">
              <li>
                <span className="text-faint">sales</span><br />
                <a href="mailto:sales@orgon.asystem.kg" className="text-foreground hover:text-primary">sales@orgon.asystem.kg</a>
              </li>
              <li>
                <span className="text-faint">support</span><br />
                <a href="mailto:support@orgon.asystem.kg" className="text-foreground hover:text-primary">support@orgon.asystem.kg</a>
              </li>
              <li>
                <span className="text-faint">security</span><br />
                <a href="mailto:security@orgon.asystem.kg" className="text-foreground hover:text-primary">security@orgon.asystem.kg</a>
              </li>
            </ul>
          </div>
        </div>

        {/* Legal entity + license */}
        <div className="mt-12 pt-8 border-t border-border">
          <div className="grid lg:grid-cols-[2fr_1fr] gap-8 items-start">
            <div>
              <Eyebrow>Юридическое лицо</Eyebrow>
              <div className="mt-3 grid sm:grid-cols-2 gap-x-8 gap-y-2 font-mono text-[12px]">
                <div className="flex justify-between gap-3">
                  <span className="text-faint">оператор</span>
                  <span className="text-foreground">ОсОО «АСИСТЕМ»</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span className="text-faint">рег. №</span>
                  <span className="text-foreground">000000-0000-ООО</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span className="text-faint">ИНН</span>
                  <span className="text-foreground">00000000000000</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span className="text-faint">адрес</span>
                  <span className="text-foreground text-right">КР, г. Бишкек</span>
                </div>
              </div>
            </div>

            <div className="lg:border-l lg:border-border lg:pl-8">
              <Eyebrow>Регулирование</Eyebrow>
              <div className="mt-3 space-y-2 font-mono text-[12px]">
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-warning" />
                  <span className="text-foreground">Лицензия НБ КР</span>
                  <span className="text-faint">· в процессе</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-success" />
                  <span className="text-foreground">FATF Travel Rule</span>
                  <span className="text-faint">· implemented</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-warning" />
                  <span className="text-foreground">ISO 27001:2022</span>
                  <span className="text-faint">· in progress</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom strip */}
        <div className="mt-10 pt-6 border-t border-border flex flex-wrap items-center justify-between gap-4">
          <Mono size="xs" className="text-faint">
            © {year} ОсОО «АСИСТЕМ». ORGON™ — торговая марка ОсОО «АСИСТЕМ».
          </Mono>
          <div className="flex items-center gap-4">
            <Mono size="xs" className="text-faint">build · 2026.04.27</Mono>
            <Mono size="xs" className="text-faint">status · operational</Mono>
          </div>
        </div>
      </div>
    </footer>
  );
}
