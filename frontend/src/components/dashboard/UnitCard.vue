<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'

const props = defineProps({
  unit: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})

const TINT = {
  brand: 'bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400',
  invest: 'bg-blue-50 text-blue-600 dark:bg-blue-500/15 dark:text-blue-400',
  risk: 'bg-violet-50 text-violet-600 dark:bg-violet-500/15 dark:text-violet-400',
  budget: 'bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-400',
  cash: 'bg-green-50 text-green-600 dark:bg-green-500/15 dark:text-green-400',
}
const BAR = {
  brand: 'bg-brand-600',
  invest: 'bg-blue-600',
  risk: 'bg-violet-600',
  budget: 'bg-amber-500',
  cash: 'bg-green-600',
}
const tint = computed(() => TINT[props.unit.color] || TINT.brand)
const bar = computed(() => BAR[props.unit.color] || BAR.brand)
</script>

<template>
  <RouterLink
    :to="{ name: 'studyPlan', query: { unit: unit.id } }"
    class="card group relative flex items-center gap-4 p-4 transition hover:shadow-md"
    :class="{ 'ring-2 ring-brand-500': selected, 'opacity-70': unit.locked }"
  >
    <div class="flex h-11 w-11 items-center justify-center rounded-xl" :class="tint">
      <Icon :name="unit.icon || 'book'" class="h-5 w-5" />
    </div>
    <div class="min-w-0 flex-1">
      <p class="text-xs font-semibold uppercase tracking-wide text-slate-400">{{ $t('unitTest.unitCode', { code: unit.code }) }}</p>
      <p class="line-clamp-2 font-bold leading-snug text-slate-900 dark:text-white">{{ unit.title }}</p>
      <ProgressBar :value="unit.progress" :color="bar" class="mt-2" />
    </div>
    <Icon v-if="unit.locked" name="lock" class="h-4 w-4 text-slate-400" />
    <Icon v-else name="chevronRight" class="h-4 w-4 text-slate-300 transition group-hover:translate-x-0.5" />
  </RouterLink>
</template>
