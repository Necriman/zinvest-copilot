<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import BearSticker from '@/components/mascot/BearSticker.vue'
import InlineLoader from '@/components/ui/InlineLoader.vue'
import { getAIQuota } from '@/api/ai'
import { useAsyncData } from '@/composables/useAsyncData'

const { locale } = useI18n()
const { data, loading, error } = useAsyncData(getAIQuota)

const leftPercent = computed(() => (data.value?.limit ? Math.max(0, Math.min(100, Math.round((data.value.remaining / data.value.limit) * 100))) : 0))
const resetDate = computed(() => {
  const raw = data.value?.reset_date
  if (!raw) return ''
  const d = new Date(`${raw}T00:00:00`)
  return Number.isNaN(d.getTime()) ? raw : d.toLocaleDateString(locale.value, { day: 'numeric', month: 'long' })
})
</script>

<template>
  <section class="mx-auto max-w-2xl">
    <div class="flex items-center justify-between gap-4">
      <div>
        <h1 class="text-3xl font-extrabold">{{ $t('nav.plans') }}</h1>
        <p class="mt-3 text-slate-500">{{ $t('plan.intro') }}</p>
      </div>
      <BearSticker name="coin" float class="hidden h-28 w-28 shrink-0 sm:block" />
    </div>
    <InlineLoader v-if="loading" class="mt-6" />
    <p v-if="error" role="alert" class="mt-6 text-red-600">{{ error }}</p>
    <div v-if="data" class="card mt-6 p-6">
      <p class="text-xs font-bold uppercase tracking-wider text-brand-600">{{ $t('plan.current') }}</p>
      <h2 class="mt-2 text-2xl font-extrabold capitalize">{{ data.tier }}</h2>
      <div class="mt-6">
        <div class="flex items-baseline justify-between gap-3">
          <p class="font-semibold text-slate-700 dark:text-slate-200">{{ $t('plansPage.usage') }}</p>
          <p class="text-sm font-bold text-brand-700 dark:text-brand-300">{{ $t('plansPage.left', { p: leftPercent }) }}</p>
        </div>
        <div class="mt-2 h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-surface-2" role="progressbar" :aria-valuenow="leftPercent" aria-valuemin="0" aria-valuemax="100" :aria-label="$t('plansPage.usage')">
          <div class="h-full rounded-full bg-brand-600" :style="{ width: leftPercent + '%' }" />
        </div>
        <p v-if="resetDate" class="mt-2 text-sm text-slate-500">{{ $t('plansPage.resets', { date: resetDate }) }}</p>
        <p v-if="data.bonus" class="mt-1 text-sm font-semibold text-emerald-700 dark:text-emerald-400">{{ $t('plansPage.bonus', { n: data.bonus.toLocaleString(locale) }) }}</p>
      </div>
      <p class="mt-5 rounded-xl bg-slate-50 p-3 text-sm text-slate-600 dark:bg-surface-2 dark:text-slate-300">{{ $t('plansPage.hint') }}</p>
    </div>
    <div class="mt-6 rounded-2xl border border-hairline p-6">
      <h2 class="font-bold">{{ $t('plan.pricing') }}</h2>
      <p class="mt-2 text-sm leading-relaxed text-slate-500">{{ $t('plan.pending') }}</p>
    </div>
  </section>
</template>
