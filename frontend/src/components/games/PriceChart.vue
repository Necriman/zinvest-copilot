<script setup>
/**
 * The "Up or down?" chart: the price up to the moment of the call, a shaded
 * panel where the future goes, and — once the call is made — the rest of the
 * story drawn in, green if it went up, red if it went down.
 *
 * Before the call the scale is set by the past alone: a range stretched to
 * fit the future would give the answer away (the round from the server does
 * not carry the future at all, so nothing could leak even by accident). On
 * the reveal the scale eases out to fit everything first and only then is
 * the new line drawn, so the jump reads as a camera move rather than a cut.
 *
 * Drawn in real pixels (the width is measured), so the labels stay the same
 * size on a phone and on a wide screen.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { formatChange, formatPrice } from './price'

const props = defineProps({
  before: { type: Array, required: true },
  after: { type: Array, default: null },
  unit: { type: String, default: '$' },
  up: { type: Boolean, default: true },
  label: { type: String, default: '' },
  // The small version on Home: no labels, no panel text.
  mini: { type: Boolean, default: false },
})

const box = ref(null)
const width = ref(640)
const height = computed(() => (props.mini ? 72 : Math.round(Math.min(320, Math.max(220, width.value * 0.46)))))
const PAST_SHARE = 0.62
const pad = computed(() =>
  props.mini ? { l: 2, r: 2, t: 6, b: 6 } : { l: 12, r: 12, t: 34, b: 34 },
)
const split = computed(() => pad.value.l + (width.value - pad.value.l - pad.value.r) * PAST_SHARE)

// 0 → the past only; 1 → the whole story. `drawn` is how much of the new line is on screen.
const zoom = ref(0)
const drawn = ref(0)

function range(values, share) {
  const lo = Math.min(...values)
  const hi = Math.max(...values)
  const room = (hi - lo) * share || Math.abs(hi) * 0.1 || 1
  return [lo - room, hi + room]
}
const pastRange = computed(() => range(props.before, 0.18))
const fullRange = computed(() => (props.after ? range([...props.before, ...props.after], 0.14) : pastRange.value))
const yRange = computed(() => {
  const [a0, a1] = pastRange.value
  const [b0, b1] = fullRange.value
  const k = zoom.value
  return [a0 + (b0 - a0) * k, a1 + (b1 - a1) * k]
})

function y(value) {
  const [lo, hi] = yRange.value
  const { t, b } = pad.value
  return t + (height.value - t - b) * (1 - (value - lo) / (hi - lo || 1))
}
function spread(values, x0, x1) {
  const n = Math.max(1, values.length - 1)
  return values.map((v, i) => [x0 + ((x1 - x0) * i) / n, y(v)])
}

const past = computed(() => spread(props.before, pad.value.l, split.value))
const future = computed(() =>
  props.after ? spread([props.before[props.before.length - 1], ...props.after], split.value, width.value - pad.value.r) : [],
)

// Catmull-Rom through every point, as cubic Béziers: smooth, and still exact at each price.
function smooth(points) {
  if (points.length < 2) return ''
  const f = (n) => n.toFixed(1)
  let d = `M${f(points[0][0])},${f(points[0][1])}`
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] || points[i]
    const p1 = points[i]
    const p2 = points[i + 1]
    const p3 = points[i + 2] || p2
    d += `C${f(p1[0] + (p2[0] - p0[0]) / 6)},${f(p1[1] + (p2[1] - p0[1]) / 6)} ${f(p2[0] - (p3[0] - p1[0]) / 6)},${f(p2[1] - (p3[1] - p1[1]) / 6)} ${f(p2[0])},${f(p2[1])}`
  }
  return d
}
const floor = computed(() => height.value - pad.value.b)
const pastLine = computed(() => smooth(past.value))
const pastArea = computed(() => `${pastLine.value}L${split.value.toFixed(1)},${floor.value}L${pad.value.l},${floor.value}Z`)
const futureLine = computed(() => smooth(future.value))
const futureArea = computed(() =>
  future.value.length
    ? `${futureLine.value}L${(width.value - pad.value.r).toFixed(1)},${floor.value}L${split.value.toFixed(1)},${floor.value}Z`
    : '',
)

const grid = computed(() => {
  const { t, b } = pad.value
  return [0, 1, 2, 3, 4].map((i) => t + ((height.value - t - b) * i) / 4)
})
// Oil in April 2020: a price below zero only reads as one with the zero drawn.
const zeroY = computed(() => {
  const [lo, hi] = yRange.value
  return lo < 0 && hi > 0 ? y(0) : null
})

const start = computed(() => props.before[0])
const now = computed(() => props.before[props.before.length - 1])
const end = computed(() => (props.after ? props.after[props.after.length - 1] : null))
const decision = computed(() => past.value[past.value.length - 1])
const finish = computed(() => future.value[future.value.length - 1])
const tone = computed(() => (props.up ? 'var(--game-up)' : 'var(--game-down)'))
const endLabel = computed(() => {
  if (end.value == null) return ''
  const change = formatChange(now.value, end.value)
  return `${formatPrice(end.value, props.unit)}${change ? `  ${change}` : ''}`
})
// Labels go on whichever side of the line has room.
const startAbove = computed(() => start.value >= props.before[Math.floor(props.before.length / 2)])

// ---- the reveal ---------------------------------------------------------
let frame = 0
function animate(duration, step) {
  return new Promise((resolve) => {
    const t0 = performance.now()
    const tick = (now) => {
      const k = Math.min(1, (now - t0) / duration)
      step(k)
      if (k < 1) frame = requestAnimationFrame(tick)
      else resolve()
    }
    frame = requestAnimationFrame(tick)
  })
}
const ease = (k) => (k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2)
const reduced = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

watch(
  () => props.after,
  async (after) => {
    cancelAnimationFrame(frame)
    if (!after) {
      zoom.value = 0
      drawn.value = 0
      return
    }
    if (reduced()) {
      zoom.value = 1
      drawn.value = 1
      return
    }
    zoom.value = 0
    drawn.value = 0
    await animate(450, (k) => (zoom.value = ease(k)))
    await animate(1100, (k) => (drawn.value = 1 - (1 - k) ** 3))
  },
  { immediate: true },
)

// ---- size ---------------------------------------------------------------
let observer
onMounted(() => {
  const measure = () => {
    if (box.value) width.value = Math.max(260, Math.round(box.value.clientWidth))
  }
  measure()
  observer = new ResizeObserver(measure)
  observer.observe(box.value)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  observer?.disconnect()
})
</script>

<template>
  <div ref="box" class="price-chart" :class="{ 'price-chart--mini': mini }">
    <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" role="img" :aria-label="label">
      <defs>
        <linearGradient :id="`past-fill-${mini}`" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" :style="{ stopColor: 'var(--game-line)', stopOpacity: 0.22 }" />
          <stop offset="1" :style="{ stopColor: 'var(--game-line)', stopOpacity: 0 }" />
        </linearGradient>
        <linearGradient :id="`future-fill-${mini}`" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" :style="{ stopColor: tone, stopOpacity: 0.24 }" />
          <stop offset="1" :style="{ stopColor: tone, stopOpacity: 0 }" />
        </linearGradient>
      </defs>

      <g v-if="!mini" class="price-chart__grid">
        <line v-for="g in grid" :key="g" :x1="pad.l" :x2="width - pad.r" :y1="g" :y2="g" />
      </g>
      <g v-if="zeroY !== null && !mini">
        <line class="price-chart__zero" :x1="pad.l" :x2="width - pad.r" :y1="zeroY" :y2="zeroY" />
        <text class="price-chart__muted" :x="pad.l + 2" :y="zeroY - 6">0</text>
      </g>

      <!-- Where the future goes, until it is known. -->
      <g class="price-chart__unknown" :class="{ 'is-gone': after }">
        <rect
          :x="split + (mini ? 6 : 14)"
          :y="pad.t"
          :width="Math.max(0, width - pad.r - split - (mini ? 6 : 14))"
          :height="height - pad.t - pad.b"
          :rx="mini ? 8 : 16"
        />
        <text
          :x="(split + (mini ? 6 : 14) + width - pad.r) / 2"
          :y="(pad.t + height - pad.b) / 2"
          :font-size="mini ? 26 : 64"
          dominant-baseline="central"
          text-anchor="middle"
        >?</text>
      </g>

      <path :d="pastArea" :fill="`url(#past-fill-${mini})`" />
      <path :d="pastLine" class="price-chart__line price-chart__line--past" />

      <template v-if="after">
        <path :d="futureArea" :fill="`url(#future-fill-${mini})`" :style="{ opacity: drawn }" />
        <path
          :d="futureLine"
          class="price-chart__line"
          :style="{ stroke: tone }"
          pathLength="1"
          :stroke-dasharray="1"
          :stroke-dashoffset="1 - drawn"
        />
      </template>

      <!-- The moment of the call. -->
      <circle v-if="decision" :cx="decision[0]" :cy="decision[1]" :r="mini ? 3.5 : 6" class="price-chart__dot" :class="{ 'is-waiting': !after && !mini }" />
      <circle v-if="after && finish && drawn > 0.98" :cx="finish[0]" :cy="finish[1]" :r="mini ? 3.5 : 6" :style="{ fill: tone }" />

      <template v-if="!mini">
        <text class="price-chart__muted" :x="pad.l" :y="past[0][1] + (startAbove ? -12 : 20)">{{ formatPrice(start, unit) }}</text>
        <text
          class="price-chart__strong"
          :x="decision[0]"
          :y="decision[1] + (after ? (up ? 22 : -14) : -14)"
          text-anchor="end"
        >{{ formatPrice(now, unit) }}</text>
        <text
          v-if="after && finish && drawn > 0.98"
          class="price-chart__end"
          :style="{ fill: tone }"
          :x="finish[0]"
          :y="finish[1] + (up ? -14 : 24)"
          text-anchor="end"
        >{{ endLabel }}</text>
      </template>
    </svg>
  </div>
</template>

<style scoped>
.price-chart {
  --game-line: #4f8cff;
  --game-up: #16a34a;
  --game-down: #dc2626;
  width: 100%;
  color: var(--color-ink);
}
.dark .price-chart {
  --game-line: #7aa7ff;
  --game-up: #22c55e;
  --game-down: #f87171;
}
.price-chart svg {
  display: block;
  overflow: visible;
}
.price-chart__grid line {
  stroke: currentColor;
  stroke-opacity: 0.08;
  stroke-width: 1;
}
.price-chart__zero {
  stroke: currentColor;
  stroke-opacity: 0.35;
  stroke-width: 1.5;
  stroke-dasharray: 4 4;
}
.price-chart__line {
  fill: none;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.price-chart__line--past {
  stroke: var(--game-line);
}
.price-chart--mini .price-chart__line {
  stroke-width: 2;
}
.price-chart__unknown rect {
  fill: currentColor;
  fill-opacity: 0.04;
  stroke: currentColor;
  stroke-opacity: 0.14;
  stroke-width: 1.5;
  stroke-dasharray: 6 6;
}
.price-chart__unknown text {
  fill: currentColor;
  fill-opacity: 0.28;
  font-weight: 800;
}
.price-chart__unknown {
  transition: opacity 0.35s ease;
}
.price-chart__unknown.is-gone {
  opacity: 0;
}
.price-chart__dot {
  fill: var(--color-ink);
  stroke: var(--surface);
  stroke-width: 3;
}
.price-chart__dot.is-waiting {
  animation: price-chart-pulse 1.6s ease-in-out infinite;
  transform-box: fill-box;
  transform-origin: center;
}
@keyframes price-chart-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.35); }
}
.price-chart__muted {
  fill: currentColor;
  fill-opacity: 0.5;
  font-size: 12px;
  font-weight: 600;
}
.price-chart__strong {
  fill: currentColor;
  font-size: 13px;
  font-weight: 700;
}
.price-chart__end {
  font-size: 14px;
  font-weight: 800;
}
@media (prefers-reduced-motion: reduce) {
  .price-chart__dot.is-waiting {
    animation: none;
  }
}
</style>
