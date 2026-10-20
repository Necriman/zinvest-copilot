<script setup>
// Lightweight right-click menu. Positioned at (x, y) in viewport coordinates,
// clamped to stay on-screen, and dismissed on any outside click, scroll, resize,
// or Escape. `items` is the item list (see ContextMenuList for the supported item
// shapes: divider, swatches, submenu via `children`, and regular actions).
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

import ContextMenuList from './ContextMenuList.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  x: { type: Number, default: 0 },
  y: { type: Number, default: 0 },
  items: { type: Array, default: () => [] },
})
const emit = defineEmits(['close'])

const menuEl = ref(null)
const left = ref(0)
const top = ref(0)

// Keep the menu fully inside the viewport (flip against right/bottom edges).
function reposition() {
  const el = menuEl.value
  const pad = 8
  const w = el?.offsetWidth || 200
  const h = el?.offsetHeight || 0
  left.value = Math.max(pad, Math.min(props.x, window.innerWidth - w - pad))
  top.value = Math.max(pad, Math.min(props.y, window.innerHeight - h - pad))
}

function close() {
  emit('close')
}

// --- global dismissal ------------------------------------------------------
function onDocMouse(e) {
  // Right-clicks are the editor's job (it repositions us); ignore them here.
  if (e.button === 2) return
  if (menuEl.value && !menuEl.value.contains(e.target)) close()
}
function onScroll() {
  close()
}
function onKey(e) {
  if (e.key === 'Escape') close()
}
function bind() {
  document.addEventListener('mousedown', onDocMouse, true)
  window.addEventListener('scroll', onScroll, true) // capture → catches nested scrollers
  window.addEventListener('resize', onScroll)
  document.addEventListener('keydown', onKey)
}
function unbind() {
  document.removeEventListener('mousedown', onDocMouse, true)
  window.removeEventListener('scroll', onScroll, true)
  window.removeEventListener('resize', onScroll)
  document.removeEventListener('keydown', onKey)
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      left.value = props.x
      top.value = props.y
      nextTick(() => {
        reposition()
        // Defer binding one tick so the opening right-click doesn't self-dismiss.
        setTimeout(bind, 0)
      })
    } else {
      unbind()
    }
  },
)
onBeforeUnmount(unbind)
</script>

<template>
  <Teleport to="body">
    <Transition name="pop">
      <div
        v-if="open"
        ref="menuEl"
        class="fixed z-[120] min-w-[11rem] origin-top-left rounded-xl border border-slate-200 bg-white p-1 shadow-float dark:border-hairline dark:bg-surface"
        :style="{ left: `${left}px`, top: `${top}px` }"
        role="menu"
        @contextmenu.prevent
      >
        <ContextMenuList :items="items" @close="close" />
      </div>
    </Transition>
  </Teleport>
</template>
