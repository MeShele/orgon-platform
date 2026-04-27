// FlowSection v3 — light surface, no ink/navy block.
// Visual rhythm comes from a vertical crimson rail + larger heading,
// not from inverse-contrast colour. Steps animate in sequentially.

"use client";

import { Mono } from "@/components/ui/primitives";
import { Reveal, RevealItem } from "./Reveal";

const STEPS = [
  { n: "01", title: "WALLET",    meta: "treasury · main",  detail: "0x4f2a · · b81c",   time: "14:18" },
  { n: "02", title: "POLICY",    meta: "3 of 5 + admin",   detail: "ETA · 4м 12с",       time: "14:22" },
  { n: "03", title: "BROADCAST", meta: "TRON · mainnet",   detail: "auto · gas locked",  time: "14:23" },
  { n: "04", title: "AUDIT",     meta: "log · immutable",  detail: "+ 6 events",         time: "14:23" },
];

export function FlowSection() {
  return (
    <section className="border-b border-border bg-muted/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-28">
        <div className="grid lg:grid-cols-[1fr_1.4fr] gap-10 lg:gap-16 items-start">
          <Reveal>
            <Mono size="xs" className="text-primary tracking-[0.18em]">— КАК ЭТО РАБОТАЕТ</Mono>
            <h2 className="mt-4 text-[32px] sm:text-[40px] lg:text-[48px] font-medium tracking-[-0.02em] leading-[1.05] text-balance text-foreground">
              Транзакция проходит четыре периметра.
            </h2>
            <p className="mt-6 max-w-md text-[15px] leading-[1.6] text-muted-foreground">
              Каждый шаг — отдельная политика, отдельная роль, отдельная
              запись в журнале. Если хоть один периметр не прошёл —
              транзакция не уходит в сеть.
            </p>
          </Reveal>

          <Reveal stagger={0.08}>
            <ol className="grid grid-cols-1 md:grid-cols-2 gap-px bg-border border border-border">
              {STEPS.map((s, i) => (
                <RevealItem
                  key={s.n}
                  as="li"
                  className="bg-card p-6 lg:p-7 relative transition-colors hover:bg-background"
                >
                  <div className="flex items-baseline justify-between">
                    <Mono size="xs" className="text-primary tracking-[0.18em]">{s.n}</Mono>
                    <Mono size="xs" className="text-faint">{s.time}</Mono>
                  </div>
                  <div className="mt-4 text-[20px] lg:text-[22px] font-medium tracking-[-0.01em] text-foreground">
                    {s.title}
                  </div>
                  <div className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 font-mono text-[11px]">
                    <span className="text-faint">›</span>
                    <span className="text-foreground">{s.meta}</span>
                    <span className="text-faint">›</span>
                    <span className="text-faint">{s.detail}</span>
                  </div>
                  {i < STEPS.length - 1 && i % 2 === 0 && (
                    <div className="hidden md:block absolute -right-[9px] top-1/2 -translate-y-1/2 z-10">
                      <span className="block w-[18px] h-px bg-primary" />
                    </div>
                  )}
                </RevealItem>
              ))}
            </ol>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
