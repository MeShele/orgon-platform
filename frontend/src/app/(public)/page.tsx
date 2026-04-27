import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Eyebrow, Mono, BigNum, Divider } from "@/components/ui/primitives";
import { Badge } from "@/components/ui/Badge";
import { NetworkGraph, type SignerNode } from "@/components/ui/NetworkGraph";
import { TxFlow } from "@/components/ui/TxFlow";
import { Icon } from "@/lib/icons";

const HERO_SIGNERS: SignerNode[] = [
  { address: "cfo@example", initials: "АБ", state: "signed" },
  { address: "ceo@example", initials: "ДС", state: "signed" },
  { address: "coo@example", initials: "ТО", state: "pending" },
  { address: "cto@example", initials: "АЖ", state: "pending" },
  { address: "cro@example", initials: "НИ", state: "pending" },
];

export default function LandingPage() {
  return (
    <>
      <Hero />
      <Pillars />
      <Numbers />
      <FlowSection />
      <BottomCTA />
    </>
  );
}

function Hero() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-16 lg:py-24 grid lg:grid-cols-[1.15fr_0.85fr] gap-10 lg:gap-12">
        <div>
          <Eyebrow dash tone="primary">Институциональное хранение криптоактивов</Eyebrow>

          <h1 className="mt-7 font-medium tracking-[-0.035em] leading-[1.02] text-foreground text-[44px] sm:text-[56px] lg:text-[72px]">
            Совместная подпись<br />корпоративного капитала
          </h1>

          <p className="mt-7 max-w-[480px] text-[15px] sm:text-[16px] leading-[1.55] text-muted-foreground">
            ORGON — multi-signature кастоди для бирж, брокеров и банков. Пороги
            M-of-N подписей, регулируемые KYC/AML потоки, белый-лейбл и B2B API.
          </p>

          <div className="mt-9 flex flex-wrap gap-3">
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

          <div className="mt-14 pt-7 border-t border-border">
            <Eyebrow>Нам доверяют</Eyebrow>
            <p className="mt-3 text-[14px] text-muted-foreground max-w-md leading-[1.55]">
              Используется обменниками и финтех-компаниями Кыргызстана для
              совместного управления корпоративными криптоактивами.
            </p>
          </div>
        </div>

        {/* Right: navy demo block — multi-sig in action */}
        <div className="bg-navy text-navy-foreground p-7 lg:p-8 self-start">
          <div className="flex items-start justify-between gap-3">
            <div>
              <Eyebrow tone="muted" className="!text-white/55">WALLET · TREASURY-COLD</Eyebrow>
              <Mono size="md" className="mt-1 text-white/85">0x4f2a··b81c</Mono>
            </div>
            <Badge variant="primary">2 / 5 SIGNED</Badge>
          </div>

          <div className="mt-6 mb-2 flex justify-center">
            <NetworkGraph
              signers={HERO_SIGNERS}
              size={260}
              accentColor="var(--primary)"
              ringColor="rgba(255,255,255,0.30)"
              labelColor="#ffffff"
            />
          </div>

          <Divider className="!bg-white/12 mt-4" />

          <dl className="mt-4 space-y-2">
            <div className="flex justify-between font-mono text-[11px]">
              <dt className="uppercase tracking-[0.10em] text-white/55">Amount</dt>
              <dd className="text-white">0.482 BTC · $45 720</dd>
            </div>
            <div className="flex justify-between font-mono text-[11px]">
              <dt className="uppercase tracking-[0.10em] text-white/55">Destination</dt>
              <dd className="text-white">TWmh8N··aLpQ</dd>
            </div>
            <div className="flex justify-between font-mono text-[11px]">
              <dt className="uppercase tracking-[0.10em] text-white/55">Network</dt>
              <dd className="text-white">Tron mainnet</dd>
            </div>
          </dl>
        </div>
      </div>
    </section>
  );
}

const PILLARS = [
  {
    tag: "01 / Кастоди",
    title: "Multi-signature",
    body: "Пороги M-of-N. Аппаратные ключи Ledger и Trezor. Географически распределённые подписанты. Никакой single-point-of-failure.",
    icon: "solar:shield-network-bold",
  },
  {
    tag: "02 / Compliance",
    title: "KYC · KYB · AML",
    body: "Регулируемые потоки идентификации, очередь ревью, AML-алерты в реальном времени. Соответствие FATF Travel Rule.",
    icon: "solar:document-text-bold",
  },
  {
    tag: "03 / Интеграции",
    title: "Белый-лейбл и API",
    body: "Полноценный B2B API, webhooks, fiat on/off-ramp, кастомный брендинг под ваш домен. Работает в фоне у вашего клиента.",
    icon: "solar:global-bold",
  },
];

function Pillars() {
  return (
    <section className="border-b border-border bg-muted/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-24">
        <div className="max-w-2xl">
          <Eyebrow dash tone="primary">Платформа</Eyebrow>
          <h2 className="mt-5 text-[36px] lg:text-[48px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground">
            Три столпа<br />институциональной кастоди
          </h2>
        </div>

        <div className="mt-14 grid md:grid-cols-3 gap-px bg-border border border-border">
          {PILLARS.map((p) => (
            <article key={p.tag} className="bg-card p-8 lg:p-10">
              <Eyebrow tone="primary">{p.tag}</Eyebrow>
              <Icon icon={p.icon} className="text-[40px] text-foreground mt-6" />
              <h3 className="mt-6 text-[22px] font-medium tracking-tight text-foreground">{p.title}</h3>
              <p className="mt-3 text-[14px] leading-[1.6] text-muted-foreground">{p.body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

const KPIS = [
  { label: "Поддерживаемые сети", value: "7+", sub: "TRX · BSC · ETH · POL · BTC" },
  { label: "Пороги подписей", value: "M-of-N", sub: "до 7-of-15" },
  { label: "Языки интерфейса", value: "3", sub: "RU · EN · KY" },
  { label: "Time-to-live", value: "< 5 мин", sub: "от регистрации до первого кошелька" },
];

function Numbers() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-16 lg:py-20">
        <Eyebrow dash tone="primary">Цифры</Eyebrow>
        <div className="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-px bg-border border border-border">
          {KPIS.map((k) => (
            <div key={k.label} className="bg-card p-6 lg:p-8">
              <Eyebrow>{k.label}</Eyebrow>
              <BigNum size="xl" className="mt-2">{k.value}</BigNum>
              <Mono size="xs" className="mt-2 text-muted-foreground block">{k.sub}</Mono>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FlowSection() {
  return (
    <section className="border-b border-border bg-muted/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-24 grid lg:grid-cols-2 gap-14 items-center">
        <div>
          <Eyebrow dash tone="primary">Как это работает</Eyebrow>
          <h2 className="mt-5 text-[32px] lg:text-[40px] font-medium tracking-[-0.025em] leading-[1.1] text-foreground">
            Транзакция требует согласия команды
          </h2>
          <p className="mt-5 text-[15px] leading-[1.6] text-muted-foreground max-w-lg">
            Любой исходящий перевод нужно подтвердить минимум M из N
            подписантов. Без достаточного количества подписей — транзакция
            не уходит в сеть. Никаких единоличных действий с балансом.
          </p>
          <ol className="mt-7 space-y-3 text-[14px]">
            {[
              "Оператор инициирует исходящую транзакцию",
              "Запрос приходит каждому подписанту в realtime",
              "По достижении порога — broadcast в blockchain",
              "Аудит-лог сохраняет всю историю подписей",
            ].map((step, i) => (
              <li key={i} className="flex gap-3">
                <span className="font-mono text-[11px] text-faint mt-0.5">0{i + 1}</span>
                <span className="text-foreground">{step}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="bg-card border border-border p-8 lg:p-10 self-start">
          <Eyebrow>Поток транзакции</Eyebrow>
          <div className="mt-6 flex justify-center">
            <TxFlow width={420} height={120} threshold="3 / 5" />
          </div>
        </div>
      </div>
    </section>
  );
}

function BottomCTA() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-24">
        <div className="bg-navy text-navy-foreground p-10 lg:p-16 grid lg:grid-cols-[1.4fr_1fr] gap-10 items-center">
          <div>
            <Eyebrow tone="muted" className="!text-white/55">Готовы начать</Eyebrow>
            <h2 className="mt-4 text-[32px] lg:text-[44px] font-medium tracking-[-0.025em] leading-[1.05]">
              Подключите ORGON<br />за один разговор
            </h2>
            <p className="mt-4 text-white/70 text-[15px] leading-[1.55] max-w-xl">
              Покажем платформу, обсудим интеграцию с вашей системой,
              согласуем условия. Без обязательств.
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
              <Button variant="primary" size="lg" fullWidth>
                Запросить демо
                <Icon icon="solar:arrow-right-linear" className="text-[15px]" />
              </Button>
            </a>
            <Link href="/pricing">
              <Button
                variant="secondary"
                size="lg"
                fullWidth
                className="!bg-transparent !border-white/30 !text-white hover:!bg-white/10"
              >
                Сравнить тарифы
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
