<script setup>
// Tiny popover used by the editor toolbar (block type, font, table, math menus).
// Owns open/close + outside-click/Escape and wraps its panel in the global `pop`
// transition, so every toolbar dropdown snaps open identically. On open it resolves
// which side to anchor so the panel never spills past the toolbar's right edge (the
// editor pane boundary) into a neighbouring pane.
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  align: { type: String, default: 'auto' }, // auto → flip to fit | left | right
  panelClass: { type: String, default: 'min-w-[12rem]' },
})

const root = ref(null)
const panel = ref(null)
const open = ref(false)
const side = ref('left') // resolved anchor side (left | right)

function toggle() {
  open.value = !open.value
}
function close() {
  open.value = false
}

watch(open, (o) => {
  if (!o) return
  side.value = props.align === 'right' ? 'right' : 'left'
  if (props.align === 'left' || props.align === 'right') return
  // Measure once open: if a left-anchored panel would overflow the toolbar's right
  // edge, anchor it right instead (opens leftward). The pop fade masks the flip.
  nextTick(() => {
    const p = panel.value
    const r = root.value
    if (!p || !r) return
    const pad = 8
    const boundary = r.closest('.shrink-0') // the editor toolbar spans the pane width
    const rightEdge = Math.min(boundary ? boundary.getBoundingClientRect().right : window.innerWidth, window.innerWidth) - pad
    side.value = r.getBoundingClientRect().left + p.offsetWidth > rightEdge ? 'right' : 'left'
  })
})

function onDoc(e) {
  if (open.value && root.value && !root.value.contains(e.target)) open.value = false
}
function onKey(e) {
  if (e.key === 'Escape') open.value = false
}
onMounted(() => {
  document.addEventListener('mousedown', onDoc)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDoc)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div ref="root" class="relative">
    <slot name="trigger" :open="open" :toggle="toggle" />
    <Transition name="pop">
      <div
        v-if="open"
        ref="panel"
        :class="[
          'absolute top-full z-30 mt-2 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-float dark:border-hairline dark:bg-surface',
          side === 'right' ? 'right-0 origin-top-right' : 'left-0 origin-top-left',
          panelClass,
        ]"
      >
        <slot name="panel" :close="close" />
      </div>
    </Transition>
  </div>
</template>
