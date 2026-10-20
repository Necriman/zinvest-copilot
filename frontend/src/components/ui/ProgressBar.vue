<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 }, // 0..100
  color: { type: String, default: 'bg-brand-600' },
})
const pct = computed(() => Math.max(0, Math.min(100, Math.round(props.value))))
</script>

<template>
  <div class="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-surface-2">
    <div class="h-full rounded-full transition-all duration-500" :class="color" :style="{ width: pct + '%' }" />
  </div>
</template>
