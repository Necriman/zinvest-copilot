<script setup>
/**
 * Debounced search input.
 *
 * The text you type is held locally so the field never lags a keystroke behind;
 * `modelValue` only updates once typing pauses, which is what the parent
 * filters on. Clearing is immediate — there's nothing to wait for.
 */
import { onBeforeUnmount, ref, watch } from 'vue'

import Icon from './Icon.vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  delay: { type: Number, default: 250 },
  clearLabel: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const raw = ref(props.modelValue)
const input = ref(null)
let timer = null

// Keep in step when the parent resets the query itself.
watch(
  () => props.modelValue,
  (value) => {
    if (value !== raw.value) raw.value = value
  },
)

watch(raw, (value) => {
  clearTimeout(timer)
  if (!value) {
    emit('update:modelValue', '')
    return
  }
  timer = setTimeout(() => emit('update:modelValue', value), props.delay)
})

onBeforeUnmount(() => clearTimeout(timer))

function clear() {
  clearTimeout(timer)
  raw.value = ''
  emit('update:modelValue', '')
  input.value?.focus()
}
</script>

<template>
  <div class="relative">
    <Icon
      name="search"
      class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
    />
    <input
      ref="input"
      v-model="raw"
      type="search"
      :placeholder="placeholder"
      class="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-9 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none dark:border-hairline dark:bg-surface dark:text-ink [&::-webkit-search-cancel-button]:hidden"
    />
    <button
      v-if="raw"
      type="button"
      :aria-label="clearLabel || 'Clear'"
      :title="clearLabel || undefined"
      class="absolute right-1.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-surface-2 dark:hover:text-slate-200"
      @click="clear"
    >
      <Icon name="x" class="h-3.5 w-3.5" />
    </button>
  </div>
</template>
