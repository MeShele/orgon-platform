// /billing/cancel — Stripe Checkout cancel URL.
// User clicked "back" or closed the checkout tab. Nothing was charged.

"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";

export default function BillingCancelPage() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-2xl px-4 sm:px-6 lg:px-10 py-24 text-center">
        <Eyebrow dash tone="muted" className="!justify-center">
          Оплата отменена
        </Eyebrow>
        <div className="mt-8 inline-flex h-16 w-16 items-center justify-center bg-muted">
          <Icon icon="solar:close-circle-linear" className="text-3xl text-muted-foreground" />
        </div>
        <h1 className="mt-6 text-[32px] sm:text-[40px] font-medium tracking-[-0.02em] text-foreground">
          Платёж не прошёл
        </h1>
        <p className="mt-4 max-w-md mx-auto text-[15px] leading-[1.6] text-muted-foreground">
          С вашей карты ничего не списано. Можно вернуться к тарифам и
          попробовать ещё раз — или написать нам, если возникли вопросы.
        </p>

        <div className="mt-10 flex items-center justify-center gap-4">
          <Link href="/pricing">
            <Button variant="primary" size="md">
              К тарифам
            </Button>
          </Link>
          <a
            href="mailto:sales@orgon.asystem.kg?subject=ORGON%20%E2%80%94%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%20%D0%BF%D0%BE%20%D0%BE%D0%BF%D0%BB%D0%B0%D1%82%D0%B5"
            className="text-[14px] text-muted-foreground hover:text-foreground transition-colors"
          >
            Написать в продажи
          </a>
        </div>
      </div>
    </section>
  );
}
