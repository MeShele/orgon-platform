"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";

type Section = {
  id: string;
  audience: string;
  title: string;
  desc: string;
  icon: string;
};

const SECTIONS: Section[] = [
  {
    id: "for-business",
    audience: "Руководству / Compliance",
    title: "Что такое ORGON и как мы работаем с регулятором",
    desc:
      "Обзор продукта, отличие от голого custody, как мы закрываем требования Финнадзора, AFSA, ISO 27001 / SOC 2. Без технических деталей.",
    icon: "solar:buildings-bold",
  },
  {
    id: "onboarding",
    audience: "Pre-sales / Юристы",
    title: "Процесс подключения клиента",
    desc:
      "От первого звонка до первой транзакции — 6 этапов, ~1-2 недели. Что подписываем, какие документы запрашиваем, кто отвечает за каждый шаг.",
    icon: "solar:checklist-minimalistic-bold",
  },
  {
    id: "for-developers",
    audience: "Разработчики клиента",
    title: "Интеграция API",
    desc:
      "Аутентификация HMAC, первые вызовы, webhooks, обработка ошибок, rate limits. Code samples на Python и Node. Swagger UI со 183 операциями.",
    icon: "solar:code-bold",
  },
  {
    id: "for-devops",
    audience: "DevOps клиента",
    title: "Production setup",
    desc:
      "Выделенный tenant: отдельная база, изолированный Postgres, KMS-backed signer, daily backups, Disaster recovery. Готовый runbook на 30 минут.",
    icon: "solar:server-bold",
  },
  {
    id: "security",
    audience: "CTO / Security",
    title: "Security & Compliance",
    desc:
      "Multi-tenancy с RLS на уровне БД, append-only audit log, AML rule engine, KYC/KYB через Sumsub, SAR submission в Финнадзор, HMAC replay protection.",
    icon: "solar:shield-check-bold",
  },
];

const ONBOARDING_STEPS = [
  {
    step: "01",
    week: "Неделя 1",
    title: "Первый контакт",
    items: [
      "Звонок с sales — 30 минут на демо",
      "Подписание NDA",
      "Технический звонок с CTO клиента",
    ],
  },
  {
    step: "02",
    week: "Неделя 1-2",
    title: "Договор и креды",
    items: [
      "MSA / SaaS-договор",
      "DPA по GDPR / 152-ФЗ",
      "Запрос на выдачу Safina-ключа prod-tenant",
    ],
  },
  {
    step: "03",
    week: "30 минут",
    title: "Поднятие окружения",
    items: [
      "Coolify env под клиента + отдельный Postgres",
      "Cloudflare DNS + SSL",
      "Подключение Safina-ключа клиента через safina-key-switch",
    ],
  },
  {
    step: "04",
    week: "30 минут",
    title: "Smoke и handover",
    items: [
      "Создание первого admin клиента",
      "Тестовое создание кошелька",
      "Передача доступов: dashboard URL + временные пароли",
    ],
  },
  {
    step: "05",
    week: "1-2 дня",
    title: "Интеграция (опционально)",
    items: [
      "Разработчики клиента — Partner API",
      "Webhook-эндпоинты со стороны клиента",
      "Тестовые транзакции на testnet",
    ],
  },
  {
    step: "06",
    week: "Go-live",
    title: "Production",
    items: [
      "Переключение на mainnet",
      "Первые реальные транзакции с малыми суммами",
      "Scale-up по мере успешных циклов",
    ],
  },
];

const DEV_QUICK_START = [
  {
    title: "1. Учётные записи",
    body: "После подключения tenant первый admin создаётся вручную через psql. Дальше admin создаёт остальные роли (signer, viewer) через UI в /users.",
  },
  {
    title: "2. JWT-авторизация",
    body: "POST /api/auth/login с email/password возвращает access_token. Передавайте его в Authorization: Bearer для каждого запроса.",
  },
  {
    title: "3. Кошельки",
    body: "POST /api/wallets с {network, info} создаёт wallet через Safina. Возвращает myUNID. Список — GET /api/wallets.",
  },
  {
    title: "4. Транзакции",
    body: "POST /api/transactions с {token, to_address, value, info}. token-format: 'network:::SYMBOL###wallet_name'. Возвращает tx_unid в Safina-state pending.",
  },
  {
    title: "5. Подписи",
    body: "GET /api/signatures/pending — что ждёт подписи. POST /api/signatures/{unid}/sign — подписать. Replay-guard защищает от двойной подписи.",
  },
  {
    title: "6. Swagger UI",
    body: "Полная live-документация: /api/docs. Все эндпоинты, Try it out, реальные ответы. JWT-токен можно вставить в Authorize кнопкой.",
  },
];

const SECURITY_POINTS = [
  { icon: "solar:lock-keyhole-bold", title: "Multi-tenancy", desc: "Row-Level Security на Postgres — клиенты не видят друг друга даже при баге в коде." },
  { icon: "solar:history-bold", title: "Append-only audit", desc: "DB-trigger блокирует UPDATE/DELETE на audit_log. Требование SOC2 / ISO27001." },
  { icon: "solar:key-square-2-bold", title: "KMS-backed signer", desc: "Приватные ключи в AWS KMS (FIPS 140-2 L3). Никогда не покидают HSM." },
  { icon: "solar:shield-warning-bold", title: "AML rule engine", desc: "Threshold / velocity / blacklist. Действия: alert / hold / block. Полный audit-trail." },
  { icon: "solar:document-text-bold", title: "KYC / KYB через Sumsub", desc: "FedRAMP-compliant. Документы не хранятся у нас — только статус через webhook." },
  { icon: "solar:bug-bold", title: "Изолированный tenant", desc: "Каждый клиент получает отдельный Postgres + отдельный EC-ключ Safina. Никакого shared-state." },
];

export default function DocsPage() {
  return (
    <>
      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-28">
          <Eyebrow dash tone="primary">Документация</Eyebrow>
          <h1 className="mt-6 text-[44px] sm:text-[56px] lg:text-[64px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground max-w-4xl">
            Всё что нужно знать <br className="hidden sm:inline" />о подключении к ORGON
          </h1>
          <p className="mt-8 max-w-3xl text-[16px] leading-[1.7] text-muted-foreground">
            Один документ под разные аудитории — от руководителя клиента до разработчика-интегратора.
            Каждая секция отвечает на конкретные вопросы. Если что-то непонятно — напишите в support.
          </p>
        </div>
      </section>

      {/* NAVIGATOR */}
      <section className="border-b border-border bg-muted/20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-12">
          <Eyebrow dash tone="muted">Разделы</Eyebrow>
          <div className="mt-6 grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {SECTIONS.map((s) => (
              <Link
                key={s.id}
                href={`#${s.id}`}
                className="group block border border-border bg-background p-5 hover:border-primary transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Icon icon={s.icon} className="text-[24px] text-primary" />
                  <span className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">{s.audience}</span>
                </div>
                <h3 className="mt-3 text-[15px] font-medium text-foreground group-hover:text-primary transition-colors">
                  {s.title}
                </h3>
                <p className="mt-2 text-[13px] leading-[1.55] text-muted-foreground line-clamp-3">{s.desc}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 1 — for-business */}
      <section id="for-business" className="border-b border-border scroll-mt-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20">
          <Eyebrow dash tone="primary">01 — Для руководства</Eyebrow>
          <h2 className="mt-6 text-[36px] sm:text-[44px] font-medium tracking-[-0.02em] leading-[1.1] text-foreground max-w-3xl">
            Что такое ORGON
          </h2>
          <div className="mt-8 grid lg:grid-cols-2 gap-10 max-w-5xl">
            <div className="space-y-4 text-[15px] leading-[1.7] text-muted-foreground">
              <p>
                <strong className="text-foreground">Safina Pay</strong> — лицензированный кастоди-сервис в КР.
                Они держат криптоактивы и подписывают транзакции. Их API сухой — только хранилище и подпись.
              </p>
              <p>
                <strong className="text-foreground">ORGON</strong> — операционный слой поверх Safina.
                Multi-sig, RBAC, AML, KYC, audit, multi-tenancy. Всё что нужно
                чтобы биржа/обменник/банк прошли проверку Финнадзора или AFSA.
              </p>
              <p>
                Без ORGON клиенту нужно 10 инженеров и год работы.
                С ORGON — 30 минут подключения и готовый продукт под регулятор.
              </p>
            </div>
            <div className="border border-border bg-muted/30 p-6 space-y-3">
              <div className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">Кому подходит</div>
              <ul className="space-y-2 text-[14px] text-foreground">
                <li className="flex gap-3"><Icon icon="solar:check-circle-bold" className="text-primary text-[18px] mt-0.5" /> Криптообменники / OTC ($1-10М/мес)</li>
                <li className="flex gap-3"><Icon icon="solar:check-circle-bold" className="text-primary text-[18px] mt-0.5" /> Финтех-стартапы и P2P-платформы</li>
                <li className="flex gap-3"><Icon icon="solar:check-circle-bold" className="text-primary text-[18px] mt-0.5" /> Биржи под лицензией AIFC / AFSA</li>
                <li className="flex gap-3"><Icon icon="solar:check-circle-bold" className="text-primary text-[18px] mt-0.5" /> Банки с криптокастоди-стратегией</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 2 — onboarding */}
      <section id="onboarding" className="border-b border-border scroll-mt-24 bg-muted/10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20">
          <Eyebrow dash tone="primary">02 — Процесс подключения</Eyebrow>
          <h2 className="mt-6 text-[36px] sm:text-[44px] font-medium tracking-[-0.02em] leading-[1.1] text-foreground">
            От первого звонка до live — 6 этапов
          </h2>
          <p className="mt-4 max-w-3xl text-[15px] leading-[1.7] text-muted-foreground">
            Полный цикл занимает 1-2 недели. Технический setup tenant&apos;а — 30 минут.
            Если у клиента есть свой разработчик — добавьте 1-2 дня на интеграцию API.
          </p>
          <div className="mt-12 grid md:grid-cols-2 lg:grid-cols-3 gap-px bg-border">
            {ONBOARDING_STEPS.map((s) => (
              <div key={s.step} className="bg-background p-6">
                <div className="flex items-baseline justify-between">
                  <span className="text-[40px] font-light text-primary tracking-tight">{s.step}</span>
                  <span className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">{s.week}</span>
                </div>
                <h3 className="mt-4 text-[18px] font-medium text-foreground">{s.title}</h3>
                <ul className="mt-4 space-y-2 text-[13px] leading-[1.6] text-muted-foreground">
                  {s.items.map((it, i) => (
                    <li key={i} className="flex gap-2">
                      <Icon icon="solar:minus-circle-linear" className="text-[14px] mt-1 text-muted-foreground/60 shrink-0" />
                      <span>{it}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 3 — for-developers */}
      <section id="for-developers" className="border-b border-border scroll-mt-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20">
          <Eyebrow dash tone="primary">03 — Для разработчиков клиента</Eyebrow>
          <h2 className="mt-6 text-[36px] sm:text-[44px] font-medium tracking-[-0.02em] leading-[1.1] text-foreground">
            Quick Start интеграции
          </h2>
          <div className="mt-12 grid md:grid-cols-2 lg:grid-cols-3 gap-px bg-border">
            {DEV_QUICK_START.map((s) => (
              <div key={s.title} className="bg-background p-6">
                <h3 className="text-[16px] font-medium text-foreground">{s.title}</h3>
                <p className="mt-3 text-[14px] leading-[1.6] text-muted-foreground">{s.body}</p>
              </div>
            ))}
          </div>
          <div className="mt-10 flex flex-wrap gap-4">
            <a href="/api/docs" target="_blank" rel="noopener">
              <Button variant="primary" size="md">
                Открыть Swagger UI <Icon icon="solar:arrow-right-up-linear" className="text-[15px]" />
              </Button>
            </a>
            <a href="https://github.com/MeShele/orgon-platform" target="_blank" rel="noopener">
              <Button variant="secondary" size="md">
                GitHub — публичный repo
              </Button>
            </a>
          </div>
        </div>
      </section>

      {/* SECTION 4 — for-devops */}
      <section id="for-devops" className="border-b border-border scroll-mt-24 bg-muted/10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20">
          <Eyebrow dash tone="primary">04 — Для DevOps клиента</Eyebrow>
          <h2 className="mt-6 text-[36px] sm:text-[44px] font-medium tracking-[-0.02em] leading-[1.1] text-foreground">
            Production setup за 30 минут
          </h2>
          <div className="mt-8 max-w-3xl text-[15px] leading-[1.7] text-muted-foreground space-y-4">
            <p>Каждый клиент получает <strong className="text-foreground">отдельный tenant</strong> — собственный Coolify environment, изолированный Postgres, индивидуальный Safina-ключ. Никакого shared-state с другими клиентами.</p>
            <p>Технический runbook собран в репозитории: <code className="bg-muted px-1.5 py-0.5 rounded text-[13px]">docs/prod-readiness.md</code> — 10 секций, env-матрица, security-checklist, DR-procedures.</p>
          </div>
          <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-4 gap-px bg-border max-w-5xl">
            {[
              { num: "1", label: "Coolify env", desc: "Отдельное окружение под клиента" },
              { num: "2", label: "Postgres", desc: "Standalone managed DB с daily backups" },
              { num: "3", label: "DNS + SSL", desc: "Cloudflare orange-cloud, Full SSL" },
              { num: "4", label: "Safina ключ", desc: "safina-key-switch.sh — атомарная смена" },
            ].map((s) => (
              <div key={s.num} className="bg-background p-5">
                <div className="text-[24px] font-light text-primary">{s.num}</div>
                <div className="mt-2 text-[15px] font-medium text-foreground">{s.label}</div>
                <div className="mt-1 text-[13px] leading-[1.5] text-muted-foreground">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 5 — security */}
      <section id="security" className="border-b border-border scroll-mt-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20">
          <Eyebrow dash tone="primary">05 — Security & Compliance</Eyebrow>
          <h2 className="mt-6 text-[36px] sm:text-[44px] font-medium tracking-[-0.02em] leading-[1.1] text-foreground">
            Что встроено в платформу
          </h2>
          <div className="mt-12 grid md:grid-cols-2 lg:grid-cols-3 gap-px bg-border">
            {SECURITY_POINTS.map((p) => (
              <div key={p.title} className="bg-background p-6">
                <Icon icon={p.icon} className="text-[28px] text-primary" />
                <h3 className="mt-4 text-[16px] font-medium text-foreground">{p.title}</h3>
                <p className="mt-2 text-[13px] leading-[1.6] text-muted-foreground">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CONTACT */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 text-center">
          <Eyebrow dash tone="primary">Свяжитесь с нами</Eyebrow>
          <h2 className="mt-6 text-[32px] sm:text-[40px] font-medium tracking-[-0.02em] text-foreground">
            Готовы подключиться?
          </h2>
          <p className="mt-4 max-w-2xl mx-auto text-[15px] leading-[1.7] text-muted-foreground">
            Запросите демо под ваш кейс — обменник, биржа, банк или fintech. Покажем платформу за 30 минут.
          </p>
          <div className="mt-8 flex justify-center gap-3 flex-wrap">
            <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
              <Button variant="primary" size="lg">
                Запросить демо <Icon icon="solar:arrow-right-linear" className="text-[15px]" />
              </Button>
            </a>
            <a href="mailto:support@orgon.asystem.kg">
              <Button variant="secondary" size="lg">
                Support
              </Button>
            </a>
          </div>
          <div className="mt-8 text-[13px] text-muted-foreground">
            sales@orgon.asystem.kg · support@orgon.asystem.kg · t.me/asystem_dev
          </div>
        </div>
      </section>
    </>
  );
}
