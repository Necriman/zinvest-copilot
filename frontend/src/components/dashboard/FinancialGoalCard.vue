<script setup>
/**
 * Financial goal — parked as "coming soon".
 *
 * The card previously edited `target_score` (a unit-test percentage) under a
 * "financial goal" heading, which measured the wrong thing. It's muted here
 * until real goal tracking exists; the backend field and PATCH endpoint are
 * left untouched so this can be switched back on without a migration.
 */
import Icon from '@/components/ui/Icon.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
</script>

<template>
  <div class="card relative overflow-hidden p-5">
    <div class="flex items-center justify-between gap-2">
      <span class="flex items-center gap-2 text-sm font-semibold text-slate-500 dark:text-slate-400">
        <Icon name="target" class="h-4 w-4" />
        {{ $t('dashboard.financialGoal') }}
      </span>
      <PillBadge color="slate" size="sm">{{ $t('common.comingSoon') }}</PillBadge>
    </div>

    <p class="mt-3 text-sm text-slate-400">{{ $t('dashboard.goalComingSoon') }}</p>
  </div>
</template>
