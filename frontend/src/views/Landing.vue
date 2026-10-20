<script setup>
import AiSection from '@/components/landing/AiSection.vue'
import CtaSection from '@/components/landing/CtaSection.vue'
import Curriculum from '@/components/landing/Curriculum.vue'
import FaqSection from '@/components/landing/FaqSection.vue'
import HeroSection from '@/components/landing/HeroSection.vue'
import HowItWorks from '@/components/landing/HowItWorks.vue'
import PersonalPlan from '@/components/landing/PersonalPlan.vue'
import WhoItsFor from '@/components/landing/WhoItsFor.vue'
</script>

<template>
  <div>
    <!-- Hero. Starts at y=0 (the layout adds no top padding) so it runs behind
         the floating navbar; `pt-28/36` clears the bar for the content. -->
    <section class="relative overflow-hidden px-4 pb-16 pt-28 sm:pb-24 sm:pt-36">
      <!-- Depth, at the edge of visible: a ruled grid that reads as graph paper
           rather than decoration, fading out well before the copy starts. The
           canvas stays the theme's own colour. -->
      <div class="hero-depth" aria-hidden="true" />
      <HeroSection />
    </section>

    <HowItWorks />
    <PersonalPlan />

    <!-- Alternating surface so the long page reads as distinct bands rather
         than one continuous scroll. In dark the band is a touch lighter than
         the page; a translucent surface was indistinguishable from it. -->
    <div class="border-y border-hairline bg-white dark:bg-surface/70">
      <Curriculum />
    </div>

    <WhoItsFor />
    <AiSection />

    <div class="border-y border-hairline bg-white dark:bg-surface/70">
      <FaqSection />
    </div>

    <CtaSection />
  </div>
</template>

<style scoped>
/* One fixed environment layer behind the hero. Two ruled grids at different
   pitches read as graph paper; both are under 4% opacity, so they register as
   texture rather than as a pattern anyone would name. */
.hero-depth {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(to right, color-mix(in oklab, var(--text) 5%, transparent) 1px, transparent 1px),
    linear-gradient(to bottom, color-mix(in oklab, var(--text) 5%, transparent) 1px, transparent 1px);
  background-size: 64px 64px;
  opacity: 0.5;
  -webkit-mask-image: radial-gradient(74% 62% at 50% 34%, #000 0%, transparent 78%);
  mask-image: radial-gradient(74% 62% at 50% 34%, #000 0%, transparent 78%);
}
.dark .hero-depth {
  opacity: 0.85;
}
</style>
