<script setup>
import Icon from './Icon.vue'

defineProps({
  name: { type: String, required: true },
  label: { type: String, default: '' },
})
</script>

<template>
  <button
    type="button"
    :aria-label="label"
    class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 dark:border-hairline dark:bg-surface dark:text-slate-300 dark:hover:bg-surface-2 dark:hover:text-white"
  >
    <Icon :name="name" class="h-5 w-5" />
  </button>
</template>
