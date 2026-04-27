// TrustRow v3 — pilot logos as Magic UI Marquee + compliance cards.

"use client";

import { Eyebrow, Mono } from "@/components/ui/primitives";
import { Reveal, RevealItem } from "./Reveal";
import { Marquee } from "@/components/magicui/marquee";

const CLIENTS = [
  { name: "PILOT 01", kind: "PILOT" },
  { name: "PILOT 02", kind: "PILOT" },
  { name: "PILOT 03", kind: "PARTNER" },
  { name: "PILOT 04", kind: "PILOT" },
  { name: "PILOT 05", kind: "PARTNER" },
  { name: "PILOT 06", kind: "PILOT" },
];

const COMPLIANCE = [
  { code: "FATF",   label: "Travel Rule",  status: "implemented" },
  { code: "ISO",    label: "27001:2022",   status: "in progress" },
  { code: "SOC 2",  label: "Type I",       status: "in progress" },
];

export function TrustRow() {
  return (
    <section className="border-b border-border bg-muted/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-12 lg:py-14">
        <div className="flex items-baseline justify-between flex-wrap gap-2">
          <Eyebrow dash>В работе с</Eyebrow>
          <Mono size="xs" className="text-faint">пилотные интеграции · 2026</Mono>
        </div>

        {/* Edge-to-edge marquee */}
        <div className="mt-5 relative border-y border-border bg-card overflow-hidden">
          <Marquee pauseOnHover className="[--duration:35s] [--gap:0px] py-0">
            {CLIENTS.map((c) => (
              <div
                key={c.name}
                className="px-8 py-7 min-w-[220px] border-r border-border flex flex-col justify-between gap-3"
              >
                <div className="font-medium tracking-[0.04em] text-[14px] text-foreground">
                  {c.name}
                </div>
                <Mono size="xs" className="text-faint">{c.kind}</Mono>
              </div>
            ))}
          </Marquee>
          {/* Edge fades */}
          <div className="pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-card to-transparent" />
          <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-card to-transparent" />
        </div>

        <div className="mt-10 flex items-baseline justify-between flex-wrap gap-2">
          <Eyebrow dash>Соответствие</Eyebrow>
          <Mono size="xs" className="text-faint">обновлено 04 / 2026</Mono>
        </div>

        <Reveal stagger={0.06}>
          <ul className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-px bg-border border border-border">
            {COMPLIANCE.map((c) => (
              <RevealItem
                key={c.code}
                as="li"
                className="bg-card px-5 py-5 flex items-center justify-between gap-4 transition-colors hover:bg-muted"
              >
                <div>
                  <div className="font-mono text-[11px] tracking-[0.10em] uppercase text-faint">
                    {c.code}
                  </div>
                  <div className="mt-1 text-[15px] tracking-[-0.01em] text-foreground">
                    {c.label}
                  </div>
                </div>
                <ComplianceTag status={c.status} />
              </RevealItem>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  );
}

function ComplianceTag({ status }: { status: string }) {
  const isLive = status === "implemented";
  return (
    <span
      className={
        "inline-flex items-center gap-2 px-2 py-1 border font-mono text-[10px] tracking-[0.08em] uppercase " +
        (isLive
          ? "border-success/40 text-success bg-success/5"
          : "border-strong text-muted-foreground bg-background")
      }
    >
      <span className={"w-1.5 h-1.5 " + (isLive ? "bg-success" : "bg-strong")} />
      {status}
    </span>
  );
}
