<script setup>
import Icon from '@/components/ui/Icon.vue'

defineProps({ coins: { type: Number, default: 0 } })
</script>

<template>
  <div class="card flex items-center gap-4 p-5">
    <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 dark:bg-brand-500/15">
      <Icon name="coin" class="h-6 w-6 text-brand-600 dark:text-brand-400" />
    </div>
    <div>
      <p class="text-3xl font-extrabold leading-none text-brand-600 dark:text-brand-400">{{ coins }}</p>
      <p class="mt-1 text-xs text-slate-500">{{ $t('dashboard.coinsEarned') }}</p>
    </div>
  </div>
</template>
