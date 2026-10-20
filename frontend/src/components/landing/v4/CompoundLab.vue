<script setup>
/**
 * The one thing the visitor does on this page: watch compound interest work.
 *
 * Pick a monthly amount, press and hold, and years go by while you hold. Ten
 * columns fill in one year at a time; the lower, quiet part of each column is
 * what you set aside, the gold above it is what interest on interest added.
 * All columns share one scale (the top amount after ten years), so the gold
 * visibly takes over in the later years.
 *
 * Letting go early eases the years back down rather than snapping to zero;
 * reaching ten years locks the result and lights up the explanation. With
 * reduced motion the finished state is shown at once, no hold needed.
 *
 * The rate is a stated example, 10% a year compounded monthly, and the note
 * under the numbers says so in plain words.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { vIn } from './inView'

const AMOUNTS = [100000, 300000, 500000]
const YEARS = 10
const RATE = 0.1 / 12
const HOLD_MS = 3400 // ten years under the thumb
const DECAY_MS = 2200 // letting go early drifts back this fast
const MAX_SUM = grownAt(AMOUNTS[AMOUNTS.length - 1], YEARS)
const COLUMNS = Array.from({ length: YEARS }, (_, i) => i + 1)

function grownAt(monthly, years) {
  const n = years * 12
  return n <= 0 ? 0 : (monthly * (Math.pow(1 + RATE, n) - 1)) / RATE
}

const { t, locale } = useI18n()

const amount = ref(AMOUNTS[1])
const holding = ref(false)
const done = ref(false)
const shownYears = ref(0) // throttled copy for the text
const panel = ref(null)
const colEls = []
const setCol = (i) => (el) => {
  colEls[i] = el
}
const colCache = COLUMNS.map(() => ({ s: -1, g: -1 }))

let years = 0
let rafId = null
let last = 0
let lastText = 0
let reduced = false

const fmt = computed(() => new Intl.NumberFormat(locale.value === 'en' ? 'en-US' : locale.value === 'uz' ? 'uz-UZ' : 'ru-RU'))
const money = (v) => `${fmt.value.format(Math.round(v / 1000) * 1000)} ${t('v4.compound.currency')}`

const saved = computed(() => amount.value * shownYears.value * 12)
const grown = computed(() => grownAt(amount.value, shownYears.value))
const diff = computed(() => Math.max(0, grown.value - saved.value))
const holdLabel = computed(() =>
  done.value ? t('v4.compound.again') : holding.value ? t('v4.compound.holding') : t('v4.compound.hold'),
)
const yearsLabel = computed(() => (done.value ? String(YEARS) : shownYears.value.toFixed(1).replace(/\.0$/, '')))

function paint() {
  for (let i = 0; i < YEARS; i++) {
    const el = colEls[i]
    if (!el) continue
    // Column i+1 grows during year i+1 and then holds that year's totals.
    const at = years > i ? Math.min(i + 1, years) : 0
    const s = (amount.value * at * 12) / MAX_SUM
    const g = grownAt(amount.value, at) / MAX_SUM
    const c = colCache[i]
    if (Math.abs(s - c.s) > 0.001 || (s !== c.s && s === 0)) {
      el.style.setProperty('--s', s.toFixed(4))
      c.s = s
    }
    if (Math.abs(g - c.g) > 0.001 || (g !== c.g && g === 0)) {
      el.style.setProperty('--g', g.toFixed(4))
      c.g = g
    }
  }
  panel.value?.style.setProperty('--p', (years / YEARS).toFixed(4))
}

function syncText(now, force = false) {
  if (!force && now - lastText < 100) return
  lastText = now
  const rounded = Math.round(years * 10) / 10
  if (rounded !== shownYears.value) shownYears.value = rounded
}

function frame(now) {
  const dt = Math.min(64, now - (last || now))
  last = now
  if (holding.value && !done.value) {
    years = Math.min(YEARS, years + (dt / HOLD_MS) * YEARS)
    if (years >= YEARS) {
      years = YEARS
      done.value = true
    }
  } else if (!done.value) {
    years = Math.max(0, years - (dt / DECAY_MS) * YEARS)
  }
  paint()
  syncText(now, years === 0 || years === YEARS)
  const busy = (holding.value && !done.value) || (!done.value && years > 0)
  if (busy) rafId = requestAnimationFrame(frame)
  else {
    rafId = null
    last = 0
  }
}

function kick() {
  if (rafId === null) rafId = requestAnimationFrame(frame)
}

function press() {
  if (reduced) return
  if (done.value) {
    // A finished run starts over from zero on the next press.
    done.value = false
    years = 0
  }
  holding.value = true
  kick()
}

function release() {
  if (!holding.value) return
  holding.value = false
  kick()
}

function onKey(e) {
  if (e.key !== ' ' && e.key !== 'Enter') return
  e.preventDefault()
  if (e.type === 'keydown' && !e.repeat) press()
  if (e.type === 'keyup') release()
}

function pick(value) {
  amount.value = value
  paint()
}

function finish() {
  years = YEARS
  done.value = true
  shownYears.value = YEARS
  paint()
}

let mql = null
function onMotion() {
  reduced = mql.matches
  if (reduced) {
    holding.value = false
    finish()
  }
}

onMounted(() => {
  mql = window.matchMedia('(prefers-reduced-motion: reduce)')
  mql.addEventListener('change', onMotion)
  reduced = mql.matches
  if (reduced) finish()
  else paint()
})

onBeforeUnmount(() => {
  mql?.removeEventListener('change', onMotion)
  if (rafId !== null) cancelAnimationFrame(rafId)
})
</script>

<template>
  <section id="try" v-in class="z4-section zs scroll-mt-24">
    <div class="z4-wrap">
      <header class="zs__head">
        <p class="z4-kicker" data-in>{{ t('v4.compound.eyebrow') }}</p>
        <h2 class="z4-h2 zs__title" data-in style="--i: 1">{{ t('v4.compound.title') }}</h2>
        <p class="z4-lede zs__lede" data-in style="--i: 2">{{ t('v4.compound.body') }}</p>
      </header>

      <div ref="panel" class="zs__panel" data-in style="--i: 3" :class="{ 'is-holding': holding, 'is-done': done }">
        <div class="zs__stage" aria-hidden="true">
          <p class="zs__years">
            <span class="zs__years-n">{{ yearsLabel }}</span>
            <span class="zs__years-l">{{ t('v4.compound.years') }}</span>
          </p>
          <div class="zs__chart">
            <i class="zs__grid" style="--at: 0.25" />
            <i class="zs__grid" style="--at: 0.5" />
            <i class="zs__grid" style="--at: 0.75" />
            <i class="zs__grid" style="--at: 1" />
            <div v-for="(y, i) in COLUMNS" :key="y" :ref="setCol(i)" class="zs__col">
              <span class="zs__bar zs__bar--g" />
              <span class="zs__bar zs__bar--s" />
              <span class="zs__tick">{{ y }}</span>
            </div>
          </div>
        </div>

        <div class="zs__controls">
          <fieldset class="zs__amounts">
            <legend class="zs__label">{{ t('v4.compound.amountLabel') }}</legend>
            <div class="zs__chips">
              <button
                v-for="a in AMOUNTS"
                :key="a"
                type="button"
                class="zs__chip"
                :aria-pressed="amount === a"
                @click="pick(a)"
              >
                {{ money(a) }}
              </button>
            </div>
          </fieldset>

          <dl class="zs__figures" aria-live="polite">
            <div class="zs__fig">
              <dt><i class="zs__sw zs__sw--s" aria-hidden="true" />{{ t('v4.compound.saved') }}</dt>
              <dd>{{ money(saved) }}</dd>
            </div>
            <div class="zs__fig zs__fig--grown">
              <dt><i class="zs__sw zs__sw--g" aria-hidden="true" />{{ t('v4.compound.grown') }}</dt>
              <dd>{{ money(grown) }}</dd>
            </div>
            <div class="zs__fig zs__fig--diff">
              <dt>{{ t('v4.compound.diff') }}</dt>
              <dd>+{{ money(diff) }}</dd>
            </div>
          </dl>

          <button
            type="button"
            class="zs__hold"
            :aria-pressed="holding"
            @pointerdown.prevent="press"
            @pointerup="release"
            @pointercancel="release"
            @pointerleave="release"
            @keydown="onKey"
            @keyup="onKey"
            @blur="release"
            @contextmenu.prevent
          >
            <span class="zs__hold-label">{{ holdLabel }}</span>
            <span class="zs__hold-fill" aria-hidden="true"><span class="zs__hold-label">{{ holdLabel }}</span></span>
          </button>

          <p class="zs__reveal">{{ t('v4.compound.reveal') }}</p>
          <p class="zs__note">{{ t('v4.compound.note') }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zs__head {
  text-align: center;
}
.zs__title {
  margin-inline: auto;
  max-width: 18ch;
}
.zs__lede {
  margin-inline: auto;
}

.zs__panel {
  --p: 0;
  margin-top: 3.5rem;
  display: grid;
  border-radius: 1.75rem;
  background: var(--z4-panel);
  border: 1px solid var(--z4-line);
  box-shadow: 0 40px 80px -40px rgba(0, 0, 0, 0.7);
  overflow: hidden;
}
@media (min-width: 960px) {
  .zs__panel {
    grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
  }
}

/* ---- the chart ------------------------------------------------------------ */
.zs__stage {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1.75rem 1.5rem 1.5rem;
  min-height: 24rem;
}
@media (min-width: 960px) {
  .zs__stage {
    min-height: 32rem;
    padding: 2.4rem 2.4rem 2rem;
  }
}
.zs__years {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
}
.zs__years-n {
  font: 500 clamp(3rem, 2rem + 3vw, 4.5rem) / 1 var(--z4-mono);
  letter-spacing: -0.05em;
  color: var(--z4-text);
  font-variant-numeric: tabular-nums;
}
.zs__years-l {
  font: 500 0.78rem/1 var(--z4-mono);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--z4-text-3);
}
.zs__chart {
  position: relative;
  flex: 1;
  min-height: 15rem;
  display: grid;
  grid-template-columns: repeat(10, minmax(0, 1fr));
  gap: clamp(0.35rem, 1vw, 0.8rem);
  padding-bottom: 1.6rem; /* room for the year ticks */
}
.zs__grid {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(1.6rem + (100% - 1.6rem) * var(--at));
  height: 1px;
  background: var(--z4-line);
}
.zs__col {
  --s: 0;
  --g: 0;
  position: relative;
}
.zs__bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 1.6rem;
  height: calc(100% - 1.6rem);
  border-radius: 0.35rem 0.35rem 0.15rem 0.15rem;
  transform-origin: 50% 100%;
}
.zs__bar--g {
  background: linear-gradient(to top, #b08a3e, var(--z4-gold));
  transform: scaleY(var(--g));
}
.zs__bar--s {
  background: #3a3748;
  transform: scaleY(var(--s));
}
.zs__tick {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  text-align: center;
  font: 500 0.72rem/1 var(--z4-mono);
  color: var(--z4-text-3);
}

/* ---- controls -------------------------------------------------------------- */
.zs__controls {
  display: flex;
  flex-direction: column;
  gap: 1.6rem;
  padding: 2rem 1.5rem 2.2rem;
  border-top: 1px solid var(--z4-line);
}
@media (min-width: 960px) {
  .zs__controls {
    padding: 2.6rem;
    border-top: 0;
    border-left: 1px solid var(--z4-line);
  }
}
.zs__amounts {
  border: 0;
  padding: 0;
  margin: 0;
  min-width: 0;
}
.zs__label,
.zs__fig dt {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font: 500 0.74rem/1.2 var(--z4-mono);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--z4-text-3);
}
.zs__sw {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 0.2rem;
}
.zs__sw--s {
  background: #57536a;
}
.zs__sw--g {
  background: var(--z4-gold);
}
.zs__chips {
  margin-top: 0.7rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.zs__chip {
  min-height: 2.75rem;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  border: 1px solid var(--z4-edge);
  background: transparent;
  color: var(--z4-text-2);
  font: 500 0.95rem/1 var(--z4-body);
  font-variant-numeric: tabular-nums;
  cursor: pointer;
  transition: background-color 0.25s var(--z4-ease), color 0.25s var(--z4-ease), border-color 0.25s var(--z4-ease);
}
.zs__chip:hover {
  color: var(--z4-text);
  border-color: var(--z4-text-2);
}
.zs__chip[aria-pressed='true'] {
  background: var(--z4-text);
  border-color: var(--z4-text);
  color: var(--z4-canvas);
}

.zs__figures {
  display: grid;
  gap: 1rem;
  margin: 0;
}
.zs__fig {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 0.9rem;
  border-bottom: 1px solid var(--z4-line);
}
.zs__fig dd {
  margin: 0;
  font: 500 1.2rem/1.2 var(--z4-mono);
  color: var(--z4-text-2);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.zs__fig--grown dd {
  font-size: clamp(1.35rem, 1.1rem + 1vw, 1.8rem);
  color: var(--z4-text);
}
.zs__fig--diff {
  border-bottom: 0;
  padding-bottom: 0;
}
.zs__fig--diff dd {
  color: var(--z4-gold);
}

/* The hold button fills with gold as the years go by. The filled part carries
   its own ink copy of the label, clipped to the fill, so the words stay
   readable on both sides of the edge. */
.zs__hold {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 3.75rem;
  padding: 0 1.25rem;
  border-radius: 999px;
  border: 1px solid rgba(230, 190, 106, 0.55);
  background: rgba(230, 190, 106, 0.06);
  color: var(--z4-gold);
  font: 600 1.05rem/1 var(--z4-body);
  overflow: hidden;
  cursor: pointer;
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  transition: transform 0.25s var(--z4-ease);
}
.zs__hold:active {
  transform: scale(0.985);
}
.zs__hold-fill {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 0 1.25rem;
  background: var(--z4-gold);
  color: var(--z4-gold-ink);
  clip-path: inset(0 calc((1 - var(--p, 0)) * 100%) 0 0);
}
.zs__hold:focus-visible,
.zs__chip:focus-visible {
  outline: 2px solid var(--z4-gold);
  outline-offset: 3px;
}

.zs__reveal {
  font: 500 1.05rem/1.5 var(--z4-body);
  color: var(--z4-text);
  opacity: 0;
  transform: translateY(8px);
  transition: opacity 0.6s var(--z4-ease), transform 0.6s var(--z4-ease);
}
.is-done .zs__reveal {
  opacity: 1;
  transform: none;
}
.zs__note {
  font: 400 0.86rem/1.55 var(--z4-body);
  color: var(--z4-text-3);
}
</style>
