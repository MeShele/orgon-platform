// /billing/success — Stripe Checkout return URL.
// The actual subscription activation happens server-side in the
// /api/v1/billing/webhook handler — this page just confirms to the user
// that payment went through.

"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";

export default function BillingSuccessPage() {
  const params = useSearchParams();
  const sessionId = params.get("session_id");

  useEffect(() => {
    // Brief pause to let the webhook flip the subscription to active.
    // We don't poll — webhooks normally land within a few seconds and the
    // user can refresh /billing themselves.
  }, [sessionId]);

  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-2xl px-4 sm:px-6 lg:px-10 py-24 text-center">
        <Eyebrow dash tone="primary" className="!justify-center">
          Платёж получен
        </Eyebrow>
        <div className="mt-8 inline-flex h-16 w-16 items-center justify-center bg-success/10">
          <Icon icon="solar:check-circle-bold" className="text-3xl text-success" />
        </div>
        <h1 className="mt-6 text-[32px] sm:text-[40px] font-medium tracking-[-0.02em] text-foreground">
          Спасибо!
        </h1>
        <p className="mt-4 max-w-md mx-auto text-[15px] leading-[1.6] text-muted-foreground">
          Подписка активируется в течение нескольких секунд. Вы получите
          подтверждение на почту, а в дашборде увидите новый тариф на
          странице{" "}
          <Link href="/billing" className="text-primary underline-offset-4 hover:underline">
            Биллинг
          </Link>
          .
        </p>
        {sessionId && (
          <p className="mt-3 font-mono text-[11px] text-faint">
            Stripe session: {sessionId.slice(0, 16)}…
          </p>
        )}

        <div className="mt-10 flex items-center justify-center gap-4">
          <Link href="/dashboard">
            <Button variant="primary" size="md">
              В кабинет&nbsp;→
            </Button>
          </Link>
          <Link
            href="/billing"
            className="text-[14px] text-muted-foreground hover:text-foreground transition-colors"
          >
            К тарифам
          </Link>
        </div>
      </div>
    </section>
  );
}
