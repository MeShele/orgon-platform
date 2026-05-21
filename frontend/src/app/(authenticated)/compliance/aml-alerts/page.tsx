"use client";

// AML alert triage standalone route.
//
// Previously the only entry to the real Wave 21 triage queue was the
// /compliance index page's "AML" tab — and /compliance itself is
// sidebar-marked `roadmap: true`, hidden behind the "Скоро" badge.
// A compliance-officer doing daily triage would naturally look at
// sidebar items, not under a roadmap-flagged dashboard.
//
// This route fixes the visibility gap: dedicated AML-triage URL,
// surfaced as a first-class sidebar entry, no roadmap pollution.
// Implementation is a thin wrapper around `<AmlAlertList />` — the
// same component the /compliance AML tab uses, so behaviour is
// identical (claim / resolve / notes / SAR via drawer + URL state).

import { Suspense } from "react";
import { Header } from "@/components/layout/Header";
import { Icon } from "@/lib/icons";
import { AmlAlertList } from "@/components/compliance/AmlAlertList";

export default function AmlAlertsPage() {
  return (
    <>
      <Header title="AML очередь" />
      <div className="p-2 sm:p-4 md:p-6 lg:p-8 space-y-6">
        <div className="flex items-start gap-3 rounded-lg border border-primary/30 bg-primary/5 p-4 text-[13px]">
          <Icon icon="solar:shield-warning-bold" className="text-primary mt-0.5 shrink-0 text-base" />
          <div className="text-foreground">
            <div className="font-medium">Очередь подозрительных транзакций</div>
            <div className="mt-1 text-muted-foreground">
              Источник — Sumsub-bridge (sanctions / AML_RISK / PEP labels)
              и in-house transaction rule engine (threshold / velocity /
              blacklist_address / recipient_geo). SAR-submission flow
              живёт внутри drawer'а каждого алерта.
            </div>
          </div>
        </div>
        {/* Suspense — useSearchParams() в AmlAlertList требует boundary
            под Next.js app router'ом, иначе SSR падает на pre-render
            этой страницы. */}
        <Suspense fallback={null}>
          <AmlAlertList />
        </Suspense>
      </div>
    </>
  );
}
