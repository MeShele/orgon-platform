// Hero v2 — landing
// Crimson Ledger v2: no AI-slop decorations, demo card is a static
// live-snapshot with real policy / ETA / audit-tail.

"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Eyebrow, BigNum, Mono, StatusPill } from "@/components/ui/primitives";

export function Hero() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-16 lg:py-24">
        <div className="grid lg:grid-cols-[1.2fr_1fr] gap-10 lg:gap-16 items-start">
          {/* Left — copy */}
          <div>
            <Eyebrow dash>Институциональная кастоди-платформа</Eyebrow>
            <h1 className="mt-5 text-[40px] sm:text-[56px] lg:text-[72px] font-medium leading-[1.02] tracking-[-0.025em] text-foreground text-balance">
              Multi-signature кастоди<br />для регулируемых&nbsp;операторов.
            </h1>
            <p className="mt-6 max-w-[58ch] text-[16px] sm:text-[17px] leading-[1.55] text-muted-foreground text-pretty">
              ORGON — операционный слой между кошельком и блокчейном.
              Политики подписи, KYC/KYB/AML и журнал аудита в одном
              периметре, готовом к проверке регулятором.
            </p>

            <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-3">
              <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
                <Button variant="primary" size="lg">Запросить демо</Button>
              </a>
              <Link
                href="/pricing"
                className="text-[15px] text-foreground hover:text-primary underline-offset-4 hover:underline transition-colors"
              >
                Смотреть тарифы&nbsp;→
              </Link>
            </div>

            <dl className="mt-12 grid grid-cols-3 max-w-md gap-px bg-border border border-border">
              <Stat label="Сетей" value="7+" />
              <Stat label="Политика" value="7-of-15" />
              <Stat label="Broadcast" value="<2с" />
            </dl>
          </div>

          {/* Right — live snapshot card */}
          <DemoSnapshot />
        </div>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-background px-4 py-3">
      <Eyebrow>{label}</Eyebrow>
      <div className="mt-1 font-medium text-[20px] tracking-[-0.01em] tabular text-foreground">
        {value}
      </div>
    </div>
  );
}

function DemoSnapshot() {
  return (
    <article className="border border-border bg-card">
      <header className="flex items-center justify-between px-5 py-3 border-b border-border">
        <Mono size="xs" className="text-faint">TX · pending signature</Mono>
        <StatusPill kind="pending" label="2/5 SIGNED" />
      </header>

      <div className="px-5 py-5 space-y-5">
        {/* From / To */}
        <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-[12px]">
          <span className="text-faint font-mono uppercase tracking-[0.10em] text-[10px]">из</span>
          <Mono className="text-foreground">treasury·main</Mono>
          <span className="text-faint font-mono uppercase tracking-[0.10em] text-[10px]">к</span>
          <Mono className="text-foreground">0x4f2a··b81c</Mono>
          <span className="text-faint font-mono uppercase tracking-[0.10em] text-[10px]">сеть</span>
          <span className="text-foreground">TRON · Mainnet</span>
        </div>

        {/* Amount */}
        <div className="border-t border-border pt-4">
          <Eyebrow>Сумма</Eyebrow>
          <div className="mt-1 flex items-baseline gap-3">
            <BigNum size="xl">128 540.00</BigNum>
            <Mono className="text-faint">USDT</Mono>
          </div>
        </div>

        {/* Policy progress */}
        <div className="border-t border-border pt-4">
          <div className="flex items-baseline justify-between">
            <Eyebrow>Политика</Eyebrow>
            <Mono size="xs" className="text-faint">3 of 5 + admin</Mono>
          </div>
          <div className="mt-3 grid grid-cols-5 gap-1.5">
            {[1, 2, 0, 0, 0].map((s, i) => (
              <div
                key={i}
                className={
                  "h-1.5 " +
                  (s === 2 ? "bg-primary" : s === 1 ? "bg-foreground" : "bg-muted")
                }
              />
            ))}
          </div>
          <div className="mt-3 flex items-center justify-between text-[11px]">
            <Mono className="text-muted-foreground">ETA · 4м 12с</Mono>
            <Mono className="text-faint">авто-broadcast при 3/5</Mono>
          </div>
        </div>

        {/* Audit tail */}
        <div className="border-t border-border pt-4">
          <Eyebrow>Audit tail</Eyebrow>
          <ul className="mt-2 space-y-1.5 font-mono text-[11px] text-muted-foreground">
            <li className="flex justify-between gap-3">
              <span><span className="text-success">✓</span> signed · 0x4f··21</span>
              <span className="text-faint">14:22</span>
            </li>
            <li className="flex justify-between gap-3">
              <span><span className="text-success">✓</span> signed · 0xa8··0e</span>
              <span className="text-faint">14:21</span>
            </li>
            <li className="flex justify-between gap-3 text-foreground">
              <span><span className="text-warning">▢</span> created · admin</span>
              <span className="text-faint">14:18</span>
            </li>
          </ul>
        </div>
      </div>
    </article>
  );
}
