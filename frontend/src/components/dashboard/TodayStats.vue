<script setup>
// Three numbers under the hero: how far through the course, units closed, best test.
import { computed } from 'vue'

import Icon from '@/components/ui/Icon.vue'

const props = defineProps({ stats: { type: Object, default: null } })

const items = computed(() => [
  { key: 'course', icon: 'book', value: `${props.stats?.learning_progress ?? 0}`, unit: '%', hint: 'statsStrip.courseHint' },
  { key: 'units', icon: 'target', value: `${props.stats?.units_completed ?? 0}`, unit: ` / ${props.stats?.units_total ?? 0}`, hint: 'statsStrip.unitsHint' },
  { key: 'best', icon: 'trophy', value: `${props.stats?.best_score ?? 0}`, unit: '%', hint: 'statsStrip.bestHint' },
])
</script>

<template>
  <section class="card mb-5 grid grid-cols-1 divide-y divide-hairline sm:grid-cols-3 sm:divide-x sm:divide-y-0">
    <div v-for="item in items" :key="item.key" class="px-5 py-4">
      <p class="flex items-center gap-2 text-xs font-medium text-ink-muted">
        <Icon :name="item.icon" class="h-4 w-4" /> {{ $t(`statsStrip.${item.key}`) }}
      </p>
      <p class="mt-1.5 text-3xl font-bold tracking-tight text-ink">
        {{ item.value }}<span class="text-base font-semibold text-ink-muted">{{ item.unit }}</span>
      </p>
      <p class="mt-0.5 text-xs text-ink-muted">{{ $t(item.hint) }}</p>
    </div>
  </section>
</template>
