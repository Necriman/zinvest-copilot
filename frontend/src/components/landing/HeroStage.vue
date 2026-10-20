<script setup>
/**
 * The hero's right-hand side: the bear standing inside a small piece of the
 * product rather than on an empty panel.
 *
 * Three cards, no more — today's lesson, the streak, the practice portfolio.
 * Between them they say what the page claims in words: the plan is yours, you
 * practise rather than read, and the progress is counted. They drift a few
 * pixels behind the pointer so the group reads as one scene with depth, and
 * they sit still entirely when the visitor asks for less motion.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

import BearMascot from '@/components/mascot/BearMascot.vue'
import Icon from '@/components/ui/Icon.vue'

const stage = ref(null)
// Pointer offset, -1..1 on each axis. Each card multiplies it by its own depth.
const px = ref(0)
const py = ref(0)

const fine = typeof window !== 'undefined' && window.matchMedia?.('(pointer: fine)').matches
const still =
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

let queued = false
let last = null

function onMove(event) {
  last = event
  if (queued) return
  queued = true
  requestAnimationFrame(() => {
    queued = false
    if (!stage.value || !last) return
    const box = stage.value.getBoundingClientRect()
    const reach = Math.max(420, window.innerWidth / 2)
    px.value = Math.max(-1, Math.min(1, (last.clientX - (box.left + box.width / 2)) / reach))
    py.value = Math.max(-1, Math.min(1, (last.clientY - (box.top + box.height / 2)) / reach))
  })
}

function rest() {
  px.value = 0
  py.value = 0
}

// `depth` is the travel in pixels at the pointer's furthest reach.
function drift(depth) {
  if (still || !fine) return null
  return { transform: `translate3d(${(px.value * depth).toFixed(2)}px, ${(py.value * depth).toFixed(2)}px, 0)` }
}

onMounted(() => {
  if (still || !fine) return
  window.addEventListener('pointermove', onMove, { passive: true })
  document.documentElement.addEventListener('pointerleave', rest)
})
onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onMove)
  document.documentElement.removeEventListener('pointerleave', rest)
})
</script>

<template>
  <div ref="stage" class="hs">
    <!-- Light, not decoration: the bear stands in it, so the column stops
         reading as a cut-out on a flat panel. -->
    <div class="hs__glow" aria-hidden="true" />

    <div class="hs__bear" :style="drift(4)">
      <!-- Presents the headline beside him rather than waving: every place on
           the site has its own gesture (src/mascot/places.js). -->
      <BearMascot mood="present" interactive />
    </div>

    <!-- Today's lesson: the plan is already made, and it is short. -->
    <article class="hs__card hs__card--lesson" :style="drift(-12)">
      <p class="hs__label">
        <Icon name="book" class="h-3.5 w-3.5 text-brand-600 dark:text-brand-400" />
        {{ $t('landing.stage.lesson.label') }}
      </p>
      <p class="hs__title">{{ $t('landing.stage.lesson.title') }}</p>
      <p class="hs__meta">{{ $t('landing.stage.lesson.meta') }}</p>
    </article>

    <!-- The streak: progress is counted, quietly. -->
    <article class="hs__card hs__card--streak" :style="drift(-7)">
      <span class="hs__flame"><Icon name="flame" class="h-4 w-4" /></span>
      <span>
        <b class="hs__streakValue">{{ $t('landing.stage.streak.value') }}</b>
        <span class="hs__meta">{{ $t('landing.stage.streak.label') }}</span>
      </span>
    </article>

    <!-- The practice portfolio: you do the thing, you don't only read about it. -->
    <article class="hs__card hs__card--portfolio" :style="drift(-16)">
      <p class="hs__label">{{ $t('landing.stage.portfolio.label') }}</p>
      <p class="hs__row">
        <b class="hs__gain">{{ $t('landing.stage.portfolio.value') }}</b>
        <svg class="hs__spark" viewBox="0 0 64 22" fill="none" aria-hidden="true">
          <path
            d="M1 18 L11 14 L21 16 L31 9 L41 11 L52 5 L63 2"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </p>
      <p class="hs__meta">{{ $t('landing.stage.portfolio.meta') }}</p>
    </article>
  </div>
</template>

<style scoped>
.hs {
  position: relative;
  width: 100%;
  height: 100%;
  container-type: inline-size;
}

/* A single soft light behind the bear. Kept under 20% so it reads as air in
   the room rather than a glow effect. */
.hs__glow {
  position: absolute;
  inset: -12% -6% 6%;
  pointer-events: none;
  background: radial-gradient(
    58% 48% at 50% 44%,
    color-mix(in oklab, var(--brand-500) 16%, transparent),
    transparent 70%
  );
  filter: blur(6px);
  opacity: 0.55;
}
.dark .hs__glow {
  opacity: 0.85;
}

.hs__bear {
  position: absolute;
  inset: 7% 5% 0;
  transition: transform 500ms cubic-bezier(0.22, 0.61, 0.36, 1);
  will-change: transform;
}

/* Cards. Sized against the stage so they shrink with it instead of crowding
   the bear on a narrow column. */
.hs__card {
  position: absolute;
  z-index: 2;
  border-radius: 1rem;
  border: 1px solid var(--color-hairline);
  background-color: color-mix(in oklab, var(--surface) 88%, transparent);
  box-shadow: 0 14px 34px -22px rgb(15 23 42 / 0.5);
  backdrop-filter: blur(10px);
  padding: clamp(0.5rem, 2.4cqw, 0.85rem) clamp(0.65rem, 2.9cqw, 1rem);
  transition:
    transform 500ms cubic-bezier(0.22, 0.61, 0.36, 1),
    box-shadow 250ms ease,
    border-color 250ms ease;
  will-change: transform;
}
.hs:hover .hs__card {
  box-shadow: 0 18px 40px -20px rgb(15 23 42 / 0.55);
}

.hs__label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: clamp(0.6rem, 2.3cqw, 0.7rem);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
}
.hs__title {
  margin-top: 0.2rem;
  font-size: clamp(0.8rem, 3.1cqw, 0.95rem);
  font-weight: 700;
  color: var(--color-ink);
}
.hs__meta {
  font-size: clamp(0.62rem, 2.4cqw, 0.75rem);
  color: var(--color-ink-muted);
}

/* Offset from the portfolio card rather than level with it, so the two read as
   two moments in a scene and not as a header row. */
.hs__card--lesson {
  left: 0;
  top: 13%;
  width: clamp(8.5rem, 42cqw, 11.5rem);
}

.hs__card--streak {
  left: 4%;
  bottom: 16%;
  display: flex;
  align-items: center;
  gap: 0.55rem;
}
.hs__flame {
  display: grid;
  place-items: center;
  width: clamp(1.5rem, 6cqw, 1.9rem);
  aspect-ratio: 1;
  border-radius: 999px;
  background: color-mix(in oklab, var(--color-budget) 16%, transparent);
  color: var(--color-budget);
}
.hs__streakValue {
  display: block;
  font-size: clamp(0.85rem, 3.3cqw, 1rem);
  font-weight: 800;
  line-height: 1.1;
  color: var(--color-ink);
}

/* Up at the top right on purpose. The bear model carries a growth arrow above
   his head, and floating in empty space it read as a leftover sticker; from
   here the arrow points straight into the gain, so the two become one idea
   instead of two unrelated yellow-and-green things. The three cards then sit
   at the corners of a triangle around him rather than down one side. */
.hs__card--portfolio {
  right: 0;
  top: 4%;
  width: clamp(7.5rem, 36cqw, 10rem);
}
.hs__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 0.15rem;
}
.hs__gain {
  font-size: clamp(0.95rem, 3.8cqw, 1.2rem);
  font-weight: 800;
  color: var(--color-cash);
}
.hs__spark {
  width: clamp(2.5rem, 13cqw, 3.6rem);
  color: color-mix(in oklab, var(--color-cash) 70%, transparent);
}

/* Tablet: two cards, not three, and they move to opposite corners so the
   scene stays balanced instead of stacking both on one side.

   The threshold is 26rem rather than 30rem because the portfolio card is what
   the bear's arrow points at: at 1024 the column is 28rem and both top cards
   still fit side by side, so dropping it there left the arrow aimed at
   nothing — which is exactly how it used to look wrong. */
@container (max-width: 26rem) {
  .hs__card--portfolio {
    display: none;
  }
  .hs__card--lesson {
    top: 6%;
  }
  .hs__card--streak {
    left: auto;
    right: 2%;
    bottom: 20%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hs__bear,
  .hs__card {
    transition: none;
  }
}
</style>
