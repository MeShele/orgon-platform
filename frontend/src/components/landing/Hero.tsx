// Hero v3 — light, scroll-revealed copy + demo snapshot.

"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Button } from "@/components/ui/Button";
import { Eyebrow, BigNum, Mono, StatusPill } from "@/components/ui/primitives";
import { MagneticButton } from "@/components/ui/MagneticButton";
import { TextEffect } from "@/components/motion-primitives/text-effect";

export function Hero() {
  const reduce = useReducedMotion();
  const fadeUp = (delay = 0) =>
    reduce
      ? { initial: { opacity: 1 }, animate: { opacity: 1 } }
      : {
          initial: { opacity: 0, y: 24 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] as const, delay },
        };

  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-16 lg:py-24">
        <div className="grid lg:grid-cols-[1.2fr_1fr] gap-10 lg:gap-16 items-start">
          {/* Left — copy */}
          <div>
            <motion.div {...fadeUp(0)}>
              <Eyebrow dash>Институциональная кастоди-платформа</Eyebrow>
            </motion.div>
            <TextEffect
              as="h1"
              per="word"
              delay={0.1}
              duration={0.55}
              className="mt-5 text-[40px] sm:text-[56px] lg:text-[72px] font-medium leading-[1.02] tracking-[-0.025em] text-foreground text-balance"
            >
              Multi-signature кастоди для регулируемых операторов.
            </TextEffect>
            <motion.p
              {...fadeUp(0.12)}
              className="mt-6 max-w-[58ch] text-[16px] sm:text-[17px] leading-[1.55] text-muted-foreground text-pretty"
            >
              ORGON — операционный слой между кошельком и блокчейном.
              Политики подписи, KYC/KYB/AML и журнал аудита в одном
              периметре, готовом к проверке регулятором.
            </motion.p>

            <motion.div {...fadeUp(0.2)} className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-3">
              <MagneticButton>
                <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
                  <Button variant="primary" size="lg" className="hover:scale-[1.03] active:scale-[0.98] transition-transform">
                    Запросить демо
                  </Button>
                </a>
              </MagneticButton>
              <Link
                href="/pricing"
                className="text-[15px] text-foreground hover:text-primary underline-offset-4 hover:underline transition-colors"
              >
                Смотреть тарифы&nbsp;→
              </Link>
            </motion.div>

            <motion.dl {...fadeUp(0.28)} className="mt-12 grid grid-cols-3 max-w-md gap-px bg-border border border-border">
              <Stat label="Сетей" value="7+" />
              <Stat label="Политика" value="7-of-15" />
              <Stat label="Broadcast" value="<2с" />
            </motion.dl>
          </div>

          {/* Right — live snapshot card */}
          <motion.div {...fadeUp(0.18)}>
            <DemoSnapshot reduce={!!reduce} />
          </motion.div>
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

function DemoSnapshot({ reduce }: { reduce: boolean }) {
  const auditItems = [
    { sym: "✓", color: "text-success", text: "signed · 0x4f··21", time: "14:22" },
    { sym: "✓", color: "text-success", text: "signed · 0xa8··0e", time: "14:21" },
    { sym: "▢", color: "text-warning", text: "created · admin",   time: "14:18" },
  ];

  return (
    <article className="border border-border bg-card transition-shadow hover:shadow-lg">
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

        <div className="border-t border-border pt-4">
          <Eyebrow>Сумма</Eyebrow>
          <div className="mt-1 flex items-baseline gap-3">
            <BigNum size="xl">128 540.00</BigNum>
            <Mono className="text-faint">USDT</Mono>
          </div>
        </div>

        <div className="border-t border-border pt-4">
          <div className="flex items-baseline justify-between">
            <Eyebrow>Политика</Eyebrow>
            <Mono size="xs" className="text-faint">3 of 5 + admin</Mono>
          </div>
          <div className="mt-3 grid grid-cols-5 gap-1.5">
            {[1, 2, 0, 0, 0].map((s, i) => (
              <motion.div
                key={i}
                initial={reduce ? { scaleX: 1 } : { scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: 0.5, delay: 0.5 + i * 0.07, ease: "easeOut" }}
                style={{ transformOrigin: "left" }}
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

        <div className="border-t border-border pt-4">
          <Eyebrow>Audit tail</Eyebrow>
          <ul className="mt-2 space-y-1.5 font-mono text-[11px] text-muted-foreground">
            {auditItems.map((it, i) => (
              <motion.li
                key={i}
                initial={reduce ? { opacity: 1, x: 0 } : { opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: 0.7 + i * 0.1, ease: "easeOut" }}
                className={"flex justify-between gap-3 " + (i === 2 ? "text-foreground" : "")}
              >
                <span><span className={it.color}>{it.sym}</span> {it.text}</span>
                <span className="text-faint">{it.time}</span>
              </motion.li>
            ))}
          </ul>
        </div>
      </div>
    </article>
  );
}
