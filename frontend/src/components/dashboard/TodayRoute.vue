<script setup>
import { RouterLink } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'

const LINKS = [
  { icon: 'map', title: 'today.plan', sub: 'today.planSub', to: { name: 'studyPlan' } },
  { icon: 'zap', title: 'challenge.title', sub: 'today.drillsSub', to: { name: 'drills' } },
  { icon: 'bot', title: 'dashboard.route04', sub: 'today.aiSub', to: { name: 'zinvestAI' } },
]
</script>

<template>
  <div class="card p-5">
    <h2 class="mb-2 text-lg font-bold text-ink">{{ $t('today.practice') }}</h2>
    <div class="flex flex-col">
      <RouterLink
        v-for="link in LINKS"
        :key="link.title"
        :to="link.to"
        class="group -mx-2 flex items-center gap-3 rounded-2xl px-2 py-2.5 transition hover:bg-surface-2"
      >
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
          <Icon :name="link.icon" class="h-5 w-5" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-semibold text-ink">{{ $t(link.title) }}</span>
          <span class="block truncate text-xs text-ink-muted">{{ $t(link.sub) }}</span>
        </span>
        <Icon name="chevronRight" class="h-4 w-4 text-slate-400 transition group-hover:translate-x-0.5" />
      </RouterLink>
    </div>
  </div>
</template>
