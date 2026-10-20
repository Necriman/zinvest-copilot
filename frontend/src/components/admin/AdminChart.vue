<script setup>
// Daily bars for the last N days. Plain HTML bars (not SVG), so they stay
// crisp at any width; each one names its day and value on hover.
import { computed } from 'vue'

import { useAdminFormat } from '@/composables/useAdminFormat'

const props = defineProps({
  title: { type: String, required: true },
  points: { type: Array, default: () => [] }, // [{ date, value }]
  tone: { type: String, default: 'brand' }, // brand | green | amber
})

const fmt = useAdminFormat()

const BARS = {
  brand: 'bg-brand-500/80 group-hover:bg-brand-600 dark:bg-brand-400/80',
  green: 'bg-green-500/80 group-hover:bg-green-600 dark:bg-green-400/80',
  amber: 'bg-amber-500/80 group-hover:bg-amber-600 dark:bg-amber-400/80',
}

const max = computed(() => Math.max(1, ...props.points.map((p) => p.value || 0)))
const total = computed(() => props.points.reduce((sum, p) => sum + (p.value || 0), 0))
const first = computed(() => props.points[0]?.date)
const last = computed(() => props.points[props.points.length - 1]?.date)
</script>

<template>
  <section class="card p-4 sm:p-5">
    <div class="flex items-baseline justify-between gap-3">
      <h3 class="text-sm font-bold text-slate-800 dark:text-slate-100">{{ title }}</h3>
      <p class="text-sm font-extrabold tabular-nums text-slate-900 dark:text-white">{{ fmt.num(total) }}</p>
    </div>
    <div class="relative mt-4">
      <span class="absolute -top-1 right-0 text-[10px] tabular-nums text-slate-400">{{ fmt.num(max) }}</span>
      <div class="flex h-28 items-end gap-[3px] border-b border-slate-200 pt-3 dark:border-hairline" role="img" :aria-label="`${title}: ${fmt.num(total)}`">
        <div
          v-for="p in points"
          :key="p.date"
          class="group flex h-full flex-1 items-end"
          :title="`${fmt.shortDate(p.date)}: ${fmt.num(p.value)}`"
        >
          <div
            class="w-full rounded-t-[3px] transition-colors"
            :class="p.value ? BARS[tone] || BARS.brand : 'bg-slate-200 dark:bg-surface-2'"
            :style="{ height: p.value ? `${Math.max(4, (p.value / max) * 100)}%` : '2px' }"
          />
        </div>
      </div>
      <div class="mt-1.5 flex justify-between text-[11px] text-slate-400">
        <span>{{ fmt.shortDate(first) }}</span>
        <span>{{ fmt.shortDate(last) }}</span>
      </div>
    </div>
  </section>
</template>
