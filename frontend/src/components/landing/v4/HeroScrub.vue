<script setup>
/**
 * The coin hero.
 *
 * One generated shot (the camera glides along a row of gold coin stacks on a
 * graphite table, each stack taller than the last, and settles on the
 * tallest) is scrubbed by scroll: down plays it forward, up plays it back.
 * Four caption bands live in the dark space on the left, above the coins.
 * The page settles on the resting frame and the settle band carries the one
 * call to action.
 *
 * The engineering is the 10k-websites scrub standard, all of it:
 *  - the video is fetched whole as a Blob (hosts without Range support would
 *    otherwise clamp every seek to 0), streamed behind an honest ring;
 *  - the displayed time eases toward the scroll target in a rAF loop that
 *    rests when converged or off screen, normalised to 60fps so every refresh
 *    rate feels the same;
 *  - seeks are gated: never a second one while one is in flight;
 *  - the DOM is written only when a value actually changes;
 *  - five static-hero gates, identical here and in the CSS, decided live;
 *  - the page is complete over the poster if the video never arrives.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/store/auth'
import { dropIn, ordered } from './split'

const VIDEO_URL = '/landing/v4/hero-scrub.mp4'
const VIDEO_BYTES = 6960156 // fallback when Content-Length is missing
const POSTER_URL = '/landing/v4/hero-poster.jpg'
// The video finishes here; the settle band then holds on the resting frame.
const VIDEO_END = 0.84

// Character for character the same as the @media gate in the style block.
const GATES = [
  '(max-width: 720px)',
  '(orientation: portrait) and (max-width: 1024px)',
  '(orientation: portrait) and (pointer: coarse)',
  '(orientation: landscape) and (pointer: coarse) and (max-height: 560px)',
  '(prefers-reduced-motion: reduce)',
]

// Scroll-progress bands, starting points validated with the flick test.
const BANDS = [
  { a: 0, b: 0.2 },
  { a: 0.25, b: 0.46 },
  { a: 0.51, b: 0.72 },
  { a: 0.78, b: 1 },
]

const { t } = useI18n()
const auth = useAuthStore()
const startTo = computed(() => (auth.isAuthenticated ? { name: 'dashboard' } : { name: 'register' }))

const b1Words = computed(() => dropIn(t('v4.hero.b1'), 7))
const b2Words = computed(() => ordered(t('v4.hero.b2'), 0.45, 3))
const b3Words = computed(() => ordered(t('v4.hero.b3'), 0.5, 5))
const b4Words = computed(() => ordered(t('v4.hero.settleTitle'), 0.5, 9))

const scrubEl = ref(null)
const posterEl = ref(null)
const videoEl = ref(null)
const bandEls = []
const setBand = (i) => (el) => {
  bandEls[i] = el
}

const ready = ref(false)
const failed = ref(false)
const loading = ref(false)
const ringOffset = ref(57)
const cueGone = ref(false)

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))
const smoothstep = (p, e0, e1) => {
  const x = clamp((p - e0) / (e1 - e0), 0, 1)
  return x * x * (3 - 2 * x)
}

// --- scrub state -------------------------------------------------------------
let scrubOn = false
let heroInited = false
let heroOnScreen = true
let target = 0
let shown = 0
let rafId = null
let lastTick = 0
let loadK = 0
let loadStart = 0
let seekBusy = false
let pendingTime = null
let abort = null
let posterTimer = null
let objectUrl = null
let mqls = []
let io = null
const cache = BANDS.map(() => ({ op: -1, k: -1, on: null }))

function heroProgress() {
  const el = scrubEl.value
  if (!el) return 0
  const range = el.offsetHeight - window.innerHeight
  if (range <= 0) return 0
  return clamp(-el.getBoundingClientRect().top / range, 0, 1)
}

function videoTime(p) {
  const v = videoEl.value
  if (!v || !v.duration) return 0
  return Math.min(1, p / VIDEO_END) * Math.max(0, v.duration - 0.04)
}

function requestSeek(time) {
  const v = videoEl.value
  if (!v || !v.duration || !ready.value) return
  if (seekBusy) {
    pendingTime = time
    return
  }
  if (Math.abs(v.currentTime - time) < 0.001) return
  seekBusy = true
  v.currentTime = time
}

function onSeeked() {
  seekBusy = false
  if (pendingTime !== null) {
    const time = pendingTime
    pendingTime = null
    requestSeek(time)
  }
}

function onVideoError() {
  // The deadlock escape: a failed seek never fires `seeked`.
  seekBusy = false
  pendingTime = null
  if (!ready.value) failVideo()
}

function updateCaptions(p) {
  for (let i = 0; i < BANDS.length; i++) {
    const el = bandEls[i]
    if (!el) continue
    const { a, b } = BANDS[i]
    const f = Math.min(0.04, (b - a) / 3)
    const first = i === 0
    const last = i === BANDS.length - 1
    const op = (first ? 1 : smoothstep(p, a, a + f)) * (last ? 1 : 1 - smoothstep(p, b - f, b))
    const ramp = Number(el.dataset.ramp) || 0.04
    let k = clamp((p - a) / ramp, 0, 1)
    if (first) k = Math.max(k, loadK)

    const c = cache[i]
    if (Math.abs(op - c.op) > 0.004 || (op !== c.op && (op === 0 || op === 1))) {
      el.style.opacity = op.toFixed(3)
      c.op = op
      const on = op > 0.5
      if (on !== c.on) {
        c.on = on
        el.classList.toggle('is-on', on)
      }
    }
    if (Math.abs(k - c.k) > 0.008 || (k !== c.k && (k === 0 || k === 1))) {
      el.style.setProperty('--k', k.toFixed(3))
      c.k = k
    }
  }
}

const easeOut = (x) => 1 - Math.pow(1 - x, 3)

function tick(now) {
  const dt = Math.min(100, now - (lastTick || now))
  lastTick = now
  shown += (target - shown) * (1 - Math.pow(1 - 0.16, dt / 16.667))
  const moving = Math.abs(target - shown) >= 0.0005
  if (!moving) shown = target
  if (loadK < 1) loadK = easeOut(clamp((now - loadStart) / 1400, 0, 1))

  requestSeek(videoTime(shown))
  updateCaptions(shown)

  if ((moving || loadK < 1) && scrubOn && heroOnScreen) {
    rafId = requestAnimationFrame(tick)
  } else {
    rafId = null
    lastTick = 0
  }
}

function kick() {
  if (rafId === null && scrubOn && heroOnScreen) rafId = requestAnimationFrame(tick)
}

function onScroll() {
  target = heroProgress()
  const gone = target > 0.03
  if (gone !== cueGone.value) cueGone.value = gone
  kick()
}

// --- loading -----------------------------------------------------------------
function initHeroOnce() {
  if (heroInited) return
  heroInited = true
  // The poster wins the bandwidth race: paint it first, fetch the video after.
  if (posterEl.value) posterEl.value.style.backgroundImage = `url('${POSTER_URL}')`
  const img = new Image()
  img.onload = startBlobFetch
  img.onerror = startBlobFetch
  img.src = POSTER_URL
  posterTimer = setTimeout(startBlobFetch, 4000)
}

let fetchStarted = false
function startBlobFetch() {
  if (fetchStarted) return
  fetchStarted = true
  clearTimeout(posterTimer)
  loadHeroBlob().catch(failVideo)
}

async function loadHeroBlob() {
  loading.value = true
  abort = new AbortController()
  let watchdog = setTimeout(() => abort.abort(), 20000)
  const res = await fetch(VIDEO_URL, { priority: 'low', signal: abort.signal })
  if (!res.ok || !res.body) throw new Error(`video ${res.status}`)
  const total = Number(res.headers.get('Content-Length')) || VIDEO_BYTES
  const reader = res.body.getReader()
  const chunks = []
  let got = 0
  let lastRing = 0
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    clearTimeout(watchdog)
    watchdog = setTimeout(() => abort.abort(), 20000)
    chunks.push(value)
    got += value.length
    const frac = Math.min(1, got / total)
    const now = performance.now()
    if (now - lastRing > 100 || frac === 1) {
      lastRing = now
      ringOffset.value = Math.round(57 * (1 - frac))
    }
  }
  clearTimeout(watchdog)
  ringOffset.value = 0
  const v = videoEl.value
  if (!v) return
  objectUrl = URL.createObjectURL(new Blob(chunks, { type: 'video/mp4' }))
  v.addEventListener(
    'canplay',
    () => {
      ready.value = true
      loading.value = false
      requestSeek(videoTime(heroProgress()))
    },
    { once: true },
  )
  v.preload = 'auto'
  v.src = objectUrl
  v.load()
}

function failVideo() {
  loading.value = false
  failed.value = true
}

// --- the live gate -----------------------------------------------------------
function enableScrub() {
  if (scrubOn) return
  scrubOn = true
  initHeroOnce()
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onScroll)
  cache.forEach((c) => {
    c.op = -1
    c.k = -1
    c.on = null
  })
  loadStart = performance.now()
  target = heroProgress()
  shown = target
  updateCaptions(shown)
  onScroll()
}

function disableScrub() {
  if (!scrubOn) return
  scrubOn = false
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', onScroll)
  if (rafId !== null) cancelAnimationFrame(rafId)
  rafId = null
  lastTick = 0
}

function applyHeroMode() {
  if (mqls.some((m) => m.matches)) disableScrub()
  else enableScrub()
}

// A keyboard user tabbing into the settle band's buttons while the band is
// still hidden gets carried to the end of the journey, where it is visible.
function onSettleFocus() {
  if (cache[BANDS.length - 1].op > 0.9 || !scrubEl.value) return
  const el = scrubEl.value
  const end = el.getBoundingClientRect().top + window.scrollY + el.offsetHeight - window.innerHeight
  window.scrollTo({ top: end, behavior: 'instant' })
}

onMounted(() => {
  const v = videoEl.value
  v?.addEventListener('seeked', onSeeked)
  v?.addEventListener('error', onVideoError)
  if (typeof IntersectionObserver !== 'undefined' && scrubEl.value) {
    io = new IntersectionObserver(([entry]) => {
      heroOnScreen = entry.isIntersecting
      if (heroOnScreen) onScroll()
    })
    io.observe(scrubEl.value)
  }
  // Keep the query lists referenced so their listeners survive.
  mqls = GATES.map((q) => window.matchMedia(q))
  mqls.forEach((m) => m.addEventListener('change', applyHeroMode))
  applyHeroMode()
})

onBeforeUnmount(() => {
  disableScrub()
  mqls.forEach((m) => m.removeEventListener('change', applyHeroMode))
  io?.disconnect()
  abort?.abort()
  clearTimeout(posterTimer)
  const v = videoEl.value
  v?.removeEventListener('seeked', onSeeked)
  v?.removeEventListener('error', onVideoError)
  if (objectUrl) URL.revokeObjectURL(objectUrl)
})
</script>

<template>
  <section class="zh">
    <!-- The journey: laptops and desktops -->
    <div ref="scrubEl" class="zh__scrub">
      <div class="zh__stage" :class="{ 'is-ready': ready, 'is-failed': failed }">
        <div ref="posterEl" class="zh__poster" aria-hidden="true" />
        <video
          ref="videoEl"
          class="zh__video"
          muted
          playsinline
          preload="none"
          disablepictureinpicture
          aria-hidden="true"
          tabindex="-1"
        />
        <div class="zh__scrim" aria-hidden="true" />

        <div class="zh__col">
          <div :ref="setBand(0)" class="zh__band zh__band--b1">
            <p class="zh__eyebrow">{{ t('v4.hero.eyebrow') }}</p>
            <h1 class="zh__h1">
              <span class="sr-only">{{ t('v4.hero.b1') }}</span>
              <span aria-hidden="true">
                <template v-for="(w, i) in b1Words" :key="i">
                  <span class="w"><span v-for="(ch, j) in w.chars" :key="j" class="c" :style="ch.style">{{ ch.c }}</span></span>
                  {{ ' ' }}
                </template>
              </span>
            </h1>
            <p class="zh__sub">{{ t('v4.hero.b1sub') }}</p>
          </div>

          <div :ref="setBand(1)" class="zh__band zh__band--b2" data-ramp="0.05">
            <p class="zh__h2">
              <span class="sr-only">{{ t('v4.hero.b2') }}</span>
              <span aria-hidden="true">
                <template v-for="(w, i) in b2Words" :key="i">
                  <span class="w" :style="w.style">{{ w.text }}</span>
                  {{ ' ' }}
                </template>
              </span>
            </p>
            <p class="zh__sub">{{ t('v4.hero.b2sub') }}</p>
          </div>

          <div :ref="setBand(2)" class="zh__band zh__band--b3" data-ramp="0.05">
            <p class="zh__h2">
              <span class="sr-only">{{ t('v4.hero.b3') }}</span>
              <span aria-hidden="true">
                <template v-for="(w, i) in b3Words" :key="i">
                  <span class="w" :style="w.style">{{ w.text }}</span>
                  {{ ' ' }}
                </template>
              </span>
            </p>
            <p class="zh__sub">{{ t('v4.hero.b3sub') }}</p>
          </div>

          <div :ref="setBand(3)" class="zh__band zh__band--b4" data-ramp="0.06" @focusin="onSettleFocus">
            <h2 class="zh__settle">
              <span class="sr-only">{{ t('v4.hero.settleTitle') }}</span>
              <span aria-hidden="true">
                <template v-for="(w, i) in b4Words" :key="i">
                  <span class="w" :style="w.style">{{ w.text }}</span>
                  {{ ' ' }}
                </template>
              </span>
            </h2>
            <p class="zh__body">{{ t('v4.hero.settleBody') }}</p>
            <div class="zh__ctas">
              <RouterLink :to="startTo" class="z4-btn">{{ t('v4.hero.start') }}</RouterLink>
              <RouterLink v-if="!auth.isAuthenticated" :to="{ name: 'login' }" class="z4-btn z4-btn--ghost">
                {{ t('v4.hero.login') }}
              </RouterLink>
            </div>
          </div>
        </div>

        <div class="zh__cue" :class="{ 'is-gone': cueGone }" aria-hidden="true">
          <svg v-if="loading" class="zh__ring" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="9" class="zh__ring-track" />
            <circle cx="12" cy="12" r="9" class="zh__ring-fill" :style="{ strokeDashoffset: ringOffset }" />
          </svg>
          <svg v-else class="zh__chev" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" /></svg>
          <span>{{ t('v4.hero.scroll') }}</span>
        </div>
      </div>
    </div>

    <!-- The composed still: phones, portrait tablets, reduced motion -->
    <div class="zh__static">
      <div class="zh__static-bg" aria-hidden="true" />
      <div class="zh__static-copy">
        <p class="zh__eyebrow">{{ t('v4.hero.eyebrow') }}</p>
        <h1 class="zh__static-h1">{{ t('v4.hero.b1') }}</h1>
        <p class="zh__sub">{{ t('v4.hero.b1sub') }}</p>
        <p class="zh__body">{{ t('v4.hero.settleBody') }}</p>
        <div class="zh__ctas">
          <RouterLink :to="startTo" class="z4-btn">{{ t('v4.hero.start') }}</RouterLink>
          <RouterLink v-if="!auth.isAuthenticated" :to="{ name: 'login' }" class="z4-btn z4-btn--ghost">
            {{ t('v4.hero.login') }}
          </RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zh {
  position: relative;
  background: var(--z4-canvas);
}

/* ---- the journey ---------------------------------------------------------- */
.zh__scrub {
  position: relative;
  height: 600vh;
}
.zh__stage {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
  background: var(--z4-canvas);
}
.zh__poster,
.zh__video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.zh__poster {
  background: var(--z4-canvas) center / cover no-repeat;
}
.zh__video {
  object-fit: cover;
  opacity: 0;
  transform: translateZ(0);
  transition: opacity 0.9s var(--z4-ease);
}
.is-ready .zh__video {
  opacity: 1;
}
.is-failed .zh__video {
  display: none;
}
/* Always-on base: the navbar band on top, a soft vignette, and a fade into
   the page at the bottom so the journey hands over without a seam. */
.zh__scrim {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(to top, var(--z4-canvas) 0%, rgba(15, 14, 20, 0) 16%),
    linear-gradient(to bottom, rgba(10, 9, 14, 0.6) 0%, rgba(10, 9, 14, 0) 20%),
    /* the caption side stays dark; the coins on the right keep their light */
    linear-gradient(90deg, rgba(10, 9, 14, 0.7) 0%, rgba(10, 9, 14, 0.5) 28%, rgba(10, 9, 14, 0.12) 50%, rgba(10, 9, 14, 0) 60%),
    radial-gradient(ellipse 120% 90% at 55% 45%, rgba(10, 9, 14, 0) 40%, rgba(10, 9, 14, 0.5) 100%);
}

.zh__col {
  position: absolute;
  top: 0;
  bottom: 0;
  left: max(1.5rem, calc((100vw - 76rem) / 2 + 2rem));
  width: min(40rem, 52vw);
}
.zh__band {
  position: absolute;
  left: 0;
  right: 0;
  top: 21vh;
  isolation: isolate;
  opacity: 0;
  pointer-events: none;
  text-shadow: var(--z4-tshadow);
}
.zh__band.is-on {
  pointer-events: auto;
}
.zh__band--b1 {
  opacity: 1;
}
.zh__band--b4 {
  top: 17vh;
}
/* The band's own scrim: deepens while its words are on, and nowhere else. */
.zh__band::before {
  content: '';
  position: absolute;
  inset: -34% -30% -34% -45%;
  z-index: -1;
  pointer-events: none;
  opacity: calc(0.25 + 0.75 * var(--k, 1));
  background: radial-gradient(
    ellipse 62% 58% at 42% 50%,
    rgba(10, 9, 14, var(--scrim, 0.62)) 0%,
    rgba(10, 9, 14, calc(var(--scrim, 0.62) * 0.66)) 46%,
    rgba(10, 9, 14, 0) 76%
  );
}
.zh__band--b1 {
  --scrim: 0.66;
}
.zh__band--b4 {
  --scrim: 0.72;
}

.zh__eyebrow {
  font: 500 0.8rem/1.2 var(--z4-mono);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--z4-violet-2);
}
.zh__h1,
.zh__static-h1 {
  margin-top: 1.1rem;
  font: 700 clamp(2.8rem, 1.5rem + 3.6vw, 5.4rem) / 0.98 var(--z4-display);
  font-variation-settings: 'SHRP' 60;
  letter-spacing: -0.035em;
  color: var(--z4-text);
  text-wrap: balance;
}
.zh__h2 {
  font: 650 clamp(2.6rem, 1.5rem + 3.2vw, 4.9rem) / 1 var(--z4-display);
  font-variation-settings: 'SHRP' 60;
  letter-spacing: -0.035em;
  color: var(--z4-text);
  text-wrap: balance;
}
.zh__settle {
  font: 650 clamp(2.2rem, 1.3rem + 2.5vw, 3.9rem) / 1.02 var(--z4-display);
  font-variation-settings: 'SHRP' 60;
  letter-spacing: -0.03em;
  color: var(--z4-text);
  text-wrap: balance;
}
.zh__sub {
  margin-top: 1.25rem;
  max-width: 30ch;
  font: 500 clamp(1.1rem, 0.95rem + 0.5vw, 1.35rem) / 1.45 var(--z4-body);
  color: #e4e1d8; /* brighter than the page's secondary: this sits on footage */
}
.zh__body {
  margin-top: 1.25rem;
  max-width: 44ch;
  font: 400 1.1rem/1.6 var(--z4-body);
  color: #e4e1d8;
}
.zh__ctas {
  margin-top: 2rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  text-shadow: none;
}

/* Entrances. Every one is transform and opacity only, scrubbed off --k and
   fully reversible. The words are inline-blocks so they can move. */
.w,
.c {
  display: inline-block;
}
/* Band 1, drop in: the letters settle one after another, like coins onto a stack. */
.zh__band--b1 .c {
  --kc: clamp(0, (var(--k, 0) - var(--th, 0)) * 2.6, 1);
  opacity: var(--kc);
  transform: translate(calc((1 - var(--kc)) * var(--jx, 0px)), calc((1 - var(--kc)) * var(--jy, 0px)))
    rotate(calc((1 - var(--kc)) * var(--jr, 0deg)));
}
.zh__band--b1 .zh__sub,
.zh__band--b1 .zh__eyebrow {
  opacity: clamp(0, (var(--k, 0) - 0.45) * 3, 1);
}
/* Band 2, drift down: the words come down into place. */
.zh__band--b2 .w {
  --kc: clamp(0, (var(--k, 0) - var(--th, 0)) * 2.8, 1);
  opacity: var(--kc);
  transform: translateY(calc((1 - var(--kc)) * -30px));
}
/* Band 3, grow: the words rise to full size, as the stacks do. */
.zh__band--b3 .w {
  --kc: clamp(0, (var(--k, 0) - var(--th, 0)) * 2.6, 1);
  opacity: var(--kc);
  transform: scale(calc(0.7 + 0.3 * var(--kc)));
  transform-origin: 0 80%;
}
.zh__band--b2 .zh__sub,
.zh__band--b3 .zh__sub {
  opacity: clamp(0, (var(--k, 0) - 0.55) * 3, 1);
  transform: translateY(calc((1 - clamp(0, (var(--k, 0) - 0.55) * 3, 1)) * 10px));
}
/* Band 4, the settle: words rise, then the body, then the buttons. */
.zh__band--b4 .w {
  --kc: clamp(0, (var(--k, 0) - var(--th, 0)) * 2.4, 1);
  opacity: var(--kc);
  transform: translateY(calc((1 - var(--kc)) * 0.55em));
}
.zh__band--b4 .zh__body {
  --ks: clamp(0, (var(--k, 0) - 0.62) * 4, 1);
  opacity: var(--ks);
  transform: translateY(calc((1 - var(--ks)) * 12px));
}
.zh__band--b4 .zh__ctas {
  --kb: clamp(0, (var(--k, 0) - 0.78) * 5, 1);
  opacity: var(--kb);
  transform: translateY(calc((1 - var(--kb)) * 12px));
}

/* The loading ring that turns into a scroll cue. */
.zh__cue {
  position: absolute;
  left: 50%;
  bottom: 1.75rem;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0.95rem 0.5rem 0.6rem;
  border-radius: 999px;
  background: rgba(10, 9, 14, 0.5);
  border: 1px solid rgba(220, 214, 255, 0.22);
  backdrop-filter: blur(10px);
  color: var(--z4-text-2);
  font: 500 0.74rem/1 var(--z4-mono);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  transform: translateX(-50%);
  transition: opacity 0.5s var(--z4-ease);
}
.zh__cue.is-gone {
  opacity: 0;
}
.zh__ring,
.zh__chev {
  width: 1.4rem;
  height: 1.4rem;
}
.zh__ring {
  transform: rotate(-90deg);
}
.zh__ring circle {
  fill: none;
  stroke-width: 2;
}
.zh__ring-track {
  stroke: rgba(220, 214, 255, 0.25);
}
.zh__ring-fill {
  stroke: var(--z4-text);
  stroke-dasharray: 57;
  transition: stroke-dashoffset 0.12s linear;
}
.zh__chev path {
  fill: none;
  stroke: var(--z4-text);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.zh__chev {
  animation: zh-nudge 2.4s var(--z4-ease-io) infinite -0.6s;
}
@keyframes zh-nudge {
  0%,
  60%,
  100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(3px);
  }
}
@media (max-height: 560px) {
  .zh__cue {
    display: none;
  }
}

/* ---- the composed still ------------------------------------------------- */
.zh__static {
  display: none;
}
@media (max-width: 720px), (orientation: portrait) and (max-width: 1024px), (orientation: portrait) and (pointer: coarse), (orientation: landscape) and (pointer: coarse) and (max-height: 560px), (prefers-reduced-motion: reduce) {
  .zh__scrub {
    display: none;
  }
  .zh__static {
    position: relative;
    display: flex;
    min-height: 100svh;
    overflow: hidden;
  }
  .zh__static-bg {
    position: absolute;
    inset: 0;
    background: var(--z4-canvas) url('/landing/v4/hero-end.jpg') 75% 50% / cover no-repeat;
  }
  .zh__static-bg::after {
    content: '';
    position: absolute;
    inset: 0;
    background:
      linear-gradient(to top, var(--z4-canvas) 0%, rgba(15, 14, 20, 0) 18%),
      linear-gradient(100deg, rgba(10, 9, 14, 0.78) 0%, rgba(10, 9, 14, 0.5) 40%, rgba(10, 9, 14, 0) 70%);
  }
  .zh__static-copy {
    position: relative;
    align-self: center;
    width: 100%;
    max-width: 76rem;
    margin: 0 auto;
    padding: 7rem 1.5rem 4rem;
    text-shadow: var(--z4-tshadow);
  }
  .zh__static-copy > * {
    max-width: 40rem;
  }
}
@media (orientation: portrait) and (max-width: 1024px), (max-width: 720px) {
  .zh__static-bg {
    background-image: url('/landing/v4/hero-end-portrait.jpg');
    background-position: 50% 100%;
  }
  .zh__static-bg::after {
    background: linear-gradient(
      to bottom,
      rgba(10, 9, 14, 0.82) 0%,
      rgba(10, 9, 14, 0.66) 42%,
      rgba(10, 9, 14, 0.12) 68%,
      rgba(15, 14, 20, 0) 82%,
      var(--z4-canvas) 100%
    );
  }
  .zh__static-copy {
    align-self: flex-start;
    padding: 6.5rem 1.25rem 3rem;
  }
  .zh__static-h1 {
    font-size: clamp(2.4rem, 1.4rem + 5vw, 3.6rem);
  }
}
</style>
