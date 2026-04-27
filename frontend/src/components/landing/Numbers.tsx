// Numbers — KPI strip
// 7-of-15 (concrete max policy), <2с broadcast latency, 5 tiles total.

"use client";

import { Eyebrow, BigNum, Mono } from "@/components/ui/primitives";
import { Reveal, RevealItem } from "./Reveal";

const KPIS = [
  { label: "Сетей",     value: "7+",      caption: "EVM + TRON" },
  { label: "Политика",  value: "7-of-15", caption: "макс. подписантов" },
  { label: "Регионы",   value: "3",       caption: "KG · KZ · UZ" },
  { label: "Подписи",   value: "<5м",     caption: "среднее время" },
  { label: "Broadcast", value: "<2с",     caption: "latency p95" },
];

export function Numbers() {
  return (
    <section className="border-b border-border bg-muted/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-16 lg:py-20">
        <div className="flex items-baseline justify-between flex-wrap gap-3 mb-8">
          <Eyebrow dash>В цифрах</Eyebrow>
          <Mono size="xs" className="text-faint">метрики платформы · 04/2026</Mono>
        </div>

        <Reveal stagger={0.06} as="ul" className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-px bg-border border border-border">
          {KPIS.map((k) => (
            <RevealItem key={k.label} as="li" className="bg-card p-5 lg:p-6">
              <Eyebrow>{k.label}</Eyebrow>
              <BigNum size="xl" className="mt-2 block">{k.value}</BigNum>
              <Mono size="xs" className="mt-2 block text-faint">{k.caption}</Mono>
            </RevealItem>
          ))}
        </Reveal>
      </div>
    </section>
  );
}
