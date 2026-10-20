<script setup>
// On/off row: label and hint on the left, the switch on the right. Same
// switch as Settings → Appearance.
import { useId } from 'vue'

defineProps({
  modelValue: { type: Boolean, default: false },
  label: { type: String, required: true },
  hint: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])
const id = useId()
</script>

<template>
  <div class="flex items-center gap-4 py-3">
    <div class="min-w-0 flex-1">
      <p :id="`${id}-label`" class="text-sm font-semibold text-slate-700 dark:text-slate-200">{{ label }}</p>
      <p v-if="hint" :id="`${id}-hint`" class="mt-0.5 text-xs text-slate-500">{{ hint }}</p>
    </div>
    <button
      type="button"
      role="switch"
      :aria-checked="modelValue"
      :aria-labelledby="`${id}-label`"
      :aria-describedby="hint ? `${id}-hint` : undefined"
      :disabled="disabled"
      class="relative h-7 w-12 shrink-0 rounded-full transition disabled:opacity-50"
      :class="modelValue ? 'bg-brand-600' : 'bg-slate-300 dark:bg-slate-600'"
      @click="emit('update:modelValue', !modelValue)"
    >
      <span class="absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition-all" :class="modelValue ? 'left-[22px]' : 'left-0.5'" />
    </button>
  </div>
</template>
