// ORGON · Crimson Ledger v2 — Landing
// PublicHeader/PublicFooter сидят в (public)/layout.tsx — здесь только секции.

import { Hero } from "@/components/landing/Hero";
import { TrustRow } from "@/components/landing/TrustRow";
import { Pillars } from "@/components/landing/Pillars";
import { Numbers } from "@/components/landing/Numbers";
import { FlowSection } from "@/components/landing/FlowSection";
import { BottomCTA } from "@/components/landing/BottomCTA";

export default function HomePage() {
  return (
    <>
      <Hero />
      <TrustRow />
      <Pillars />
      <Numbers />
      <FlowSection />
      <BottomCTA />
    </>
  );
}
