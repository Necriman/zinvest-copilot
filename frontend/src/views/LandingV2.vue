<script setup>
/**
 * Landing V2 — the narrative landing.
 *
 * The page argues in order rather than listing: here is the problem, here is
 * the shape of the answer, here is the answer working (try it), here is the
 * road it puts you on, here is who walks it with you, here is what he can do,
 * here is what it adds up to. Every section is its own small component; this
 * file only decides the order, the floor each one stands on, and the ambient
 * light behind all of them.
 *
 * The previous landing is untouched and still served at /old.
 */
import CtaSection from '@/components/landing/CtaSection.vue'
import FaqSection from '@/components/landing/FaqSection.vue'
import WhoItsFor from '@/components/landing/WhoItsFor.vue'
import AiPreview from '@/components/landing/v2/AiPreview.vue'
import DecisionDemo from '@/components/landing/v2/DecisionDemo.vue'
import FlowSection from '@/components/landing/v2/FlowSection.vue'
import HeroV2 from '@/components/landing/v2/HeroV2.vue'
import MeetTheBear from '@/components/landing/v2/MeetTheBear.vue'
import PathPreview from '@/components/landing/v2/PathPreview.vue'
import ProblemSection from '@/components/landing/v2/ProblemSection.vue'
import ProgressStrip from '@/components/landing/v2/ProgressStrip.vue'
</script>

<template>
  <div class="zl2">
    <!-- Ambient light for the whole page, fixed so it does not travel with the
         scroll. Two lamps and a grain, all under 4%: the page should feel lit
         rather than decorated, and nobody should be able to name the effect. -->
    <div class="zl2__ambient" aria-hidden="true" />
    <div class="zl2__grain" aria-hidden="true" />

    <section class="relative overflow-hidden px-4 pb-16 pt-28 sm:pb-24 sm:pt-36">
      <div class="zl2__grid" aria-hidden="true" />
      <HeroV2 />
    </section>

    <ProblemSection />
    <FlowSection />

    <!-- The centrepiece stands on its own floor, so the page visibly stops to
         hand the visitor something to do. -->
    <div class="zl2__band">
      <DecisionDemo />
    </div>

    <PathPreview />
    <!-- From the first landing: who the road is for, once the road is shown. -->
    <WhoItsFor />
    <MeetTheBear />

    <div class="zl2__band">
      <AiPreview />
    </div>

    <ProgressStrip />
    <!-- The questions people ask right before signing up, right before the sign-up. -->
    <FaqSection />
    <CtaSection />
  </div>
</template>

<style scoped>
.zl2 {
  position: relative;
  isolation: isolate;
}

.zl2__ambient {
  position: fixed;
  inset: 0;
  z-index: -2;
  pointer-events: none;
  background:
    radial-gradient(
      62% 40% at 78% 8%,
      color-mix(in oklab, var(--brand-500) 9%, transparent),
      transparent 68%
    ),
    radial-gradient(
      54% 38% at 12% 72%,
      color-mix(in oklab, var(--brand-500) 6%, transparent),
      transparent 70%
    );
  opacity: 0.55;
}
.dark .zl2__ambient {
  opacity: 1;
}

/* Grain. Static, rasterised once, and low enough that it only shows up as an
   absence of banding on the large soft gradients above. */
.zl2__grain {
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  opacity: 0.025;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3'/%3E%3C/filter%3E%3Crect width='120' height='120' filter='url(%23n)'/%3E%3C/svg%3E");
}
.dark .zl2__grain {
  opacity: 0.04;
}

/* Graph paper behind the hero only — it belongs to the first screen, and
   running it down the whole page would turn texture into wallpaper. */
.zl2__grid {
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
.dark .zl2__grid {
  opacity: 0.85;
}

/* A band is a change of floor, not a box: full-bleed, hairline top and
   bottom, and a surface a shade off the canvas. */
.zl2__band {
  border-top: 1px solid var(--color-hairline);
  border-bottom: 1px solid var(--color-hairline);
  background-color: color-mix(in oklab, var(--surface) 55%, transparent);
}
</style>
