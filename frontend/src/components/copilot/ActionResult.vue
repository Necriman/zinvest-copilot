<script setup>
/**
 * What one piece of Copilot work produced, for any of the five kinds: the
 * records read from text, the analysis, the cash warning, the chosen loan
 * (with everything compared) and the business plan with its forecast. Used on
 * the Copilot page and in the history (where `print` keeps everything open).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import Icon from '@/components/ui/Icon.vue'
import { isNumeric, money, monthLabel } from '@/utils/format'

const props = defineProps({
  kind: { type: String, required: true },
  payload: { type: Object, required: true },
  currency: { type: String, default: 'UZS' },
})
const { locale } = useI18n()
const fmt = (v) => money(v, props.currency)
// The plan's sums are text the AI wrote: "60000000" reads as money, anything else as written.
const sum = (v) => (isNumeric(v) ? fmt(v) : v)
// "2026-12" -> "December 2026" / "Dec 2026"; free text stays as written.
const month = (v, style = 'long') => monthLabel(v, locale.value, style)
const rate = (o) => (o.rate_min === o.rate_max ? o.rate_max : `${o.rate_min}–${o.rate_max}`)
const p = computed(() => props.payload || {})
// White text on these keeps at least 4.5:1 (the -500/-600 shades did not).
const HEALTH = { strong: 'bg-emerald-700', stable: 'bg-sky-700', watch: 'bg-amber-700', risk: 'bg-red-600' }
const RUNWAY = { critical: 'border-red-300 bg-red-50 text-red-900 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-100', warning: 'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-100', ok: 'border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-500/40 dark:bg-emerald-500/10 dark:text-emerald-100' }
const sections = ['executive_summary', 'problem', 'solution', 'customers', 'competition', 'operations', 'team']
const LABEL = 'mb-1 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400'
</script>

<template>
  <div class="break-words text-sm text-slate-700 dark:text-slate-200">
    <!-- Records read from the owner's text -->
    <template v-if="kind === 'entries'">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[28rem] text-left">
          <thead class="text-xs text-slate-500 dark:text-slate-400">
            <tr>
              <th scope="col" class="py-1.5 pr-2 font-semibold">{{ $t('copilot.month') }}</th>
              <th scope="col" class="pr-2"><span class="sr-only">{{ $t('copilot.colType') }}</span></th>
              <th scope="col" class="pr-2"><span class="sr-only">{{ $t('copilot.colCategory') }}</span></th>
              <th scope="col" class="pr-2 text-right font-semibold">{{ $t('copilot.amount') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(e, i) in p.entries" :key="i" class="border-t border-slate-100 dark:border-hairline">
              <td class="whitespace-nowrap py-1.5 pr-2 tabular-nums text-slate-500 dark:text-slate-400">{{ month(e.month, 'short') }}</td>
              <td class="pr-2"><span class="whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-bold" :class="e.type === 'revenue' ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300' : 'bg-red-50 text-red-700 dark:bg-red-500/15 dark:text-red-300'">{{ $t(`copilot.type_${e.type}`) }}</span></td>
              <td class="pr-2">{{ e.category }}<span v-if="e.type === 'spending'" class="ml-1 text-xs text-slate-400">· {{ $t(`copilot.cost_${e.cost_type}`) }}</span></td>
              <td class="whitespace-nowrap pl-2 text-right font-semibold tabular-nums">{{ fmt(e.amount) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="p.unclear?.length" class="mt-2 text-xs text-amber-700 dark:text-amber-300">{{ $t('copilot.unclear') }}: {{ p.unclear.join('; ') }}</p>
    </template>

    <!-- Analysis -->
    <template v-else-if="kind === 'analysis'">
      <p class="flex flex-wrap items-center gap-2">
        <span class="rounded-full px-2.5 py-0.5 text-xs font-bold text-white" :class="HEALTH[p.health] || HEALTH.stable">{{ $t(`copilot.health_${p.health || 'stable'}`) }}</span>
        <span class="min-w-0 font-bold text-slate-900 dark:text-white">{{ p.headline }}</span>
      </p>
      <div class="mt-3 grid gap-4 md:grid-cols-2">
        <div v-if="p.findings?.length" class="min-w-0">
          <p :class="LABEL">{{ $t('copilot.findings') }}</p>
          <ul class="space-y-1.5"><li v-for="(f, i) in p.findings" :key="i"><span class="font-semibold">{{ f.title }}.</span> {{ f.detail }}</li></ul>
        </div>
        <div v-if="p.actions?.length" class="min-w-0">
          <p :class="LABEL">{{ $t('copilot.actionsTitle') }}</p>
          <ol class="list-decimal space-y-1.5 pl-5"><li v-for="(a, i) in p.actions" :key="i"><span class="font-semibold">{{ a.title }}</span> — {{ a.why }}</li></ol>
        </div>
      </div>
    </template>

    <!-- Cash runway -->
    <template v-else-if="kind === 'runway'">
      <div class="rounded-2xl border-2 p-4" :class="RUNWAY[p.forecast?.status] || RUNWAY.ok">
        <p class="flex items-start gap-2 text-lg font-extrabold leading-snug">
          <Icon :name="p.forecast?.months ? 'alert' : 'checkCircle'" class="mt-1 h-5 w-5 shrink-0" />
          <span v-if="p.forecast?.months" class="min-w-0">{{ $t('copilot.runsOut', { months: p.forecast.months, date: month(p.forecast.runs_out) }, Number(p.forecast.months) || 2) }}</span>
          <span v-else class="min-w-0">{{ $t('copilot.safe') }}</span>
        </p>
        <p v-if="p.forecast?.months" class="mt-1 text-sm opacity-90">{{ $t('copilot.burnLine', { burn: fmt(p.forecast.burn), cash: fmt(p.forecast.cash) }) }}</p>
      </div>
      <p v-if="p.message" class="mt-3">{{ p.message }}</p>
      <div v-if="p.actions?.length" class="mt-3">
        <p :class="LABEL">{{ $t('copilot.actionsTitle') }}</p>
        <ol class="list-decimal space-y-1.5 pl-5"><li v-for="(a, i) in p.actions" :key="i"><span class="font-semibold">{{ a.title }}</span> — {{ a.impact }}</li></ol>
      </div>
    </template>

    <!-- Loan -->
    <template v-else-if="kind === 'loan' && p.chosen">
      <div class="rounded-2xl border-2 border-brand-200 bg-brand-50/50 p-4 dark:border-brand-500/30 dark:bg-brand-500/10">
        <p class="text-xs font-bold uppercase tracking-wide text-brand-600 dark:text-brand-300">{{ p.chosen.bank }}</p>
        <p class="text-lg font-extrabold text-slate-900 dark:text-white">{{ p.chosen.product }}</p>
        <dl class="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-4">
          <div class="min-w-0"><dt class="text-xs text-slate-500 dark:text-slate-400">{{ $t('copilot.amount') }}</dt><dd class="font-semibold tabular-nums">{{ fmt(p.need?.amount) }}</dd></div>
          <div class="min-w-0"><dt class="text-xs text-slate-500 dark:text-slate-400">{{ $t('copilot.rate') }}</dt><dd class="font-semibold tabular-nums">{{ rate(p.chosen) }}%</dd></div>
          <div class="min-w-0"><dt class="text-xs text-slate-500 dark:text-slate-400">{{ $t('copilot.payment') }}</dt><dd class="font-semibold tabular-nums">{{ fmt(p.chosen.payment) }}</dd></div>
          <div class="min-w-0"><dt class="text-xs text-slate-500 dark:text-slate-400">{{ $t('copilot.totalInterest') }}</dt><dd class="font-semibold tabular-nums">{{ fmt(p.chosen.total_interest) }}</dd></div>
        </dl>
        <p v-if="p.chosen.payment_share != null" class="mt-2 text-xs" :class="p.chosen.affordable ? 'text-emerald-700 dark:text-emerald-300' : 'text-red-700 dark:text-red-300'">{{ $t('copilot.share', { share: p.chosen.payment_share }) }}</p>
        <a v-if="p.chosen.url" :href="p.chosen.url" target="_blank" rel="noopener noreferrer" class="-my-1 mt-1 inline-flex min-h-9 items-center gap-1 rounded-lg text-xs font-semibold text-brand-600 underline underline-offset-2 hover:text-brand-700 dark:text-brand-300 dark:hover:text-brand-200">
          {{ $t('copilot.openBank') }} <Icon name="arrowRight" class="h-3 w-3 shrink-0" /><span class="sr-only">({{ $t('copilot.newTab') }})</span>
        </a>
      </div>
      <p v-if="p.why" class="mt-3"><span class="font-semibold">{{ $t('copilot.why') }}:</span> {{ p.why }}</p>
      <div class="mt-3 grid gap-4 md:grid-cols-2">
        <div v-if="p.steps?.length" class="min-w-0"><p :class="LABEL">{{ $t('copilot.steps') }}</p><ol class="list-decimal space-y-1 pl-5"><li v-for="(s, i) in p.steps" :key="i">{{ s }}</li></ol></div>
        <div v-if="p.watch_out?.length" class="min-w-0"><p :class="LABEL">{{ $t('copilot.watchOut') }}</p><ul class="list-disc space-y-1 pl-5"><li v-for="(s, i) in p.watch_out" :key="i">{{ s }}</li></ul></div>
      </div>
      <details v-if="p.options?.length" class="mt-3">
        <summary class="cursor-pointer rounded-lg py-1.5 text-xs font-semibold text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200">{{ $t('copilot.otherOptions') }} ({{ p.options.length }})</summary>
        <div class="mt-1 overflow-x-auto">
          <table class="w-full min-w-[34rem] text-left text-xs">
            <thead class="sr-only">
              <tr>
                <th scope="col">{{ $t('copilot.colBank') }}</th>
                <th scope="col">{{ $t('copilot.colLoan') }}</th>
                <th scope="col">{{ $t('copilot.rate') }}</th>
                <th scope="col">{{ $t('copilot.payment') }}</th>
                <th scope="col">{{ $t('copilot.colNote') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="o in p.options" :key="o.id" class="border-t border-slate-100 dark:border-hairline" :class="o.eligible ? '' : 'text-slate-400'">
                <td class="py-1.5 pr-2 font-semibold">{{ o.bank }}</td>
                <td class="pr-2">{{ o.product }}</td>
                <td class="whitespace-nowrap pr-2 tabular-nums">{{ rate(o) }}%</td>
                <td class="whitespace-nowrap pr-2 tabular-nums">{{ o.eligible ? fmt(o.payment) : '' }}</td>
                <td>{{ o.eligible ? '' : `${$t('copilot.notEligible')}: ${(o.reasons || []).map((r) => $t(`copilot.reason_${r}`)).join(', ')}` }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
      <p class="mt-2 text-[11px] text-slate-400">{{ $t('copilot.indicative', { date: month(p.checked) }) }}</p>
    </template>

    <!-- Business plan -->
    <template v-else-if="kind === 'plan'">
      <p class="text-lg font-extrabold text-slate-900 dark:text-white">{{ p.title }}</p>
      <div class="mt-2 space-y-2">
        <p v-for="s in sections.filter((s) => p[s])" :key="s"><span class="font-semibold">{{ $t(`copilot.sec_${s}`) }}:</span> {{ p[s] }}</p>
      </div>
      <div v-if="p.marketing?.length" class="mt-3">
        <p :class="LABEL">{{ $t('copilot.sec_marketing') }}</p>
        <ul class="list-disc space-y-1 pl-5"><li v-for="(m, i) in p.marketing" :key="i"><span class="font-semibold">{{ m.channel }}:</span> {{ m.action }}<span v-if="m.monthly_budget && m.monthly_budget !== '0'" class="whitespace-nowrap tabular-nums text-slate-500 dark:text-slate-400"> · {{ sum(m.monthly_budget) }}</span></li></ul>
      </div>
      <div v-if="p.milestones?.length" class="mt-3">
        <p :class="LABEL">{{ $t('copilot.sec_milestones') }}</p>
        <ul class="space-y-1"><li v-for="(m, i) in p.milestones" :key="i"><span class="font-semibold text-slate-500 dark:text-slate-400">{{ month(m.month) }}</span> — {{ m.goal }}</li></ul>
      </div>
      <div v-if="p.funding?.use?.length || (p.funding?.need && p.funding.need !== '0')" class="mt-3">
        <p :class="LABEL">{{ $t('copilot.sec_funding') }}<span v-if="p.funding.need && p.funding.need !== '0'" class="normal-case tracking-normal">: <span class="tabular-nums">{{ sum(p.funding.need) }}</span></span></p>
        <ul class="list-disc space-y-1 pl-5"><li v-for="(u, i) in p.funding.use" :key="i">{{ u.item }}<span v-if="u.amount" class="whitespace-nowrap tabular-nums"> — {{ sum(u.amount) }}</span></li></ul>
      </div>
      <div v-if="p.risks?.length" class="mt-3">
        <p :class="LABEL">{{ $t('copilot.sec_risks') }}</p>
        <ul class="list-disc space-y-1 pl-5"><li v-for="(r, i) in p.risks" :key="i"><span class="font-semibold">{{ r.risk }}</span> — {{ r.mitigation }}</li></ul>
      </div>
      <div v-if="p.forecast?.length" class="mt-4">
        <p :class="LABEL">{{ $t('copilot.forecast') }}</p>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[34rem] text-right text-xs tabular-nums">
            <thead class="text-slate-500 dark:text-slate-400">
              <tr>
                <th scope="col" class="py-1 pr-2 text-left font-semibold">{{ $t('copilot.month') }}</th>
                <th scope="col" class="pl-3 font-semibold">{{ $t('copilot.revenue') }}</th>
                <th scope="col" class="pl-3 font-semibold">{{ $t('copilot.expenses') }}</th>
                <th scope="col" class="pl-3 font-semibold">{{ $t('copilot.profit') }}</th>
                <th scope="col" class="pl-3 font-semibold">{{ $t('copilot.cumulative') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in p.forecast" :key="r.month" class="border-t border-slate-100 dark:border-hairline">
                <th scope="row" class="whitespace-nowrap py-1 pr-2 text-left font-normal">{{ month(r.month, 'short') }}</th>
                <td class="whitespace-nowrap pl-3">{{ fmt(r.revenue) }}</td>
                <td class="whitespace-nowrap pl-3">{{ fmt(r.expenses) }}</td>
                <td class="whitespace-nowrap pl-3" :class="Number(r.profit) < 0 ? 'text-red-600 dark:text-red-400' : 'text-emerald-700 dark:text-emerald-300'">{{ fmt(r.profit) }}</td>
                <td class="whitespace-nowrap pl-3" :class="Number(r.cumulative) < 0 ? 'text-red-600 dark:text-red-400' : ''">{{ fmt(r.cumulative) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="mt-1 text-[11px] text-slate-400">{{ $t('copilot.assumptions', { g: parseFloat(p.assumptions?.revenue_growth_per_month) || 0, cg: parseFloat(p.assumptions?.variable_cost_growth_per_month) || 0 }) }}</p>
      </div>
    </template>
  </div>
</template>
