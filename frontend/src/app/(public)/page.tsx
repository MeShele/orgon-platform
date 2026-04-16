import { Hero } from '@/components/landing/HeroNew';
import { Features } from '@/components/landing/FeaturesNew';
import { Stats } from '@/components/landing/Stats';
import { CTA } from '@/components/landing/CTA';

export default function LandingPage() {
  return (
    <>
      <Hero />
      <Features />
      <Stats />
      <CTA />
    </>
  );
}
