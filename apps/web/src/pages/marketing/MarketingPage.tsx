import { AmanahSection } from './sections/AmanahSection';
import { DesensitizationSection } from './sections/DesensitizationSection';
import { HeroSection } from './sections/HeroSection';
import { HowItWorksSection } from './sections/HowItWorksSection';
import { MethodologySection } from './sections/MethodologySection';
import { PathSection } from './sections/PathSection';
import { ProblemSection } from './sections/ProblemSection';
import { ResponsibleUseSection } from './sections/ResponsibleUseSection';
import { WhatItDoesSection } from './sections/WhatItDoesSection';

/**
 * Public marketing page.
 *
 * Reads as one argument: each remark already matters and the feed will not
 * keep it, anonymity can lower the cost of saying worse things, a longitudinal
 * record holds the longer view without asking targeted people to absorb every
 * example, that record is itself a trust, and the product is what carrying
 * that trust looks like in practice.
 *
 * Product proof and the methodology detail follow next.
 */
export function MarketingPage() {
  return (
    <>
      <HeroSection />
      <ProblemSection />
      <PathSection />
      <DesensitizationSection />
      <AmanahSection />
      <WhatItDoesSection />
      <HowItWorksSection />
      <ResponsibleUseSection />
      <MethodologySection />
    </>
  );
}
