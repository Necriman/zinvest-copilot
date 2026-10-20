<script setup>
// Visual table-size picker: a 10×10 grid where hovering highlights the region
// from [1,1] to the hovered cell, and clicking emits the chosen dimensions.
// Used inside the editor toolbar's table dropdown.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const emit = defineEmits(['select'])

const ROWS = 10
const COLS = 10
const hoverR = ref(0) // 0 = nothing hovered yet
const hoverC = ref(0)

const { t } = useI18n()
const label = computed(() =>
  hoverR.value && hoverC.value ? t('editor.table.size', { rows: hoverR.value, cols: hoverC.value }) : t('editor.table.pick'),
)

function inRegion(r, c) {
  return r <= hoverR.value && c <= hoverC.value
}
function hover(r, c) {
  hoverR.value = r
  hoverC.value = c
}
function reset() {
  hoverR.value = 0
  hoverC.value = 0
}
function pick(r, c) {
  emit('select', { rows: r, cols: c })
}
</script>

<template>
  <div class="p-1.5" @mouseleave="reset">
    <p class="mb-2 text-center text-xs font-semibold text-slate-500 dark:text-slate-400">
      {{ label }}
    </p>
    <div class="grid grid-cols-[repeat(10,1.25rem)] gap-1">
      <template v-for="r in ROWS" :key="r">
        <button
          v-for="c in COLS"
          :key="`${r}-${c}`"
          type="button"
          class="h-5 w-5 rounded-[5px] border transition-colors duration-100 ease-out"
          :class="
            inRegion(r, c)
              ? 'border-violet-400 bg-violet-200 dark:border-violet-500 dark:bg-violet-500/40'
              : 'border-slate-200 bg-slate-50 hover:border-slate-300 dark:border-hairline dark:bg-surface-2'
          "
          :aria-label="$t('editor.table.cell', { rows: r, cols: c })"
          @mouseover="hover(r, c)"
          @focus="hover(r, c)"
          @click="pick(r, c)"
        />
      </template>
    </div>
  </div>
</template>
