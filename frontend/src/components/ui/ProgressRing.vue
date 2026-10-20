<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 }, // 0..100
  size: { type: Number, default: 44 },
  stroke: { type: Number, default: 5 },
  color: { type: String, default: 'text-brand-600' },
})

const radius = computed(() => (props.size - props.stroke) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const offset = computed(() => {
  const pct = Math.max(0, Math.min(100, props.value))
  return circumference.value * (1 - pct / 100)
})
</script>

<template>
  <div class="relative inline-flex items-center justify-center" :style="{ width: size + 'px', height: size + 'px' }">
    <svg :width="size" :height="size" class="-rotate-90">
      <circle
        :cx="size / 2" :cy="size / 2" :r="radius" :stroke-width="stroke"
        class="fill-none stroke-slate-100 dark:stroke-slate-800"
      />
      <circle
        :cx="size / 2" :cy="size / 2" :r="radius" :stroke-width="stroke"
        stroke-linecap="round"
        class="fill-none transition-all duration-500"
        :class="color"
        stroke="currentColor"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
      />
    </svg>
    <span class="absolute text-[11px] font-bold text-slate-700 dark:text-slate-200">
      <slot>{{ Math.round(value) }}</slot>
    </span>
  </div>
</template>
