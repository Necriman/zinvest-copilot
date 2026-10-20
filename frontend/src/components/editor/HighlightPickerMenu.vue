<script setup>
// Highlight-color popover. Mirrors ColorPickerMenu but drives the Highlight mark:
// emits `select` with a hex (→ setHighlight({ color })) and `reset` to clear it.
// Closes on outside-click / Escape.
import { onBeforeUnmount, onMounted, ref } from 'vue'

import Icon from '@/components/ui/Icon.vue'

defineProps({
  color: { type: String, default: '#fef08a' }, // current highlight → drives the bar
})
const emit = defineEmits(['select', 'reset'])

// Soft, readable highlighter fills (yellow, amber, red, pink, green, teal, blue, purple).
const SWATCHES = ['#fef08a', '#fde68a', '#fecaca', '#fbcfe8', '#bbf7d0', '#a7f3d0', '#bfdbfe', '#ddd6fe']

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
    <!-- Trigger: highlighter glyph over a bar tinted with the active highlight -->
    <button
      type="button"
      class="flex flex-col items-center rounded-lg px-2 py-1.5 transition-all duration-200 ease-in-out hover:bg-slate-100 dark:hover:bg-surface-2"
      :class="open ? 'bg-slate-100 dark:bg-surface-2' : ''"
      :title="$t('editor.highlightColor')"
      @click="toggle"
    >
      <Icon name="highlighter" class="h-4 w-4 text-slate-700 dark:text-slate-200" />
      <span class="mt-0.5 h-1 w-4 rounded" :style="{ background: color }" />
    </button>

    <!-- Popover -->
    <Transition name="pop">
      <div
        v-if="open"
        class="absolute left-0 top-full z-30 mt-2 w-max origin-top-left rounded-2xl border border-slate-200 bg-white p-2 shadow-float dark:border-hairline dark:bg-surface"
      >
        <button
          type="button"
          class="mb-2 flex w-full items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-all duration-200 ease-in-out hover:bg-slate-50 dark:border-hairline dark:text-slate-200 dark:hover:bg-surface-2"
          @click="reset"
        >
          <Icon name="eraser" class="h-4 w-4 text-slate-500 dark:text-slate-400" />
          {{ $t('editor.noHighlight') }}
        </button>

        <div class="grid grid-cols-4 gap-1.5">
          <button
            v-for="hex in SWATCHES"
            :key="hex"
            type="button"
            class="h-6 w-6 rounded-md ring-1 ring-inset ring-black/10 transition-transform duration-150 ease-out hover:scale-110 dark:ring-white/15"
            :class="hex.toLowerCase() === (color || '').toLowerCase() ? 'ring-2 ring-brand-500 ring-offset-1 dark:ring-offset-surface' : ''"
            :style="{ background: hex }"
            :title="hex"
            @click="choose(hex)"
          />
        </div>
      </div>
    </Transition>
  </div>
</template>
