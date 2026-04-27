import Link from "next/link";
import Image from "next/image";

const PRODUCT = [
  { href: "/features", label: "Возможности" },
  { href: "/pricing", label: "Тарифы" },
  { href: "https://orgon-preview-api.asystem.kg/api/redoc", label: "Документация", external: true },
  { href: "/dashboard", label: "Панель управления" },
];

const COMPANY = [
  { href: "/about", label: "О компании" },
  { href: "https://asystem.ai", label: "ASYSTEM", external: true },
  { href: "mailto:sales@orgon.asystem.kg", label: "sales@orgon.asystem.kg" },
];

const LEGAL = [
  { href: "/privacy", label: "Конфиденциальность" },
  { href: "/terms", label: "Условия" },
];

export function PublicFooter() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-border bg-muted/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div className="col-span-2">
            <Link href="/" className="inline-flex items-center gap-3 text-foreground">
              <Image src="/orgon-icon.png" alt="ORGON" width={32} height={32} />
              <div className="flex flex-col leading-tight">
                <span className="font-mono text-[10px] tracking-[0.18em] text-faint">ASYSTEM</span>
                <span className="font-medium text-[15px] tracking-[0.06em]">ORGON</span>
              </div>
            </Link>
            <p className="mt-5 text-[13px] text-muted-foreground max-w-md leading-relaxed">
              Институциональное мульти-подписное хранение криптоактивов. Для бирж,
              брокеров, банков и финтех-компаний.
            </p>
          </div>

          <FooterCol title="Продукт" items={PRODUCT} />
          <FooterCol title="Компания" items={COMPANY} />
        </div>

        <div className="mt-12 pt-6 border-t border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="font-mono text-[11px] tracking-[0.08em] text-faint">
            © {year} ASYSTEM · ORGON. Все права защищены.
          </div>
          <ul className="flex gap-5">
            {LEGAL.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="font-mono text-[11px] tracking-[0.08em] text-muted-foreground hover:text-foreground"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({ title, items }: { title: string; items: { href: string; label: string; external?: boolean }[] }) {
  return (
    <div>
      <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-faint mb-4">{title}</div>
      <ul className="space-y-2.5">
        {items.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              target={item.external ? "_blank" : undefined}
              rel={item.external ? "noopener noreferrer" : undefined}
              className="text-[13px] text-muted-foreground hover:text-foreground transition-colors"
            >
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
