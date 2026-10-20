<script setup>
/**
 * Landing V4: compound interest, told plainly.
 *
 * One idea carries the page: money favours those who understand it, and
 * understanding compounds like interest, five minutes at a time. The hero is
 * a generated shot scrubbed by scroll (the camera glides along a row of coin
 * stacks on a graphite table, each taller than the last); the section after
 * it lets the visitor run ten years of compound interest themselves; the rest
 * shows how a lesson goes, what is inside the app, who it is for, the
 * questions, and the one call to action over the hero's own ending.
 *
 * Built to the 10k-websites standard: one committed world (graphite studio,
 * gold coins, a trace of the brand violet), a type trio (Geologica with its
 * sharp cut, Onest, JetBrains Mono), no two neighbouring sections on the same
 * skeleton, one fixed environment layer behind the whole page, transform and
 * opacity only, reduced motion honoured everywhere. Minimal on purpose: no
 * mascots, no illustrations, the numbers and the footage do the work.
 *
 * Earlier landings stay at /v3 (Duolingo-style), /v2 and /old.
 */
import { onBeforeUnmount, onMounted } from 'vue'

import CompoundLab from '@/components/landing/v4/CompoundLab.vue'
import FaqV4 from '@/components/landing/v4/FaqV4.vue'
import FinalV4 from '@/components/landing/v4/FinalV4.vue'
import HeroScrub from '@/components/landing/v4/HeroScrub.vue'
import InsideApp from '@/components/landing/v4/InsideApp.vue'
import LessonSteps from '@/components/landing/v4/LessonSteps.vue'
import WhoRows from '@/components/landing/v4/WhoRows.vue'

// Every loop on the page stops while the tab is hidden.
const onVisibility = () => document.body.classList.toggle('z4-paused', document.hidden)
onMounted(() => document.addEventListener('visibilitychange', onVisibility))
onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisibility)
  document.body.classList.remove('z4-paused')
})
</script>

<template>
  <div class="z4">
    <div class="z4-env" aria-hidden="true">
      <i class="z4-env__glow z4-env__glow--a" />
      <i class="z4-env__glow z4-env__glow--b" />
      <i class="z4-env__grain" />
    </div>

    <HeroScrub />
    <CompoundLab />
    <LessonSteps />
    <InsideApp />
    <WhoRows />
    <FaqV4 />
    <FinalV4 />
  </div>
</template>

<style>
/* Tokens and the shared pieces. Not scoped: the sections are children. */
.z4 {
  --z4-canvas: #0f0e14; /* graphite, tinted toward the footage's violet */
  --z4-panel: #16151d;
  --z4-panel-2: #1c1a26;
  --z4-line: rgba(220, 214, 255, 0.1);
  --z4-edge: #5d5a70; /* interactive borders, 3:1 on the panels */
  --z4-text: #f2f0ea;
  --z4-text-2: #b6b3c1;
  --z4-text-3: #908d9e;
  --z4-violet: #6f55e0;
  --z4-violet-2: #b3a3f5;
  --z4-aurora: #86cfb0; /* "right" in the product fragments */
  --z4-ice: #d9c8a0;
  --z4-gold: #e6be6a; /* the coins' gold: the call to action and rare emphasis */
  --z4-gold-hover: #f0cd84;
  --z4-gold-ink: #1d1604;

  --z4-display: 'Geologica', 'Onest', system-ui, sans-serif;
  --z4-body: 'Onest', system-ui, sans-serif;
  --z4-mono: 'JetBrains Mono', ui-monospace, 'SFMono-Regular', monospace;

  --z4-ease: cubic-bezier(0.22, 1, 0.36, 1);
  --z4-ease-io: cubic-bezier(0.65, 0, 0.35, 1);
  --z4-tshadow: 0 1px 2px rgba(5, 5, 16, 0.9), 0 3px 12px rgba(5, 5, 16, 0.6), 0 10px 44px rgba(5, 5, 16, 0.55);

  position: relative;
  isolation: isolate;
  overflow-x: clip;
  background: var(--z4-canvas);
  color: var(--z4-text);
  font-family: var(--z4-body);
  animation: z4-page 0.8s var(--z4-ease) both;
}
@keyframes z4-page {
  from {
    opacity: 0;
  }
}
.z4 > section {
  position: relative;
  z-index: 1;
}

/* ---- the one environment behind everything ------------------------------ */
.z4-env {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}
.z4-env__glow {
  position: absolute;
  width: 80vmax;
  height: 80vmax;
  border-radius: 50%;
}
.z4-env__glow--a {
  left: -30vmax;
  top: -20vmax;
  background: radial-gradient(closest-side, rgba(111, 85, 224, 0.13), transparent);
  animation: z4-drift-a 90s ease-in-out infinite alternate -20s;
}
.z4-env__glow--b {
  right: -34vmax;
  bottom: -30vmax;
  background: radial-gradient(closest-side, rgba(230, 190, 106, 0.06), transparent);
  animation: z4-drift-b 120s ease-in-out infinite alternate -40s;
}
@keyframes z4-drift-a {
  to {
    transform: translate(22vmax, 18vmax) scale(1.15);
  }
}
@keyframes z4-drift-b {
  to {
    transform: translate(-20vmax, -16vmax) scale(0.9);
  }
}
/* A still film grain, so the flat graphite reads as a surface, not a void. */
.z4-env__grain {
  position: absolute;
  inset: 0;
  opacity: 0.05;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

/* ---- shared type and layout ---------------------------------------------- */
.z4-section {
  padding-block: clamp(5.5rem, 4rem + 6vw, 10rem);
}
.z4-wrap {
  width: 100%;
  max-width: 76rem;
  margin-inline: auto;
  padding-inline: 1.25rem;
}
@media (min-width: 640px) {
  .z4-wrap {
    padding-inline: 2rem;
  }
}
.z4-kicker {
  font: 500 0.78rem/1.2 var(--z4-mono);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--z4-violet-2);
}
.z4-h2 {
  margin-top: 1.1rem;
  font: 650 clamp(2.2rem, 1.4rem + 2.8vw, 3.9rem) / 1.02 var(--z4-display);
  font-variation-settings: 'SHRP' 60;
  letter-spacing: -0.035em;
  color: var(--z4-text);
  text-wrap: balance;
}
.z4-lede {
  margin-top: 1.25rem;
  max-width: 42ch;
  font: 400 clamp(1.05rem, 0.98rem + 0.3vw, 1.2rem) / 1.6 var(--z4-body);
  color: var(--z4-text-2);
}

/* The one call to action: the arrow's gold. The ghost is its quiet partner. */
.z4-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3.4rem;
  padding: 0 1.7rem;
  border-radius: 999px;
  background: var(--z4-gold);
  color: var(--z4-gold-ink);
  font: 600 1.02rem/1 var(--z4-body);
  text-decoration: none;
  isolation: isolate;
  transition:
    background-color 0.3s var(--z4-ease),
    transform 0.3s var(--z4-ease);
}
.z4-btn::after {
  /* the glow lives on a pseudo-element and fades in, never the shadow itself */
  content: '';
  position: absolute;
  inset: -6px;
  z-index: -1;
  border-radius: inherit;
  box-shadow: 0 0 32px rgba(255, 201, 74, 0.45);
  opacity: 0;
  transition: opacity 0.35s var(--z4-ease);
}
.z4-btn:hover {
  background: var(--z4-gold-hover);
  transform: translateY(-1px);
}
.z4-btn:hover::after {
  opacity: 1;
}
.z4-btn:active {
  transform: translateY(0) scale(0.98);
}
.z4-btn:focus-visible {
  outline: 2px solid var(--z4-gold);
  outline-offset: 3px;
}
.z4-btn--ghost {
  background: rgba(13, 11, 34, 0.35);
  color: var(--z4-text);
  box-shadow: inset 0 0 0 1px var(--z4-edge);
  backdrop-filter: blur(8px);
}
.z4-btn--ghost::after {
  display: none;
}
.z4-btn--ghost:hover {
  background: rgba(236, 238, 251, 0.1);
}

/* ---- entrances: [data-in] children arrive in sequence once .in lands ----- */
.z4 [data-in] {
  transition:
    opacity 0.9s var(--z4-ease),
    transform 0.9s var(--z4-ease);
}
.z4 section:not(.in) [data-in] {
  opacity: 0;
  transform: translateY(22px);
}
.z4 section.in [data-in] {
  opacity: 1;
  transform: none;
  transition-delay: calc(var(--i, 0) * 90ms);
}
/* Once the entrance is over, the stagger retires so hovers answer at once. */
.z4 section.in.done [data-in] {
  transition-delay: 0s;
}

/* ---- pause and reduced motion -------------------------------------------- */
body.z4-paused .z4 *,
body.z4-paused .z4 *::before,
body.z4-paused .z4 *::after {
  animation-play-state: paused !important;
}
@media (prefers-reduced-motion: reduce) {
  .z4,
  .z4 *,
  .z4 *::before,
  .z4 *::after {
    animation: none !important;
    transition: none !important;
    transition-delay: 0s !important;
  }
  .z4 section [data-in] {
    opacity: 1;
    transform: none;
  }
}
</style>
