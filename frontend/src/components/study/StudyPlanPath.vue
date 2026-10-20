<script setup>
// Winding Duolingo-style path: nodes sit on a sine weave joined by a smooth
// cubic-bezier SVG track. The unit's accent colours the completed run, and the
// weave shape varies per unit (see accents.js) so categories don't all trace
// the same line. The bear waits beside the stop you are meant to do next.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import BearSticker from '@/components/mascot/BearSticker.vue'
import StudyPlanNode from './StudyPlanNode.vue'
import { accentOf, weaveFor } from './accents'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  accent: { type: String, default: 'brand' },
  /** Unit index — picks the weave shape. */
  variant: { type: Number, default: 0 },
  /** Stops completed since the learner last saw this map: that stretch of
   *  track draws itself in, instead of simply being there. */
  gained: { type: Number, default: 0 },
  /** The stop that became current since the last visit; it pops in last. */
  freshId: { type: String, default: null },
})
defineEmits(['select'])

const wrap = ref(null)
const width = ref(440)
let ro = null

const TOP_PAD = 56
const BOTTOM_PAD = 84 // room for the last node's label

const palette = computed(() => accentOf(props.accent))
const weave = computed(() => weaveFor(props.variant))

// How far nodes may swing from the centre line. Capped at 140 on wide layouts,
// but on a narrow phone it's also held to half the width minus the label's
// half-width (labels are max-w-[130px]) so a stop near the edge doesn't push its
// caption off the container — the overflow that clipped "Pay yourself first".
const LABEL_HALF = 68
const swing = computed(() =>
  Math.max(20, Math.min(width.value * weave.value.amp, 140, width.value / 2 - LABEL_HALF)),
)

const points = computed(() => {
  const cx = width.value / 2
  const { phase, step } = weave.value
  return props.nodes.map((n, i) => ({
    x: cx + swing.value * Math.sin((i * Math.PI) / 2 + phase),
    y: TOP_PAD + i * step,
  }))
})

const height = computed(
  () => TOP_PAD + Math.max(0, props.nodes.length - 1) * weave.value.step + BOTTOM_PAD,
)

const n = (v) => v.toFixed(1)

// One segment of track, from stop `a` to stop `b`. `cx` is the centre line.
const SEGMENT = {
  // Gentle S — control points at the vertical midpoint.
  wave: (a, b) => {
    const m = (a.y + b.y) / 2
    return ` C ${n(a.x)} ${n(m)}, ${n(b.x)} ${n(m)}, ${n(b.x)} ${n(b.y)}`
  },
  // A single belly, bulging away from the centre line.
  arc: (a, b, cx) => {
    const m = (a.y + b.y) / 2
    const mid = (a.x + b.x) / 2
    return ` Q ${n(mid + (mid >= cx ? 1 : -1) * 58)} ${n(m)}, ${n(b.x)} ${n(b.y)}`
  },
  // Squared-off route with rounded corners.
  step: (a, b) => {
    if (Math.abs(b.x - a.x) < 1) return ` L ${n(b.x)} ${n(b.y)}`
    const m = (a.y + b.y) / 2
    const dir = Math.sign(b.x - a.x)
    // Corner radius can never exceed half of either leg, or the corners cross.
    const r = Math.max(6, Math.min(22, Math.abs(b.x - a.x) / 2, Math.abs(b.y - a.y) / 2))
    return (
      ` L ${n(a.x)} ${n(m - r)}` +
      ` Q ${n(a.x)} ${n(m)}, ${n(a.x + dir * r)} ${n(m)}` +
      ` L ${n(b.x - dir * r)} ${n(m)}` +
      ` Q ${n(b.x)} ${n(m)}, ${n(b.x)} ${n(m + r)}` +
      ` L ${n(b.x)} ${n(b.y)}`
    )
  },
  // Exaggerated S — control points pushed apart so the track sweeps out.
  swoop: (a, b) => {
    const dy = b.y - a.y
    return ` C ${n(a.x)} ${n(a.y + dy * 0.9)}, ${n(b.x)} ${n(b.y - dy * 0.9)}, ${n(b.x)} ${n(b.y)}`
  },
}

function buildPath(pts) {
  if (pts.length < 2) return ''
  const seg = SEGMENT[weave.value.curve] || SEGMENT.wave
  const cx = width.value / 2
  let d = `M ${n(pts[0].x)} ${n(pts[0].y)}`
  for (let i = 1; i < pts.length; i++) d += seg(pts[i - 1], pts[i], cx)
  return d
}

// Leading run of completed nodes (lessons complete in order). The current node
// sits at index progressCount; the accent trail runs through it, dashed after.
const progressCount = computed(() => {
  let c = 0
  for (const n of props.nodes) {
    if (n.state === 'completed') c++
    else break
  }
  return c
})
// With progress since the last visit, the run is drawn in two pieces: the
// part the learner had already seen, still, and the new stretch, which draws
// from the old position to the new one.
const seenCount = computed(() => Math.max(0, progressCount.value - props.gained))
const completedPath = computed(() =>
  buildPath(points.value.slice(0, (props.gained ? seenCount.value : progressCount.value) + 1)),
)
const gainedPath = computed(() =>
  props.gained ? buildPath(points.value.slice(seenCount.value, progressCount.value + 1)) : '',
)
const lockedPath = computed(() => buildPath(points.value.slice(progressCount.value)))

// The bear stands on the far side of the current stop, where the track is not.
// Hidden when the column is too narrow to fit it without touching the node.
const bear = computed(() => {
  const i = props.nodes.findIndex((node) => node.state === 'current')
  if (i < 0) return null
  const p = points.value[i]
  const dir = p.x >= width.value / 2 ? -1 : 1
  const x = Math.max(52, Math.min(width.value - 52, p.x + dir * 120))
  if (Math.abs(x - p.x) < 100) return null
  return { node: props.nodes[i], x, y: p.y + 6, test: props.nodes[i].kind === 'test' }
})

function measure() {
  if (wrap.value) width.value = wrap.value.clientWidth
}

onMounted(() => {
  ro = new ResizeObserver(measure)
  ro.observe(wrap.value)
  measure()
})
onBeforeUnmount(() => ro?.disconnect())
</script>

<template>
  <div ref="wrap" class="relative mx-auto w-full max-w-md" :style="{ height: height + 'px' }">
    <!-- The bear points the way; the node itself stays the real button. -->
    <div
      v-if="bear"
      class="spp-bear absolute h-28 w-28 cursor-pointer"
      :style="{ left: bear.x + 'px', top: bear.y + 'px', transform: 'translate(-50%, -50%)' }"
      aria-hidden="true"
      @click="$emit('select', bear.node)"
    >
      <BearSticker :name="bear.test ? 'book' : 'point'" pop float class="h-full w-full" />
    </div>

    <svg
      class="pointer-events-none absolute inset-0"
      :width="width"
      :height="height"
      :viewBox="`0 0 ${width} ${height}`"
      fill="none"
    >
      <!-- Upcoming: dashed, in a faded version of the unit's accent. Tinted
           rather than grey so a brand-new learner — who has no completed run
           yet — still sees four visibly different categories. -->
      <path
        v-if="lockedPath"
        data-track="todo"
        :d="lockedPath"
        stroke="currentColor"
        :class="palette.trackSoft"
        :stroke-width="weave.width"
        :stroke-dasharray="weave.dash"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <!-- Completed → current: thick solid, in the unit's accent -->
      <path
        v-if="(gained ? seenCount : progressCount) > 0"
        data-track="done"
        :d="completedPath"
        stroke="currentColor"
        :class="palette.track"
        :stroke-width="weave.width"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <!-- Done since the last visit. pathLength="1" makes the dash units the
           path's own length, so it draws in exactly, whatever its shape. -->
      <path
        v-if="gainedPath"
        data-track="gained"
        class="spp-draw"
        :d="gainedPath"
        pathLength="1"
        stroke="currentColor"
        :class="palette.track"
        :stroke-width="weave.width"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>

    <!-- translate Y by -32px (half the 64px circle) so the CIRCLE center — not the
         circle+label button center — sits on the point, and the track threads
         through the circle centers regardless of label line count. -->
    <div
      v-for="(node, i) in nodes"
      :key="`${node.id}-${i}`"
      class="absolute"
      :style="{ left: points[i].x + 'px', top: points[i].y + 'px', transform: 'translate(-50%, -32px)' }"
    >
      <StudyPlanNode
        :node="node"
        :accent="accent"
        :index="i"
        :fresh="!!freshId && node.id === freshId"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
/* The new stretch of track: waits a beat so the eye lands on the map, then
   draws from where the learner was to where they are. */
.spp-draw {
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: spp-draw 800ms cubic-bezier(0.22, 0.61, 0.36, 1) 250ms forwards;
}
@keyframes spp-draw {
  to {
    stroke-dashoffset: 0;
  }
}

/* The bear follows the track to the new stop instead of teleporting. */
.spp-bear {
  transition:
    left 900ms cubic-bezier(0.65, 0, 0.35, 1) 200ms,
    top 900ms cubic-bezier(0.65, 0, 0.35, 1) 200ms;
}

@media (prefers-reduced-motion: reduce) {
  .spp-draw {
    animation: none;
    stroke-dashoffset: 0;
  }
  .spp-bear {
    transition: none;
  }
}
</style>
