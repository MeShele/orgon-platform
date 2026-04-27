// BottomCTA v2 — surface-contrast block

import { Button } from "@/components/ui/Button";
import { Mono } from "@/components/ui/primitives";

export function BottomCTA() {
  return (
    <section className="bg-[color:var(--surface-contrast)] text-[color:var(--surface-contrast-foreground)] border-t border-[color:var(--surface-contrast-border)]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 lg:py-24">
        <div className="grid lg:grid-cols-[1.4fr_1fr] gap-10 items-end">
          <div>
            <Mono size="xs" className="text-primary tracking-[0.18em]">— ЗАПРОС ДЕМО</Mono>
            <h2 className="mt-4 text-[32px] sm:text-[40px] lg:text-[52px] font-medium tracking-[-0.02em] leading-[1.05] text-balance">
              Покажем платформу на ваших&nbsp;кейсах.
            </h2>
            <p className="mt-5 max-w-xl text-[15px] leading-[1.6] text-[color:var(--surface-contrast-faint)]">
              30 минут — пройдём политики подписи, KYC/KYB-флоу и
              интеграцию API на примере одной из ваших операций.
            </p>
          </div>

          <div className="flex flex-col gap-3 lg:items-end">
            <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
              <Button variant="primary" size="lg">Запросить демо&nbsp;→</Button>
            </a>
            <Mono size="xs" className="text-[color:var(--surface-contrast-faint)]">
              sales · ответ в течение 1 рабочего дня
            </Mono>
          </div>
        </div>
      </div>
    </section>
  );
}
