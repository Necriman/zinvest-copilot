<script setup>
// Where you stand in this week's league, in one line of the right rail.
// Fetches on its own so the card can appear anywhere without threading props.
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
import { getLeague } from '@/api/league'

defineProps({
  name: { type: String, default: '' },
})

const league = ref(null)

onMounted(async () => {
  try {
    league.value = await getLeague()
  } catch {
    // The rail is decoration: a failed call leaves the plain card.
  }
})

const DIVISION_COLOR = { bronze: 'budget', silver: 'slate', gold: 'amber', platinum: 'invest', diamond: 'risk' }
</script>

<template>
  <RouterLink :to="{ name: 'leaderboard' }" class="card flex items-center gap-3 p-4 transition hover:bg-slate-50 dark:hover:bg-surface-2/60">
    <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-900 text-sm font-bold text-white dark:bg-white dark:text-slate-900">
      {{ league?.me.rank ?? '—' }}
    </span>
    <div class="min-w-0 flex-1">
      <p class="truncate text-sm font-semibold text-slate-900 dark:text-white">{{ name }}</p>
      <p class="truncate text-xs text-slate-500">
        <template v-if="league">{{ $t('league.points', { n: league.me.points }) }}</template>
        <template v-else>{{ $t('dashboard.weeklyProgress') }}</template>
      </p>
    </div>
    <PillBadge v-if="league" :color="DIVISION_COLOR[league.division] || 'slate'" size="sm">
      {{ $t(`league.div_${league.division}`) }}
    </PillBadge>
    <Icon name="chevronRight" class="h-4 w-4 shrink-0 text-slate-300" />
  </RouterLink>
</template>
