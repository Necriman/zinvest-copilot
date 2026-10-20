<script setup>
/**
 * The one thing on this page a visitor should still remember tomorrow.
 *
 * "You have $10,000. What would you do?" — three answers, none of them
 * scored. Choosing draws your own path over ten years, then fades the other
 * two in behind it, because the lesson is not which button was right: it is
 * that every answer has a shape, and you can see it.
 *
 * The numbers are plain compound growth, stated as assumptions on screen
 * rather than implied as promises — this is a teaching page, not a pitch for
 * a return. Nothing here calls the API; it is the product's philosophy in
 * miniature, so it has to be honest at the same standard the lessons are.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import Icon from '@/components/ui/Icon.vue'
import BearMascot from '@/components/mascot/BearMascot.vue'

const { locale } = useI18n()

const YEARS = 10
const START = 10000

// Rate per option. `spend` is not a rate — the money leaves.
const OPTIONS = [
  { key: 'invest', icon: 'trending', rate: 0.07, tone: 'invest' },
  { key: 'save', icon: 'wallet', rate: 0.04, tone: 'cash' },
  { key: 'spend', icon: 'coin', rate: null, tone: 'budget' },
]

const picked = ref(null)

function seriesFor(opt) {
  if (opt.rate === null) {
    // Gone in the first year, and honest about staying gone.
    return Array.from({ length: YEARS + 1 }, (_, t) => (t === 0 ? START : 0))
  }
  return Array.from({ length: YEARS + 1 }, (_, t) => START * (1 + opt.rate) ** t)
}

const CEILING = START * 1.07 ** YEARS * 1.08

// Plotted in a 100x100 box; the wrapper svg scales it.
function pathFor(opt) {
  const points = seriesFor(opt).map((v, t) => {
    const x = (t / YEARS) * 100
    const y = 100 - Math.min(100, (v / CEILING) * 100)
    return `${x.toFixed(2)},${y.toFixed(2)}`
  })
  return `M${points.join(' L')}`
}

const paths = computed(() => OPTIONS.map((o) => ({ ...o, d: pathFor(o), end: seriesFor(o)[YEARS] })))
// Where each line finishes, as a percentage down the plot, so its label can sit
// on it.
const endY = (p) => 100 - Math.min(100, (p.end / CEILING) * 100)
const others = computed(() => paths.value.filter((p) => p.key !== picked.value))
const mine = computed(() => paths.value.find((p) => p.key === picked.value) || null)

// Grouped the way the reader's own language groups digits — "19 672" in
// Russian and Uzbek, "19,672" in English. The currency stays dollars: the
// question is posed in dollars on purpose, so the figure has to match it.
const GROUPING = { ru: 'ru-RU', uz: 'ru-RU', en: 'en-US' }
const money = (n) => `$${Math.round(n).toLocaleString(GROUPING[locale.value] || 'en-US')}`

// What the choice cost against the best of the three — the number the lesson
// is actually about.
const forgone = computed(() => {
  if (!mine.value) return 0
  const best = Math.max(...paths.value.map((p) => p.end))
  return best - mine.value.end
})

function choose(key) {
  picked.value = key
}
function again() {
  picked.value = null
}
</script>

<template>
  <section id="try" class="zdd scroll-mt-28 px-6 py-20 sm:py-28">
    <div class="mx-auto max-w-6xl">
      <div class="flex items-end justify-between gap-8">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.18em] text-brand-600 dark:text-brand-400">
            {{ $t('v2.demo.eyebrow') }}
          </p>

          <!-- The question carries the section: no card around it, no subtitle
               explaining that there is about to be a question. -->
          <h2
            class="mt-4 max-w-[16ch] text-[2.1rem] font-extrabold leading-[1.05] tracking-[-0.03em] text-slate-900 sm:text-5xl dark:text-white"
          >
            {{ $t('v2.demo.title') }}
          </h2>
          <p class="mt-4 max-w-[46ch] text-base leading-[1.65] text-slate-500 dark:text-slate-400">
            {{ $t('v2.demo.lede') }}
          </p>
        </div>
        <!-- While you choose, the bear weighs the answers too, a paw for
             each; once you have chosen, the one in the result explains. -->
        <Transition name="zdd-fade">
          <div v-if="!picked" class="zdd__weigh" aria-hidden="true">
            <BearMascot mood="weigh" :decorations="false" />
          </div>
        </Transition>
      </div>

      <div class="zdd__panel mt-10">
        <!-- ASKING -->
        <div v-if="!picked" class="grid gap-3 sm:grid-cols-3">
          <button
            v-for="opt in OPTIONS"
            :key="opt.key"
            type="button"
            class="zdd__choice group"
            @click="choose(opt.key)"
          >
            <span class="zdd__choiceIcon" :data-tone="opt.tone">
              <Icon :name="opt.icon" class="h-4 w-4" />
            </span>
            <span class="zdd__choiceLabel">{{ $t(`v2.demo.${opt.key}.label`) }}</span>
            <span class="zdd__choiceHint">{{ $t(`v2.demo.${opt.key}.hint`) }}</span>
          </button>
        </div>

        <!-- ANSWERED -->
        <div v-else class="zdd__result">
          <div class="zdd__chartWrap">
            <!-- The plot is wiped in from the left rather than drawn with a
                 dash offset: the stroke is non-scaling inside a viewBox with
                 no aspect lock, so its rendered length is not the path length
                 and any dasharray guess comes out as stripes. -->
            <div class="zdd__plotBox">
              <div class="zdd__plot">
                <svg class="zdd__chart" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                  <!-- Ruled baseline, so the drop to zero reads as zero. -->
                  <line x1="0" y1="100" x2="100" y2="100" class="zdd__axis" />
                  <path v-for="p in others" :key="p.key" :d="p.d" class="zdd__ghost" :data-tone="p.tone" />
                  <path :d="mine.d" class="zdd__line" :data-tone="mine.tone" />
                </svg>
              </div>

              <!-- Labelled at the end of each line rather than in a legend:
                   three unnamed dotted lines are a decoration, and the whole
                   point of the section is that the reader can compare them. -->
              <div class="zdd__marks" aria-hidden="true">
                <span
                  v-for="p in paths"
                  :key="p.key"
                  class="zdd__mark"
                  :class="p.key === picked ? 'zdd__mark--mine' : ''"
                  :data-tone="p.tone"
                  :style="{ top: `${endY(p)}%` }"
                >
                  {{ $t(`v2.demo.${p.key}.label`) }}
                </span>
              </div>
            </div>

            <div class="zdd__scale" aria-hidden="true">
              <span>{{ $t('v2.demo.now') }}</span>
              <span>{{ $t('v2.demo.later', { years: YEARS }) }}</span>
            </div>
          </div>

          <p class="zdd__figure" :data-tone="mine.tone">
            {{ money(mine.end) }}
            <span class="zdd__figureNote">{{ $t(`v2.demo.${picked}.after`, { years: YEARS }) }}</span>
          </p>

          <!-- The bear does the explaining here, exactly as he does inside a
               lesson. The line is a nuance, never a verdict. -->
          <div class="zdd__says">
            <!-- Bust framing: at this size the full body is a white speck,
                 and it is his face that is doing the talking. -->
            <div class="zdd__bear"><BearMascot mood="talk" framing="bust" :decorations="false" /></div>
            <div class="min-w-0">
              <p class="zdd__saysText">{{ $t(`v2.demo.${picked}.says`) }}</p>
              <p v-if="forgone > 0" class="zdd__cost">
                {{ $t('v2.demo.forgone', { amount: money(forgone) }) }}
              </p>
            </div>
          </div>

          <div class="zdd__foot">
            <button type="button" class="zdd__again" @click="again">
              <Icon name="undo" class="h-3.5 w-3.5" />
              {{ $t('v2.demo.again') }}
            </button>
            <p class="zdd__assume">{{ $t('v2.demo.assumption') }}</p>
          </div>
        </div>
      </div>

      <!-- The point of the whole section, said once, plainly. The second
           clause takes its own line: it is the half that matters, and letting
           it start mid-line buried it. -->
      <p class="zdd__moral">
        {{ $t('v2.demo.moralLead') }}
        <span class="block text-slate-900 dark:text-white">{{ $t('v2.demo.moralEmph') }}</span>
      </p>
    </div>
  </section>
</template>

<style scoped>
.zdd__panel {
  border-radius: 1.5rem;
  border: 1px solid var(--color-hairline);
  background-color: color-mix(in oklab, var(--surface) 92%, transparent);
  padding: clamp(1rem, 3vw, 1.75rem);
  box-shadow: 0 24px 60px -40px rgb(15 23 42 / 0.45);
}

/* ---- asking ----
   Tiles, not cards. The panel around them is already a bordered object, and
   bordering these too gave the section the boxes-inside-boxes look the rest of
   the page is trying to get away from. They separate from the panel by tone
   and only draw an edge when the pointer is on them. */
.zdd__choice {
  display: grid;
  gap: 0.3rem;
  border-radius: 1.15rem;
  border: 1px solid transparent;
  background-color: var(--surface-2);
  padding: 1.25rem 1.25rem 1.4rem;
  text-align: left;
  transition:
    transform 200ms var(--ease-out),
    border-color 200ms ease,
    box-shadow 200ms ease;
}
.zdd__choice:hover {
  transform: translateY(-2px);
  border-color: color-mix(in oklab, var(--brand-500) 55%, transparent);
  box-shadow: 0 16px 34px -26px rgb(15 23 42 / 0.55);
}
.zdd__choice:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
}
.zdd__choiceIcon {
  display: grid;
  place-items: center;
  width: 2rem;
  aspect-ratio: 1;
  border-radius: 0.7rem;
  margin-bottom: 0.45rem;
  transition: transform 200ms var(--ease-out);
}
.zdd__choice:hover .zdd__choiceIcon {
  transform: translateY(-1px) scale(1.04);
}
.zdd__choiceIcon[data-tone='invest'] {
  background: color-mix(in oklab, var(--color-invest) 14%, transparent);
  color: var(--color-invest);
}
.zdd__choiceIcon[data-tone='cash'] {
  background: color-mix(in oklab, var(--color-cash) 14%, transparent);
  color: var(--color-cash);
}
.zdd__choiceIcon[data-tone='budget'] {
  background: color-mix(in oklab, var(--color-budget) 16%, transparent);
  color: var(--color-budget);
}
.zdd__choiceLabel {
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--color-ink);
}
.zdd__choiceHint {
  font-size: 0.8rem;
  line-height: 1.5;
  color: var(--color-ink-muted);
}

/* ---- answered ---- */
.zdd__result {
  animation: zdd-in 420ms var(--ease-out) both;
}
@keyframes zdd-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
}

.zdd__chartWrap {
  position: relative;
}
.zdd__plotBox {
  position: relative;
}

/* The padding gives the stroke caps room, so the finished wipe (inset 0) does
   not shave the ends of the lines. */
.zdd__plot {
  padding: 3px;
  margin: -3px;
  animation: zdd-wipe 900ms var(--ease-out) 120ms both;
}
@keyframes zdd-wipe {
  from {
    clip-path: inset(0 100% 0 0);
  }
  to {
    clip-path: inset(0 0 0 0);
  }
}
.zdd__chart {
  display: block;
  width: 100%;
  height: clamp(9rem, 26vw, 14rem);
  overflow: visible;
}
.zdd__axis {
  stroke: var(--color-hairline);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
}
.zdd__line,
.zdd__ghost {
  fill: none;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}
.zdd__line[data-tone='invest'],
.zdd__ghost[data-tone='invest'] {
  stroke: var(--color-invest);
}
.zdd__line[data-tone='cash'],
.zdd__ghost[data-tone='cash'] {
  stroke: var(--color-cash);
}
.zdd__line[data-tone='budget'],
.zdd__ghost[data-tone='budget'] {
  stroke: var(--color-budget);
}
/* Yours arrives with the wipe; the alternatives follow at a whisper, so the
   comparison is offered rather than argued. */
.zdd__ghost {
  opacity: 0;
  stroke-width: 1.5;
  stroke-dasharray: 3 4;
  animation: zdd-ghost 500ms ease 900ms forwards;
}
@keyframes zdd-ghost {
  to {
    opacity: 0.4;
  }
}

/* End labels. They arrive with the ghosts, once the reader's own line has
   finished drawing — naming the alternatives before the answer would put the
   comparison ahead of the choice. */
.zdd__marks {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0;
  animation: zdd-marks 500ms ease 900ms forwards;
}
@keyframes zdd-marks {
  to {
    opacity: 1;
  }
}
.zdd__mark {
  position: absolute;
  right: 0;
  transform: translateY(-145%);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  white-space: nowrap;
  opacity: 0.55;
}
.zdd__mark--mine {
  opacity: 1;
  font-size: 0.78rem;
}
.zdd__mark[data-tone='invest'] {
  color: var(--color-invest);
}
.zdd__mark[data-tone='cash'] {
  color: var(--color-cash);
}
.zdd__mark[data-tone='budget'] {
  color: var(--color-budget);
}

.zdd__scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.6rem;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-ink-faint);
}

.zdd__figure {
  margin-top: 1.4rem;
  font-size: clamp(2rem, 6vw, 2.9rem);
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1;
}
.zdd__figure[data-tone='invest'] {
  color: var(--color-invest);
}
.zdd__figure[data-tone='cash'] {
  color: var(--color-cash);
}
.zdd__figure[data-tone='budget'] {
  color: var(--color-budget);
}
.zdd__figureNote {
  display: block;
  margin-top: 0.4rem;
  font-size: 0.85rem;
  font-weight: 500;
  letter-spacing: 0;
  color: var(--color-ink-muted);
}

.zdd__says {
  display: flex;
  align-items: flex-start;
  gap: 0.9rem;
  margin-top: 1.4rem;
  padding-top: 1.4rem;
  border-top: 1px solid var(--color-hairline);
}
.zdd__bear {
  width: 4rem;
  height: 4rem;
  flex-shrink: 0;
  margin-top: -0.2rem;
}
.zdd__weigh {
  display: none;
  width: 9rem;
  height: 13.5rem;
  flex-shrink: 0;
  margin-bottom: -0.5rem;
}
@media (min-width: 640px) {
  .zdd__weigh {
    display: block;
  }
}
.zdd-fade-enter-active,
.zdd-fade-leave-active {
  transition: opacity 0.25s ease;
}
.zdd-fade-enter-from,
.zdd-fade-leave-to {
  opacity: 0;
}
.zdd__saysText {
  font-size: 0.95rem;
  line-height: 1.65;
  color: var(--color-ink);
}
.zdd__cost {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: var(--color-ink-muted);
}

.zdd__foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 1.4rem;
}
.zdd__again {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border-radius: 999px;
  border: 1px solid var(--color-hairline);
  padding: 0.5rem 0.95rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-ink-muted);
  transition:
    color 200ms ease,
    border-color 200ms ease;
}
.zdd__again:hover {
  color: var(--color-ink);
  border-color: color-mix(in oklab, var(--text) 25%, transparent);
}
.zdd__again:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
}
.zdd__assume {
  font-size: 0.72rem;
  color: var(--color-ink-faint);
}

.zdd__moral {
  margin-top: 2.25rem;
  max-width: 38ch;
  font-size: clamp(1.05rem, 2.4vw, 1.3rem);
  line-height: 1.55;
  font-weight: 600;
  color: var(--color-ink-muted);
}

@media (prefers-reduced-motion: reduce) {
  .zdd__result,
  .zdd__plot,
  .zdd__ghost,
  .zdd__marks {
    animation: none;
  }
  .zdd__plot {
    clip-path: none;
  }
  .zdd__ghost {
    opacity: 0.4;
  }
  .zdd__marks {
    opacity: 1;
  }
  .zdd__choice:hover {
    transform: none;
  }
}
</style>
