<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'
import { useStartup } from '@/composables/useStartup'
import { money } from '@/utils/format'

const { data: summary } = useStartup()
const currency = computed(() => summary.value?.currency || 'USD')
const hasEntries = computed(
  () => Number(summary.value?.revenue || 0) !== 0 || Number(summary.value?.spending || 0) !== 0,
)
</script>

<template>
  <div class="card @container p-5">
    <div class="mb-4 flex items-center gap-3">
      <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
        <Icon name="store" class="h-5 w-5" />
      </span>
      <div class="min-w-0 flex-1">
        <p class="truncate text-[11px] font-semibold uppercase tracking-wider text-ink-muted">{{ $t('dashboard.myStartup') }}</p>
        <h2 class="truncate text-lg font-bold leading-tight text-ink">{{ $t('dashboard.spendingFinances') }}</h2>
      </div>
      <RouterLink
        :to="{ name: 'myStartup' }"
        class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-brand-600 transition hover:bg-brand-50 dark:text-brand-300 dark:hover:bg-brand-500/15"
        :aria-label="$t('common.open')"
        :title="$t('common.open')"
      >
        <Icon name="arrowRight" class="h-4 w-4" />
      </RouterLink>
    </div>

    <dl class="grid grid-cols-3 gap-2 @sm:gap-3">
      <div class="min-w-0 rounded-2xl bg-mint/60 p-3 dark:bg-mint">
        <dt class="truncate text-xs font-medium text-ink-muted">{{ $t('dashboard.revenue') }}</dt>
        <dd class="mt-1 truncate text-base font-bold tabular-nums text-mint-ink @sm:text-lg">{{ money(summary?.revenue, currency) }}</dd>
      </div>
      <div class="min-w-0 rounded-2xl bg-red-50 p-3 dark:bg-red-500/10">
        <dt class="truncate text-xs font-medium text-ink-muted">{{ $t('dashboard.spending') }}</dt>
        <dd class="mt-1 truncate text-base font-bold tabular-nums text-red-700 @sm:text-lg dark:text-red-300">{{ money(summary?.spending, currency) }}</dd>
      </div>
      <div class="min-w-0 rounded-2xl bg-brand-50 p-3 dark:bg-brand-500/10">
        <dt class="truncate text-xs font-medium text-ink-muted">{{ $t('dashboard.net') }}</dt>
        <dd class="mt-1 truncate text-base font-bold tabular-nums text-brand-700 @sm:text-lg dark:text-brand-300">{{ money(summary?.net, currency) }}</dd>
      </div>
    </dl>

    <p v-if="!hasEntries" class="mt-4 text-center text-sm text-ink-muted">{{ $t('dashboard.noEntries') }}</p>
  </div>
</template>
