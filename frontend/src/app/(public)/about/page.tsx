import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Eyebrow, BigNum } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";

const VALUES = [
  {
    icon: "solar:shield-check-bold",
    title: "Безопасность прежде всего",
    desc: "Мульти-подпись, аппаратные ключи и полный аудит. Никаких компромиссов в защите средств клиента.",
  },
  {
    icon: "solar:eye-bold",
    title: "Прозрачность",
    desc: "Каждое действие логируется и доступно для проверки. История подписей не редактируется.",
  },
  {
    icon: "solar:user-check-bold",
    title: "Простота",
    desc: "Сложные функции не должны быть сложными в использовании. Интерфейс под профессионалов.",
  },
  {
    icon: "solar:rocket-2-bold",
    title: "Развитие",
    desc: "Постоянное улучшение на основе обратной связи от партнёров — бирж, банков, регуляторов.",
  },
];

const TIMELINE = [
  { year: "2024", event: "Основание ASYSTEM", desc: "Запуск технологической компании в Бишкеке" },
  { year: "2025", event: "Разработка ORGON", desc: "Закрытое тестирование с пилотными партнёрами" },
  { year: "2026", event: "Production launch", desc: "Выход платформы на рынок Центральной Азии" },
];

export default function AboutPage() {
  return (
    <>
      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-28 grid lg:grid-cols-[1.2fr_0.8fr] gap-12 items-end">
          <div>
            <Eyebrow dash tone="primary">О компании</Eyebrow>
            <h1 className="mt-6 text-[44px] sm:text-[56px] lg:text-[64px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground">
              Институциональная<br />криптоинфраструктура<br />в Центральной Азии
            </h1>
          </div>
          <p className="text-[15px] leading-[1.7] text-muted-foreground">
            ORGON — продукт компании ASYSTEM из Бишкека. Мы строим
            инфраструктуру, которая позволяет биржам, брокерам и банкам
            работать с криптоактивами под институциональным контролем —
            без компромиссов в безопасности и без прихоти регуляторики.
          </p>
        </div>
      </section>

      {/* VALUES */}
      <section className="border-b border-border bg-muted/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20">
          <Eyebrow dash tone="primary">Принципы</Eyebrow>
          <h2 className="mt-5 text-[36px] lg:text-[44px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground max-w-2xl">
            Четыре принципа, на которых строим продукт
          </h2>

          <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-px bg-border border border-border">
            {VALUES.map((v) => (
              <div key={v.title} className="bg-card p-7 lg:p-8">
                <Icon icon={v.icon} className="text-[28px] text-primary" />
                <h3 className="mt-5 text-[16px] font-medium tracking-tight text-foreground">{v.title}</h3>
                <p className="mt-2 text-[13px] leading-[1.55] text-muted-foreground">{v.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TIMELINE */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20">
          <Eyebrow dash tone="primary">Хронология</Eyebrow>
          <h2 className="mt-5 text-[32px] lg:text-[40px] font-medium tracking-[-0.025em] leading-[1.1] text-foreground">
            От идеи до институционального продукта
          </h2>

          <div className="mt-14 grid md:grid-cols-3 gap-px bg-border border border-border">
            {TIMELINE.map((t) => (
              <div key={t.year} className="bg-card p-8">
                <BigNum size="xl" className="text-primary">{t.year}</BigNum>
                <div className="mt-4 text-[16px] font-medium tracking-tight text-foreground">{t.event}</div>
                <p className="mt-1 text-[13px] text-muted-foreground leading-[1.55]">{t.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CONTACT CTA */}
      <section className="border-b border-border bg-muted/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 grid md:grid-cols-2 gap-12 items-center">
          <div>
            <Eyebrow dash tone="primary">Контакты</Eyebrow>
            <h2 className="mt-5 text-[28px] sm:text-[36px] font-medium tracking-[-0.025em] leading-[1.1] text-foreground">
              Свяжитесь с нами напрямую
            </h2>
            <ul className="mt-6 space-y-3 text-[14px]">
              <li className="flex items-center gap-3">
                <Icon icon="solar:letter-bold" className="text-[18px] text-primary" />
                <a href="mailto:sales@orgon.asystem.kg" className="text-foreground hover:text-primary">
                  sales@orgon.asystem.kg
                </a>
              </li>
              <li className="flex items-center gap-3">
                <Icon icon="solar:map-point-bold" className="text-[18px] text-primary" />
                <span className="text-foreground">Бишкек, Кыргызстан</span>
              </li>
              <li className="flex items-center gap-3">
                <Icon icon="solar:global-bold" className="text-[18px] text-primary" />
                <a
                  href="https://asystem.ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-foreground hover:text-primary"
                >
                  asystem.ai
                </a>
              </li>
            </ul>
          </div>
          <div className="flex flex-col gap-3">
            <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
              <Button variant="primary" size="lg" fullWidth>
                Запросить демо
                <Icon icon="solar:arrow-right-linear" className="text-[15px]" />
              </Button>
            </a>
            <Link href="/pricing">
              <Button variant="secondary" size="lg" fullWidth>Смотреть тарифы</Button>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
