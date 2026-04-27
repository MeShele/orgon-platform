// BottomCTA v3 — light card with crimson accent rail.
// Heading scale + crimson left rail does the visual lift, not navy fill.

"use client";

import { Button } from "@/components/ui/Button";
import { Mono } from "@/components/ui/primitives";
import { Reveal } from "./Reveal";
import { MagneticButton } from "@/components/ui/MagneticButton";

export function BottomCTA() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-28">
        <Reveal>
          <div className="bg-card border border-border border-l-[3px] border-l-primary p-10 lg:p-16 grid lg:grid-cols-[1.4fr_1fr] gap-10 items-end">
            <div>
              <Mono size="xs" className="text-primary tracking-[0.18em]">— ЗАПРОС ДЕМО</Mono>
              <h2 className="mt-4 text-[32px] sm:text-[40px] lg:text-[52px] font-medium tracking-[-0.02em] leading-[1.05] text-balance text-foreground">
                Покажем платформу на ваших&nbsp;кейсах.
              </h2>
              <p className="mt-5 max-w-xl text-[15px] leading-[1.6] text-muted-foreground">
                30 минут — пройдём политики подписи, KYC/KYB-флоу и
                интеграцию API на примере одной из ваших операций.
              </p>
            </div>

            <div className="flex flex-col gap-3 lg:items-end">
              <MagneticButton>
                <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
                  <Button variant="primary" size="lg" className="hover:scale-[1.03] active:scale-[0.98] transition-transform">
                    Запросить демо&nbsp;→
                  </Button>
                </a>
              </MagneticButton>
              <Mono size="xs" className="text-faint">
                sales · ответ в течение 1 рабочего дня
              </Mono>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
