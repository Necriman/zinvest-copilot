<script setup>
/**
 * Landing V3 — the playful one.
 *
 * Duolingo's grammar in Zinvest's colours: chunky buttons you press down, round
 * type, colour-block sections, a lesson you can actually play, a winding route
 * of nodes, streaks and leagues. Every section has its own layout, so the page
 * never repeats a pattern: split hero, ticker, pop-out cards, a live lesson, a
 * path, a bento, a dark chat band, a phone, a carousel, an accordion, a banner.
 *
 * The palette is the bear's own: purple (brand), the arrow's yellow, the
 * chain's blue, plus green for "right" and coral for "spent". Tokens live on
 * .z3 below and flip for the dark theme. The earlier landings stay at /v2 and
 * /old.
 */
import AiChat from '@/components/landing/v3/AiChat.vue'
import FaqV3 from '@/components/landing/v3/FaqV3.vue'
import FinalCta from '@/components/landing/v3/FinalCta.vue'
import HeroV3 from '@/components/landing/v3/HeroV3.vue'
import LessonMock from '@/components/landing/v3/LessonMock.vue'
import Motivation from '@/components/landing/v3/Motivation.vue'
import PathV3 from '@/components/landing/v3/PathV3.vue'
import Personas from '@/components/landing/v3/Personas.vue'
import Steps from '@/components/landing/v3/Steps.vue'
import TelegramBot from '@/components/landing/v3/TelegramBot.vue'
import TopicTicker from '@/components/landing/v3/TopicTicker.vue'
</script>

<template>
  <div class="z3">
    <HeroV3 />
    <TopicTicker />
    <Steps />
    <LessonMock />
    <PathV3 />
    <Motivation />
    <AiChat />
    <TelegramBot />
    <Personas />
    <FaqV3 />
    <FinalCta />
  </div>
</template>

<style>
/* Tokens and the few shared pieces every V3 section uses. Not scoped: the
   section components are children and read them. */
.z3 {
  --z3-font: 'Nunito', 'Plus Jakarta Sans', system-ui, sans-serif;
  --z3-ink: #221d3f;
  --z3-muted: #635e82;
  --z3-bg: #ffffff;
  --z3-line: #e9e4f7;
  --z3-card: #ffffff;
  --z3-card-edge: #e3ddf4;

  --z3-purple: #6c47e6;
  --z3-purple-edge: #4f2fc0;
  --z3-purple-soft: #f2edff;
  --z3-yellow: #ffc933;
  --z3-yellow-edge: #dca300;
  --z3-yellow-soft: #fff5d6;
  --z3-blue: #2b95f5;
  --z3-blue-edge: #1874cf;
  --z3-blue-soft: #e5f3ff;
  --z3-green: #33c26a;
  --z3-green-edge: #229a51;
  --z3-green-ink: #17753c;
  --z3-green-soft: #e3f8ea;
  --z3-coral: #ff6b5e;
  --z3-coral-edge: #d9493d;
  --z3-coral-ink: #b8352b;
  --z3-coral-soft: #ffebe8;

  background: var(--z3-bg);
  color: var(--z3-ink);
  font-family: var(--z3-font);
  overflow-x: clip;
}
.dark .z3 {
  --z3-ink: #f4f1ff;
  --z3-muted: #aaa4cb;
  --z3-bg: #110e23;
  --z3-line: #2a2449;
  --z3-card: #1a1633;
  --z3-card-edge: #2d2753;
  --z3-purple: #8a6bff;
  --z3-purple-edge: #6546e0;
  --z3-purple-soft: #1f1942;
  --z3-yellow-soft: #2a2310;
  --z3-blue-soft: #0f2136;
  --z3-green-ink: #62dc93;
  --z3-green-soft: #0f271b;
  --z3-coral-ink: #ff9a90;
  --z3-coral-soft: #2c1513;
}

.z3-section {
  position: relative;
  padding: 5.5rem 1.5rem;
}
@media (min-width: 1024px) {
  .z3-section {
    padding: 7rem 1.5rem;
  }
}
.z3-wrap {
  max-width: 72rem;
  margin: 0 auto;
}
.z3-eyebrow {
  font: 800 0.8rem/1 var(--z3-font);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--z3-purple);
}
.z3-h2 {
  margin-top: 0.9rem;
  font: 900 clamp(2rem, 1.3rem + 2.6vw, 3.1rem) / 1.05 var(--z3-font);
  letter-spacing: -0.02em;
  color: var(--z3-ink);
  text-wrap: balance;
}
.z3-lede {
  margin-top: 1.1rem;
  font-family: var(--z3-font);
  font-weight: 600;
  font-size: 1.1rem;
  line-height: 1.6;
  color: var(--z3-muted);
  max-width: 44ch;
}
.z3-icon {
  display: block;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
}
/* Gentle float for the 3D icons; off for reduced motion. */
@keyframes z3-float {
  0%, 100% { transform: translateY(0) rotate(var(--z3-rot, 0deg)); }
  50% { transform: translateY(-10px) rotate(var(--z3-rot, 0deg)); }
}
.z3-float {
  animation: z3-float 4.8s ease-in-out infinite;
}
@media (prefers-reduced-motion: reduce) {
  .z3-float {
    animation: none;
  }
}
</style>
