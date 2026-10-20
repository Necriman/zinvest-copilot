<script setup>
// High-end text-color popover (no native <input type="color">). Renders its own
// "A + underline" trigger and a dropdown of Tailwind swatches. Emits `select`
// with a hex and `reset` to clear the color. Closes on outside-click / Escape.
import { onBeforeUnmount, onMounted, ref } from 'vue'

import Icon from '@/components/ui/Icon.vue'

const props = defineProps({
  color: { type: String, default: '#0f172a' }, // current color → drives the underline
})
const emit = defineEmits(['select', 'reset'])

// 3 rows (light · base · dark) × 10 hues (gray, red, orange, amber, green, teal,
// blue, indigo, purple, pink). Row-major so the grid reads light→dark top→bottom.
const SWATCHES = [
  ['#94a3b8', '#f87171', '#fb923c', '#fbbf24', '#4ade80', '#2dd4bf', '#60a5fa', '#818cf8', '#c084fc', '#f472b6'],
  ['#475569', '#dc2626', '#ea580c', '#d97706', '#16a34a', '#0d9488', '#2563eb', '#4f46e5', '#9333ea', '#db2777'],
  ['#1e293b', '#991b1b', '#9a3412', '#92400e', '#166534', '#115e59', '#1e40af', '#3730a3', '#6b21a8', '#9d174d'],
  ['#ffffff', '#000000'], // white + black (default/reset stays available above)
].flat()

const root = ref(null)
const open = ref(false)

function toggle() {
  open.value = !open.value
}
function choose(hex) {
  emit('select', hex)
  open.value = false
}
function reset() {
  emit('reset')
  open.value = false
}

// Dismiss when the user clicks anywhere outside the menu or hits Escape.
function onDocClick(e) {
  if (open.value && root.value && !root.value.contains(e.target)) open.value = false
}
function onKey(e) {
  if (e.key === 'Escape') open.value = false
}
onMounted(() => {
  document.addEventListener('mousedown', onDocClick)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocClick)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div ref="root" class="relative">
    <!-- Trigger: "A" glyph over a bar tinted with the active color -->
    <button
      type="button"
      class="flex flex-col items-center rounded-lg px-2 py-1.5 transition-all duration-200 ease-in-out hover:bg-slate-100 dark:hover:bg-surface-2"
      :class="open ? 'bg-slate-100 dark:bg-surface-2' : ''"
      :title="$t('editor.textColor')"
      @click="toggle"
    >
      <span class="text-sm font-bold leading-none text-slate-700 dark:text-slate-200">A</span>
      <span class="mt-0.5 h-1 w-4 rounded" :style="{ background: color }" />
    </button>

    <!-- Popover -->
    <Transition name="pop">
      <div
        v-if="open"
        class="absolute left-0 top-full z-30 mt-2 w-max origin-top-left rounded-2xl border border-slate-200 bg-white p-2 shadow-float dark:border-hairline dark:bg-surface"
      >
        <!-- Reset to default -->
        <button
          type="button"
          class="flex w-full items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-all duration-200 ease-in-out hover:bg-slate-50 dark:border-hairline dark:text-slate-200 dark:hover:bg-surface-2"
          @click="reset"
        >
          <Icon name="eraser" class="h-4 w-4 text-slate-500 dark:text-slate-400" />
          {{ $t('editor.defaultTheme') }}
        </button>

        <div class="my-2 h-px bg-slate-200 dark:bg-hairline" />

        <!-- Swatch grid: 3 rows × 10 hues -->
        <div class="grid grid-cols-10 gap-1.5">
          <button
            v-for="hex in SWATCHES"
            :key="hex"
            type="button"
            class="h-5 w-5 rounded-md ring-1 ring-inset ring-black/10 transition-transform duration-150 ease-out hover:scale-125"
            :class="hex.toLowerCase() === color.toLowerCase() ? 'ring-2 ring-brand-500 ring-offset-1 dark:ring-offset-surface' : ''"
            :style="{ background: hex }"
            :title="hex"
            @click="choose(hex)"
          />
        </div>
      </div>
    </Transition>
  </div>
</template>
