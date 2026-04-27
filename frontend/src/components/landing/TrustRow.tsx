// TrustRow — placeholder client logos (anonymized) + compliance badges
// Replace CLIENTS[] with real names once contracts allow disclosure.

import { Eyebrow, Mono } from "@/components/ui/primitives";

const CLIENTS = [
  { name: "PILOT 01", kind: "PILOT" },
  { name: "PILOT 02", kind: "PILOT" },
  { name: "PILOT 03", kind: "PARTNER" },
  { name: "PILOT 04", kind: "PILOT" },
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

        <ul className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-px bg-border border border-border">
          {CLIENTS.map((c) => (
            <li key={c.name} className="bg-card px-5 py-6 flex flex-col justify-between min-h-[88px]">
              <div className="font-medium tracking-[0.04em] text-[14px] text-foreground">
                {c.name}
              </div>
              <Mono size="xs" className="mt-3 text-faint">{c.kind}</Mono>
            </li>
          ))}
        </ul>

        <div className="mt-10 flex items-baseline justify-between flex-wrap gap-2">
          <Eyebrow dash>Соответствие</Eyebrow>
          <Mono size="xs" className="text-faint">обновлено 04 / 2026</Mono>
        </div>

        <ul className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-px bg-border border border-border">
          {COMPLIANCE.map((c) => (
            <li key={c.code} className="bg-card px-5 py-5 flex items-center justify-between gap-4">
              <div>
                <div className="font-mono text-[11px] tracking-[0.10em] uppercase text-faint">
                  {c.code}
                </div>
                <div className="mt-1 text-[15px] tracking-[-0.01em] text-foreground">
                  {c.label}
                </div>
              </div>
              <ComplianceTag status={c.status} />
            </li>
          ))}
        </ul>
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
