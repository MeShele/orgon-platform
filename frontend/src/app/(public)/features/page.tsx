"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";
import { FeatureIllustration } from "@/components/landing/FeatureIllustration";

interface Feature {
  tag: string;
  icon: string;
  title: string;
  description: string;
  details: string[];
}

const FEATURES: Feature[] = [
  {
    tag: "01 / Кастоди",
    icon: "solar:shield-network-bold",
    title: "Мульти-подписная безопасность",
    description:
      "Требуйте несколько подтверждений на каждую исходящую транзакцию. Настраиваемые пороги M-of-N исключают единую точку отказа.",
    details: [
      "Пороги до 7-of-15",
      "Поддержка аппаратных кошельков (Ledger, Trezor)",
      "Иерархические права и роли",
      "Географически распределённые подписанты",
    ],
  },
  {
    tag: "02 / Расписание",
    icon: "solar:calendar-mark-bold",
    title: "Планирование транзакций",
    description:
      "Регулярные платежи и автоматические переводы. Cron-выражения с пред-проверкой подписей до момента исполнения.",
    details: [
      "Cron-выражения для гибкости",
      "Повторяющиеся платежи",
      "Отложенное исполнение",
      "Автоматическая отмена просроченного",
    ],
  },
  {
    tag: "03 / Аналитика",
    icon: "solar:chart-2-bold",
    title: "Аналитика и метрики",
    description:
      "Отслеживайте балансы, объёмы транзакций и активность подписантов. Экспорт под регулятора и собственная BI.",
    details: [
      "Графики баланса и объёма",
      "Статистика по подписям",
      "Распределение токенов и сетей",
      "Экспорт CSV и JSON",
    ],
  },
  {
    tag: "04 / Адресная книга",
    icon: "solar:book-2-bold",
    title: "Контакты и адреса",
    description:
      "Сохраняйте проверенные адреса контрагентов, помечайте избранное, ведите категории — меньше человеческих ошибок при отправках.",
    details: [
      "Категории и избранное",
      "Поиск по имени и адресу",
      "Проверка checksum перед отправкой",
      "Импорт / экспорт списка",
    ],
  },
  {
    tag: "05 / Аудит",
    icon: "solar:document-text-bold",
    title: "Журнал аудита",
    description:
      "Полная история всех действий: кто, что, когда. Неизменяемый лог под FATF Travel Rule и внутренний контроль.",
    details: [
      "Полный history по каждому ресурсу",
      "Фильтрация по пользователям и действиям",
      "Точные timestamps",
      "Экспорт CSV для регулятора",
    ],
  },
  {
    tag: "06 / Сети",
    icon: "solar:global-bold",
    title: "Поддержка сетей",
    description:
      "Tron, BNB Chain, Ethereum, Polygon, BTC. Кросс-чейн совместимость через Safina Pay интеграцию.",
    details: [
      "Tron (TRC-20, USDT)",
      "EVM-сети: ETH, BSC, Polygon",
      "Bitcoin (BIP-32 кошельки)",
      "Автоматическая комиссия",
    ],
  },
];

export default function FeaturesPage() {
  return (
    <>
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-24 text-center">
          <Eyebrow dash tone="primary" className="!justify-center">Возможности платформы</Eyebrow>
          <h1 className="mt-6 text-[44px] sm:text-[56px] lg:text-[64px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground">
            Всё что нужно<br />для институциональной кастоди
          </h1>
          <p className="mt-6 max-w-2xl mx-auto text-[15px] leading-[1.6] text-muted-foreground">
            Шесть областей, которые мы выстроили под требования бирж, банков и финтех-команд.
          </p>
        </div>
      </section>

      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-12 lg:py-16">
          <div className="space-y-px bg-border border border-border">
            {FEATURES.map((feature, i) => {
              const reversed = i % 2 === 1;
              return (
                <article
                  key={feature.tag}
                  className="bg-card grid lg:grid-cols-2 gap-px"
                >
                  <div className={`p-10 lg:p-14 ${reversed ? "lg:order-2" : ""}`}>
                    <Eyebrow tone="primary">{feature.tag}</Eyebrow>
                    <h2 className="mt-5 text-[28px] sm:text-[32px] font-medium tracking-tight text-foreground">
                      {feature.title}
                    </h2>
                    <p className="mt-4 text-[15px] leading-[1.6] text-muted-foreground">
                      {feature.description}
                    </p>
                    <ul className="mt-6 space-y-2.5">
                      {feature.details.map((d) => (
                        <li key={d} className="flex items-start gap-3 text-[14px]">
                          <Icon icon="solar:check-circle-bold" className="text-success text-[16px] shrink-0 mt-0.5" />
                          <span className="text-foreground">{d}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div
                    className={`p-8 lg:p-12 flex items-center justify-center bg-muted/40 min-h-[280px] ${
                      reversed ? "lg:order-1" : ""
                    }`}
                  >
                    <FeatureIllustration index={i} />
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="border-b border-border bg-muted/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 text-center">
          <Eyebrow dash tone="primary" className="!justify-center">Готовы попробовать</Eyebrow>
          <h2 className="mt-5 text-[32px] sm:text-[40px] font-medium tracking-[-0.025em] leading-[1.1] text-foreground">
            Покажем платформу за 30 минут
          </h2>
          <p className="mt-4 max-w-xl mx-auto text-[15px] text-muted-foreground leading-[1.6]">
            Демо под ваш кейс — обменник, биржа, банк или fintech.
          </p>
          <div className="mt-8 flex justify-center gap-3 flex-wrap">
            <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
              <Button variant="primary" size="lg">
                Запросить демо
                <Icon icon="solar:arrow-right-linear" className="text-[15px]" />
              </Button>
            </a>
            <Link href="/pricing">
              <Button variant="secondary" size="lg">Смотреть тарифы</Button>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
