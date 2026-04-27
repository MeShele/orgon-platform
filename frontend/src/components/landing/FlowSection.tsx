// FlowSection v2 — surface-contrast (ink in light, navy in dark)

import { Mono } from "@/components/ui/primitives";

export function FlowSection() {
  return (
    <section className="bg-[color:var(--surface-contrast)] text-[color:var(--surface-contrast-foreground)]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-28">
        <div className="grid lg:grid-cols-[1fr_1.4fr] gap-10 lg:gap-16 items-start">
          <div>
            <Mono size="xs" className="text-primary tracking-[0.18em]">— КАК ЭТО РАБОТАЕТ</Mono>
            <h2 className="mt-4 text-[32px] sm:text-[40px] lg:text-[48px] font-medium tracking-[-0.02em] leading-[1.05] text-balance">
              Транзакция проходит четыре периметра.
            </h2>
            <p className="mt-6 max-w-md text-[15px] leading-[1.6] text-[color:var(--surface-contrast-faint)]">
              Каждый шаг — отдельная политика, отдельная роль, отдельная
              запись в журнале. Если хоть один периметр не прошёл —
              транзакция не уходит в сеть.
            </p>
          </div>

          <div className="lg:pt-2">
            <TxFlowV2 />
          </div>
        </div>
      </div>
    </section>
  );
}

function TxFlowV2() {
  const steps = [
    { n: "01", title: "WALLET",    meta: "treasury · main",  detail: "0x4f2a · · b81c",   time: "14:18" },
    { n: "02", title: "POLICY",    meta: "3 of 5 + admin",   detail: "ETA · 4м 12с",       time: "14:22" },
    { n: "03", title: "BROADCAST", meta: "TRON · mainnet",   detail: "auto · gas locked",  time: "14:23" },
    { n: "04", title: "AUDIT",     meta: "log · immutable",  detail: "+ 6 events",         time: "14:23" },
  ];

  return (
    <ol className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[color:var(--surface-contrast-border)] border border-[color:var(--surface-contrast-border)]">
      {steps.map((s, i) => (
        <li key={s.n} className="bg-[color:var(--surface-contrast)] p-6 lg:p-7 relative">
          <div className="flex items-baseline justify-between">
            <Mono size="xs" className="text-primary tracking-[0.18em]">{s.n}</Mono>
            <Mono size="xs" className="text-[color:var(--surface-contrast-faint)]">{s.time}</Mono>
          </div>
          <div className="mt-4 text-[20px] lg:text-[22px] font-medium tracking-[-0.01em]">
            {s.title}
          </div>
          <div className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 font-mono text-[11px]">
            <span className="text-[color:var(--surface-contrast-faint)]">›</span>
            <span>{s.meta}</span>
            <span className="text-[color:var(--surface-contrast-faint)]">›</span>
            <span className="text-[color:var(--surface-contrast-faint)]">{s.detail}</span>
          </div>
          {i < steps.length - 1 && (
            <div className="hidden md:block absolute -right-[9px] top-1/2 -translate-y-1/2 z-10">
              <span className="block w-[18px] h-px bg-primary" />
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
