<script setup>
/**
 * How one lesson goes, in three moves. The moves sit in a row joined by one
 * line that draws itself as the section scrolls through, and each numbered node lights when the line reaches it. Under each
 * move is a real fragment of that move (the lesson text, the question, the
 * mentor's explanation), so all three get the same weight.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { vIn } from './inView'

const STEPS = ['s1', 's2', 's3']
const root = ref(null)
const reached = ref(0) // how many nodes the line has passed

let rafId = null
let lastDraw = -1
let io = null
let onScreen = false
let mql = null

function measure() {
  rafId = null
  const el = root.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const vh = window.innerHeight
  // 0 when the row enters the lower fifth of the screen, 1 by mid-screen.
  const p = Math.min(1, Math.max(0, (vh * 0.85 - r.top) / (vh * 0.55)))
  if (Math.abs(p - lastDraw) > 0.004 || (p !== lastDraw && (p === 0 || p === 1))) {
    el.style.setProperty('--draw', p.toFixed(3))
    lastDraw = p
    const n = p >= 0.98 ? 3 : p >= 0.5 ? 2 : p > 0.02 ? 1 : 0
    if (n !== reached.value) reached.value = n
  }
}

function onScroll() {
  if (onScreen && rafId === null) rafId = requestAnimationFrame(measure)
}

function finish() {
  root.value?.style.setProperty('--draw', '1')
  reached.value = 3
}

function onMotion() {
  if (mql.matches) {
    window.removeEventListener('scroll', onScroll)
    finish()
  } else {
    window.addEventListener('scroll', onScroll, { passive: true })
    lastDraw = -1
    onScroll()
  }
}

onMounted(() => {
  mql = window.matchMedia('(prefers-reduced-motion: reduce)')
  mql.addEventListener('change', onMotion)
  if (typeof IntersectionObserver !== 'undefined' && root.value) {
    io = new IntersectionObserver(([entry]) => {
      onScreen = entry.isIntersecting
      onScroll()
    })
    io.observe(root.value)
  } else {
    onScreen = true
  }
  onMotion()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  mql?.removeEventListener('change', onMotion)
  io?.disconnect()
  if (rafId !== null) cancelAnimationFrame(rafId)
})
</script>

<template>
  <section id="how-it-works" v-in class="z4-section zl scroll-mt-24">
    <div class="z4-wrap">
      <header class="zl__head">
        <div>
          <p class="z4-kicker" data-in>{{ $t('v4.steps.eyebrow') }}</p>
          <h2 class="z4-h2" data-in style="--i: 1">{{ $t('v4.steps.title') }}</h2>
        </div>
      </header>

      <ol ref="root" class="zl__row">
        <svg class="zl__track" viewBox="0 0 1000 20" preserveAspectRatio="none" aria-hidden="true">
          <path class="zl__groove" d="M0 7 H1000 M0 13 H1000" />
          <path class="zl__line" d="M0 7 H1000 M0 13 H1000" pathLength="1" />
        </svg>

        <li v-for="(key, i) in STEPS" :key="key" class="zl__step" data-in :style="{ '--i': i + 2 }">
          <span class="zl__node" :class="{ 'is-lit': reached > i }">{{ String(i + 1).padStart(2, '0') }}</span>
          <h3 class="zl__word">{{ $t(`v4.steps.${key}.word`) }}</h3>
          <p class="zl__body">{{ $t(`v4.steps.${key}.body`) }}</p>

          <!-- 1: the lesson text -->
          <div v-if="i === 0" class="zl__card" aria-hidden="true">
            <p class="zl__tag">{{ $t('v4.steps.m1.tag') }}</p>
            <p class="zl__card-title">{{ $t('v4.steps.m1.title') }}</p>
            <p class="zl__card-text">{{ $t('v4.steps.m1.text') }}</p>
            <div class="zl__bar"><i /></div>
          </div>

          <!-- 2: the question -->
          <div v-else-if="i === 1" class="zl__card" aria-hidden="true">
            <p class="zl__card-q">{{ $t('v4.steps.m2.q') }}</p>
            <ul class="zl__opts">
              <li>{{ $t('v4.steps.m2.a1') }}</li>
              <li>{{ $t('v4.steps.m2.a2') }}</li>
              <li class="is-right">
                {{ $t('v4.steps.m2.a3') }}
                <svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
              </li>
            </ul>
          </div>

          <!-- 3: the mentor's explanation -->
          <div v-else class="zl__card zl__card--mentor" aria-hidden="true">
            <span class="zl__avatar">Z</span>
            <p class="zl__bubble">{{ $t('v4.steps.m3.text') }}</p>
          </div>
        </li>
      </ol>
    </div>
  </section>
</template>

<style scoped>
.zl__head {
  max-width: 44rem;
}

.zl__row {
  --draw: 0;
  position: relative;
  margin-top: 4rem;
  display: grid;
  gap: 3.5rem;
  padding-left: 3.25rem;
}
@media (min-width: 900px) {
  .zl__row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 2.25rem;
    padding-left: 0;
    padding-top: 0;
  }
}

/* The groove: horizontal across the tops on wide screens, down the left edge
   on phones. The drawn copy reveals with --draw. */
.zl__track {
  position: absolute;
  overflow: visible;
  pointer-events: none;
}
@media (min-width: 900px) {
  .zl__track {
    left: 1.4rem;
    right: 0;
    top: 1.05rem;
    width: calc(100% - 1.4rem);
    height: 20px;
    transform: translateY(-50%);
  }
}
@media (max-width: 899px) {
  /* On phones the groove runs down the left edge as two plain strokes. */
  .zl__track {
    display: none;
  }
  .zl__row::before,
  .zl__row::after {
    content: '';
    position: absolute;
    left: 1.4rem;
    top: 1.4rem;
    width: 2px;
    height: calc(100% - 1.4rem);
    background: var(--z4-line);
  }
  .zl__row::after {
    background: linear-gradient(to bottom, var(--z4-violet-2), var(--z4-ice));
    transform-origin: 50% 0;
    transform: scaleY(var(--draw));
  }
}
.zl__groove,
.zl__line {
  fill: none;
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}
.zl__groove {
  stroke: var(--z4-line);
}
.zl__line {
  stroke: var(--z4-violet-2);
  stroke-dasharray: 1;
  stroke-dashoffset: calc(1 - var(--draw));
}

.zl__step {
  position: relative;
  display: flex;
  flex-direction: column;
}
.zl__node {
  position: relative;
  z-index: 1;
  display: inline-flex;
  width: 2.8rem;
  height: 2.8rem;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--z4-canvas);
  border: 1px solid var(--z4-edge);
  color: var(--z4-text-3);
  font: 500 0.85rem/1 var(--z4-mono);
  transition: color 0.5s var(--z4-ease), border-color 0.5s var(--z4-ease), box-shadow 0.5s var(--z4-ease);
}
@media (max-width: 899px) {
  .zl__node {
    position: absolute;
    left: -3.25rem;
    top: 0;
  }
}
.zl__node.is-lit {
  color: var(--z4-text);
  border-color: var(--z4-violet-2);
  box-shadow: 0 0 0 6px rgba(111, 85, 224, 0.14), 0 0 24px rgba(111, 85, 224, 0.35);
}
.zl__word {
  margin-top: 1.6rem;
  font: 650 clamp(1.8rem, 1.3rem + 1.4vw, 2.5rem) / 1.05 var(--z4-display);
  font-variation-settings: 'SHRP' 60;
  letter-spacing: -0.03em;
  color: var(--z4-text);
}
@media (max-width: 899px) {
  .zl__word {
    margin-top: 0.2rem;
  }
}
.zl__body {
  margin-top: 0.8rem;
  max-width: 34ch;
  font: 400 1.02rem/1.6 var(--z4-body);
  color: var(--z4-text-2);
}

/* The three fragments share one card shape and one height floor. */
.zl__card {
  margin-top: auto;
  min-height: 12.5rem;
  padding: 1.25rem 1.3rem;
  border-radius: 1.25rem;
  background: linear-gradient(165deg, var(--z4-panel-2), var(--z4-panel));
  border: 1px solid var(--z4-line);
  box-shadow: 0 30px 60px -36px rgba(4, 2, 16, 0.9);
}
.zl__body + .zl__card {
  margin-top: 1.75rem;
}
.zl__tag {
  font: 500 0.72rem/1.2 var(--z4-mono);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--z4-violet-2);
}
.zl__card-title {
  margin-top: 0.6rem;
  font: 600 1.15rem/1.3 var(--z4-display);
  color: var(--z4-text);
}
.zl__card-text {
  margin-top: 0.5rem;
  font: 400 0.93rem/1.55 var(--z4-body);
  color: var(--z4-text-2);
}
.zl__bar {
  margin-top: 1rem;
  height: 4px;
  border-radius: 99px;
  background: rgba(220, 214, 255, 0.14);
  overflow: hidden;
}
.zl__bar i {
  display: block;
  height: 100%;
  width: 62%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--z4-violet), var(--z4-ice));
}
.zl__card-q {
  font: 500 0.95rem/1.5 var(--z4-body);
  color: var(--z4-text);
}
.zl__opts {
  margin-top: 0.85rem;
  display: grid;
  gap: 0.45rem;
}
.zl__opts li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 2.4rem;
  padding: 0.45rem 0.8rem;
  border-radius: 0.75rem;
  border: 1px solid var(--z4-line);
  font: 500 0.9rem/1.3 var(--z4-body);
  color: var(--z4-text-2);
}
.zl__opts li.is-right {
  border-color: rgba(134, 207, 176, 0.55);
  background: rgba(134, 207, 176, 0.08);
  color: var(--z4-aurora);
}
.zl__opts svg {
  width: 1.1rem;
  height: 1.1rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.zl__card--mentor {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}
/* The mentor's mark: a monogram, not a mascot. */
.zl__avatar {
  display: grid;
  place-items: center;
  width: 2.5rem;
  height: 2.5rem;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--z4-text);
  color: var(--z4-canvas);
  font: 700 0.95rem/1 var(--z4-display);
}
.zl__bubble {
  padding: 0.8rem 0.95rem;
  border-radius: 1rem;
  border-top-left-radius: 0.3rem;
  background: rgba(111, 85, 224, 0.14);
  font: 400 0.93rem/1.55 var(--z4-body);
  color: var(--z4-text);
}
</style>
