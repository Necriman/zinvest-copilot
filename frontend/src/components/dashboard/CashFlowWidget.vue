<script setup>
import { RouterLink } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'
</script>

<template>
  <RouterLink
    :to="{ name: 'cashFlow' }"
    class="card group flex flex-col justify-between gap-4 bg-gradient-to-br from-white to-brand-50/50 p-5 transition hover:shadow-md dark:from-surface dark:to-brand-500/5"
  >
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span class="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-50 text-violet-600 dark:bg-violet-500/15">
          <Icon name="wallet" class="h-5 w-5" />
        </span>
        <div>
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-400">{{ $t('dashboard.cashFlowTitle') }}</p>
          <p class="font-bold text-slate-900 dark:text-white">{{ $t('dashboard.studioForecast') }}</p>
        </div>
      </div>
      <Icon name="arrowRight" class="h-5 w-5 text-slate-400 transition group-hover:translate-x-1" />
    </div>
    <p class="text-sm text-slate-500">{{ $t('dashboard.cashFlowDesc') }}</p>
  </RouterLink>
</template>
