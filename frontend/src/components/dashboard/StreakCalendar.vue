<script setup>
/**
 * Day streak + this week's calendar.
 *
 * A streak day is earned by finishing a lesson or a unit test — never by merely
 * opening the app — so today renders as *pending* (dashed ring) until it's
 * banked. The server zeroes a lapsed streak on read, so `streak` is always the
 * live number rather than a frozen historical one.
 */
import { computed } from 'vue'

import Icon from '@/components/ui/Icon.vue'

const props = defineProps({
  streak: { type: Number, default: 0 },
  longest: { type: Number, default: 0 },
  week: { type: Array, default: () => [] }, // [{ day, date, active }]
  activeToday: { type: Boolean, default: false },
})

/** Local calendar date as YYYY-MM-DD (toISOString would shift by the UTC offset). */
function localIso(d = new Date()) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const today = localIso()

const days = computed(() =>
  props.week.map((d) => ({
    ...d,
    isToday: d.date === today,
    isFuture: d.date > today,
  })),
)
</script>

<template>
  <div class="card p-5">
    <div class="flex items-center gap-3">
      <Icon
        name="flame"
        filled
        class="h-9 w-9"
        :class="streak > 0 ? 'text-orange-500' : 'text-slate-300 dark:text-slate-600'"
      />
      <div class="min-w-0">
        <p class="text-3xl font-extrabold leading-none text-slate-900 dark:text-white">{{ streak }}</p>
        <p class="mt-1 text-xs text-slate-500">{{ $t('common.streakDays') }}</p>
      </div>
      <p v-if="longest > streak" class="ml-auto shrink-0 text-right text-xs text-slate-400">
        {{ $t('dashboard.streakBest', { n: longest }) }}
      </p>
    </div>

    <div class="mt-5 flex items-center justify-between">
      <div v-for="d in days" :key="d.day" class="flex flex-col items-center gap-1.5">
        <span
          class="text-[10px] font-semibold uppercase"
          :class="d.isToday ? 'text-orange-500' : 'text-slate-400'"
        >
          {{ $t(`common.weekday.${d.day}`) }}
        </span>
        <span
          class="flex h-7 w-7 items-center justify-center rounded-full text-xs transition-colors"
          :class="[
            d.active
              ? 'bg-orange-500 text-white'
              : d.isToday
                ? 'border-2 border-dashed border-orange-400 text-orange-400'
                : d.isFuture
                  ? 'bg-slate-50 text-slate-300 dark:bg-surface-2/50'
                  : 'bg-slate-100 text-slate-400 dark:bg-surface-2',
          ]"
        >
          <Icon v-if="d.active" name="check" class="h-3.5 w-3.5" />
        </span>
      </div>
    </div>

    <p class="mt-4 text-xs" :class="activeToday ? 'text-green-600 dark:text-green-400' : 'text-slate-500'">
      {{ activeToday ? $t('dashboard.streakEarnedToday') : $t('dashboard.streakPendingToday') }}
    </p>
  </div>
</template>
