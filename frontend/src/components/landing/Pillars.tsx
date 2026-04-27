// Pillars v3 — light, scroll-revealed. Flagship gets a 2px crimson outline,
// supporting cards have hover-border-strong; nothing navy.

"use client";

import { Eyebrow, Mono } from "@/components/ui/primitives";
import { Reveal, RevealItem } from "./Reveal";

export function Pillars() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-24">
        <Reveal>
          <div className="grid lg:grid-cols-[1.4fr_1fr] gap-10 lg:gap-16 items-end mb-12">
            <div>
              <Eyebrow dash>Платформа</Eyebrow>
              <h2 className="mt-3 text-[32px] sm:text-[40px] lg:text-[48px] font-medium tracking-[-0.02em] text-foreground text-balance">
                Три слоя одной операционной модели.
              </h2>
            </div>
            <p className="text-[15px] leading-[1.55] text-muted-foreground max-w-md">
              Мы не делаем кошелёк. Мы делаем периметр, в котором кошельки,
              политики подписи и комплаенс остаются под контролем
              оператора, а не пользователя.
            </p>
          </div>
        </Reveal>

        <Reveal stagger={0.1} className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-border border border-border">
          {/* FLAGSHIP — light, separated by double crimson outline + size */}
          <RevealItem as="article" className="bg-card p-8 lg:p-12 lg:row-span-2 flex flex-col relative outline outline-2 outline-primary outline-offset-[-1px] transition-colors hover:bg-muted/40">
            <div className="flex items-center justify-between">
              <Mono size="xs" className="text-primary tracking-[0.18em]">01 / КАСТОДИ</Mono>
              <Mono size="xs" className="text-faint">flagship</Mono>
            </div>

            <h3 className="mt-6 text-[28px] lg:text-[36px] font-medium tracking-[-0.02em] leading-tight text-foreground">
              Multi-signature&nbsp;<br className="hidden lg:block" />wallet&nbsp;layer.
            </h3>

            <p className="mt-5 text-[14px] leading-[1.6] text-muted-foreground max-w-md">
              Политики M-of-N до 7-of-15, разделение admin / signer /
              viewer ролей, HSM-ready ключи. Поддержка TRON, Ethereum,
              Polygon, BSC, Arbitrum, Optimism, Base.
            </p>

            <div className="mt-10 flex-1 flex items-center justify-center">
              <MiniNetworkGraph />
            </div>

            <ul className="mt-10 border-t border-border pt-5 space-y-2 font-mono text-[12px]">
              <li className="flex justify-between"><span className="text-faint">› policies</span><span className="text-foreground">M-of-N · admin override</span></li>
              <li className="flex justify-between"><span className="text-faint">› key storage</span><span className="text-foreground">HSM · cold · custodial</span></li>
              <li className="flex justify-between"><span className="text-faint">› networks</span><span className="text-foreground">7+ chains</span></li>
            </ul>
          </RevealItem>

          <RevealItem as="article" className="bg-card p-8 lg:p-10 transition-colors hover:border-strong border border-transparent hover:bg-muted/40">
            <Mono size="xs" className="text-faint tracking-[0.18em]">02 / COMPLIANCE</Mono>
            <h3 className="mt-5 text-[22px] lg:text-[26px] font-medium tracking-[-0.015em] text-foreground">
              KYC · KYB · AML
            </h3>
            <p className="mt-3 text-[13px] leading-[1.6] text-muted-foreground max-w-prose">
              Проверка физлиц и юрлиц, screening против санкционных
              списков, FATF Travel Rule. История проверок не редактируема.
            </p>
            <ul className="mt-6 space-y-1.5 font-mono text-[11px] text-muted-foreground">
              <li>· OFAC · EU · UN · UK · РФ</li>
              <li>· Travel Rule (Sumsub / Notabene)</li>
              <li>· Risk scoring + manual review</li>
            </ul>
          </RevealItem>

          <RevealItem as="article" className="bg-card p-8 lg:p-10 transition-colors hover:border-strong border border-transparent hover:bg-muted/40">
            <Mono size="xs" className="text-faint tracking-[0.18em]">03 / ИНТЕГРАЦИИ</Mono>
            <h3 className="mt-5 text-[22px] lg:text-[26px] font-medium tracking-[-0.015em] text-foreground">
              API & White-label
            </h3>
            <p className="mt-3 text-[13px] leading-[1.6] text-muted-foreground max-w-prose">
              REST / Webhooks / SDK для встраивания в банковские core,
              процессинги и трейдинг-системы. White-label dashboard под
              ваш бренд.
            </p>
            <ul className="mt-6 space-y-1.5 font-mono text-[11px] text-muted-foreground">
              <li>· REST · OpenAPI 3.1</li>
              <li>· Webhook events (signed · broadcast · failed)</li>
              <li>· White-label · custom domain · SSO</li>
            </ul>
          </RevealItem>
        </Reveal>
      </div>
    </section>
  );
}

function MiniNetworkGraph() {
  const size = 220;
  const cx = size / 2, cy = size / 2;
  const r = size * 0.34;
  const hubR = size * 0.10;
  const nodeR = size * 0.07;
  const n = 4;
  const angles = Array.from({ length: n }, (_, i) => (i / n) * Math.PI * 2 - Math.PI / 2);
  const nodes = angles.map((a, i) => ({
    x: cx + r * Math.cos(a),
    y: cy + r * Math.sin(a),
    signed: i < 2,
  }));

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[260px] h-auto">
      {nodes.map((nd, i) => (
        <line
          key={i}
          x1={cx} y1={cy} x2={nd.x} y2={nd.y}
          stroke={nd.signed ? "var(--primary)" : "var(--strong)"}
          strokeWidth={nd.signed ? 1.5 : 1}
          strokeDasharray={nd.signed ? "0" : "3 3"}
        />
      ))}
      <rect
        x={cx - hubR} y={cy - hubR}
        width={hubR * 2} height={hubR * 2}
        fill="var(--primary)"
      />
      <text
        x={cx} y={cy + 3}
        textAnchor="middle"
        fontFamily="var(--font-mono)"
        fontSize="9"
        fill="var(--primary-foreground)"
      >2/4</text>
      {nodes.map((nd, i) => (
        <rect
          key={i}
          x={nd.x - nodeR} y={nd.y - nodeR}
          width={nodeR * 2} height={nodeR * 2}
          fill={nd.signed ? "var(--foreground)" : "var(--muted)"}
          stroke={nd.signed ? "var(--foreground)" : "var(--strong)"}
          strokeWidth={1}
        />
      ))}
    </svg>
  );
}
