<script setup>
/**
 * Zinvest Copilot — the AI does a small business's finance work in five steps:
 * reads income and expenses from the owner's own words, analyses them, warns
 * when the money will run out, picks a bank loan and writes a business plan.
 *
 * Each step's AI work comes back as a proposal; the ApprovalPanel under it
 * asks "Approve?" and only "Yes" changes the business's data. Everything the
 * AI did is listed on the history page (views/CopilotHistory).
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import ActionResult from '@/components/copilot/ActionResult.vue'
import ApprovalPanel from '@/components/copilot/ApprovalPanel.vue'
import AiAvatar from '@/components/ai/AiAvatar.vue'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
import {
  findLoan,
  getCopilotState,
  readEntries,
  runAnalysis,
  runRunway,
  saveCopilotSettings,
  writePlan,
} from '@/api/copilot'
import { monthLabel, monthRange, money } from '@/utils/format'

const { t, locale } = useI18n()

const state = ref(null)
const loading = ref(true)
const quota = ref(null)
const busy = ref('') // which step the AI is working on
const errors = reactive({})
const shown = reactive({}) // kind -> the proposal (or decision) shown under that step

const text = ref('')
const cash = ref('')
const form = ref('business')
const savingSettings = ref(false)
const settingsSaved = ref(false)
const loanForm = reactive({ amount: '50000000', months: 24, purpose: 'working_capital' })

const currency = computed(() => state.value?.currency || 'UZS')
const fmt = (v) => money(v, currency.value)
// Same grouping as money() (the browser's own number format).
const num = (v) => new Intl.NumberFormat().format(Number(v) || 0)
// Big sums are hard to read as typed ("50000000"): show them formatted under the field.
const amountHint = (v) => (v === '' || v == null || !Number.isFinite(Number(v)) ? '' : fmt(v))
const summary = computed(() => state.value?.summary || null)

// The months the averages come from: "July – September 2026" when they run
// one after another, else each month named ("Jul 2026, Sep 2026").
const ym = /^\d{4}-\d{2}$/
const monthIndex = (m) => Number(m.slice(0, 4)) * 12 + Number(m.slice(5, 7))
const basedOnMonths = computed(() => {
  const all = summary.value?.months || []
  const ms = all.filter((m) => ym.test(m)).sort()
  if (ms.length !== all.length || !ms.length) return all.join(', ')
  if (ms.length === 1) return monthLabel(ms[0], locale.value)
  const contiguous = ms.every((m, i) => i === 0 || monthIndex(m) - monthIndex(ms[i - 1]) === 1)
  if (contiguous) return monthRange(ms[0], ms.at(-1), locale.value)
  return ms.map((m) => monthLabel(m, locale.value, 'short')).join(', ')
})

async function load() {
  try {
    state.value = await getCopilotState()
    if (state.value.cash != null) cash.value = state.value.cash
    form.value = state.value.business_form || 'business'
    for (const a of state.value.pending) if (!shown[a.kind]) shown[a.kind] = a
  } catch (e) {
    errors.page = e?.response?.data?.detail || t('errors.generic')
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function saveSettings() {
  savingSettings.value = true
  errors.settings = ''
  try {
    await saveCopilotSettings({ cash: cash.value === '' ? 0 : cash.value, business_form: form.value })
    settingsSaved.value = true
    setTimeout(() => (settingsSaved.value = false), 2000)
    await load()
  } catch (e) {
    errors.settings = e?.response?.data?.detail || t('errors.generic')
  } finally {
    savingSettings.value = false
  }
}

async function run(kind, call) {
  if (busy.value) return
  busy.value = kind
  errors[kind] = ''
  try {
    const res = await call()
    shown[kind] = res.action
    quota.value = res.quota || quota.value
  } catch (e) {
    errors[kind] = e?.response?.data?.detail || t('errors.generic')
  } finally {
    busy.value = ''
  }
}

// `blocked` names what has to happen first, shown under a step that cannot run yet.
const steps = computed(() => {
  const noData = !summary.value?.has_data
  const noCash = state.value?.cash == null
  return [
    { kind: 'entries', n: 1, icon: 'note', run: () => run('entries', () => readEntries(text.value, locale.value)), disabled: !text.value.trim() },
    { kind: 'analysis', n: 2, icon: 'chart', run: () => run('analysis', () => runAnalysis(locale.value)), disabled: noData, blocked: noData ? 'noFigures' : '' },
    { kind: 'runway', n: 3, icon: 'alert', run: () => run('runway', () => runRunway(locale.value)), disabled: noData || noCash, blocked: noCash ? 'needCash' : noData ? 'noFigures' : '' },
    { kind: 'loan', n: 4, icon: 'store', run: () => run('loan', () => findLoan({ ...loanForm, language: locale.value })), disabled: !loanForm.amount || !loanForm.months },
    { kind: 'plan', n: 5, icon: 'book', run: () => run('plan', () => writePlan(locale.value)), disabled: noData, blocked: noData ? 'noFigures' : '' },
  ]
})
const TITLE = { entries: 'step1', analysis: 'step2', runway: 'step3', loan: 'step4', plan: 'step5' }

async function decided(kind, action) {
  shown[kind] = action
  await load()
}
</script>

<template>
  <div class="mx-auto max-w-4xl">
    <div class="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div class="flex items-start gap-3">
        <AiAvatar class="h-12 w-12 shrink-0" />
        <div class="min-w-0">
          <h1 class="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">{{ $t('copilot.title') }}</h1>
          <p class="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">{{ $t('copilot.subtitle') }}</p>
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <PillBadge
          v-if="quota"
          color="brand"
          variant="soft"
          icon="coin"
          size="sm"
          class="tabular-nums"
          role="status"
          :title="$t('copilot.quota', { left: num(quota.remaining), limit: num(quota.limit) })"
          :aria-label="$t('copilot.quota', { left: num(quota.remaining), limit: num(quota.limit) })"
        >{{ num(quota.remaining) }} / {{ num(quota.limit) }}</PillBadge>
        <RouterLink :to="{ name: 'copilotHistory' }" class="flex min-h-11 items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 text-sm font-semibold text-brand-600 hover:border-brand-300 dark:border-hairline dark:bg-surface dark:text-brand-300 dark:hover:border-brand-500/50">
          <Icon name="history" class="h-4 w-4 shrink-0" />{{ $t('copilot.history') }}
        </RouterLink>
      </div>
    </div>

    <p v-if="errors.page" role="alert" class="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-300">{{ errors.page }}</p>
    <LoadingSkeleton v-if="loading" height="h-64" rounded="rounded-2xl" role="status" :aria-label="$t('common.loading')" />

    <template v-else-if="state">
      <!-- The month in numbers, and the owner's own inputs -->
      <section class="card mb-5 p-5">
        <div v-if="summary?.has_data" class="grid gap-3 sm:grid-cols-3">
          <div class="min-w-0 rounded-2xl bg-emerald-50 px-4 py-3 dark:bg-emerald-500/10"><p class="text-xs font-semibold text-emerald-700 dark:text-emerald-300">{{ $t('copilot.monthlyIncome') }}</p><p class="text-lg font-extrabold tabular-nums text-emerald-800 wrap-anywhere xl:text-xl dark:text-emerald-200">{{ fmt(summary.revenue) }}</p></div>
          <div class="min-w-0 rounded-2xl bg-red-50 px-4 py-3 dark:bg-red-500/10"><p class="text-xs font-semibold text-red-700 dark:text-red-300">{{ $t('copilot.monthlyExpenses') }}</p><p class="text-lg font-extrabold tabular-nums text-red-800 wrap-anywhere xl:text-xl dark:text-red-200">{{ fmt(summary.expenses) }}</p></div>
          <div class="min-w-0 rounded-2xl bg-slate-50 px-4 py-3 dark:bg-surface-2"><p class="text-xs font-semibold text-slate-500 dark:text-slate-400">{{ $t('copilot.monthlyNet') }}</p><p class="text-lg font-extrabold tabular-nums wrap-anywhere xl:text-xl" :class="Number(summary.net) < 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'">{{ fmt(summary.net) }}</p></div>
        </div>
        <p v-if="summary?.has_data" class="mt-2 text-xs text-slate-400">{{ $t('copilot.basedOn', { months: basedOnMonths }) }}</p>
        <p v-else class="text-sm text-slate-500 dark:text-slate-400">{{ $t('copilot.noFigures') }}</p>
        <!-- On wide screens the formatted cash sits in a second row under its
             field, so the field, the select and the button stay bottom-aligned. -->
        <form class="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end sm:gap-y-1" @submit.prevent="saveSettings">
          <label class="block text-xs font-semibold text-slate-500 sm:row-start-1 dark:text-slate-400">{{ $t('copilot.cashNow') }} ({{ currency }})
            <input v-model="cash" type="number" min="0" step="1" inputmode="numeric" class="zx-input mt-1 h-11 w-full py-2 text-sm font-normal tabular-nums" placeholder="0" aria-describedby="copilot-cash-hint" />
          </label>
          <p id="copilot-cash-hint" class="-mt-2 min-h-4 text-xs tabular-nums text-slate-500 sm:col-start-1 sm:row-start-2 sm:mt-0 dark:text-slate-400" aria-live="polite">{{ amountHint(cash) || $t('copilot.cashHint') }}</p>
          <label class="block text-xs font-semibold text-slate-500 sm:row-start-1 dark:text-slate-400">{{ $t('copilot.form') }}
            <select v-model="form" class="zx-input mt-1 h-11 w-full py-2 text-sm font-normal">
              <option value="business">{{ $t('copilot.form_business') }}</option>
              <option value="person">{{ $t('copilot.form_person') }}</option>
            </select>
          </label>
          <button type="submit" :disabled="savingSettings" :aria-busy="savingSettings" class="pill min-h-11 justify-center bg-slate-900 px-5 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50 sm:row-start-1 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-200">
            <Icon v-if="settingsSaved" name="check" class="h-4 w-4" />{{ savingSettings ? $t('settings.saving') : settingsSaved ? $t('copilot.saved') : $t('common.save') }}
          </button>
        </form>
        <p v-if="errors.settings" role="alert" class="mt-2 text-sm text-red-600 dark:text-red-300">{{ errors.settings }}</p>
      </section>

      <!-- The five steps -->
      <ol class="space-y-5">
        <li v-for="s in steps" :key="s.kind" class="card p-5" :data-step="s.kind">
          <div class="flex items-start gap-3">
            <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300" aria-hidden="true"><Icon :name="s.icon" class="h-5 w-5" /></span>
            <div class="min-w-0 flex-1">
              <p class="text-[11px] font-extrabold uppercase tracking-widest text-brand-600 dark:text-brand-300">{{ $t('copilot.step', { n: s.n }) }}</p>
              <h2 :id="`copilot-step-${s.kind}`" class="text-lg font-extrabold text-slate-900 dark:text-white">{{ $t(`copilot.${TITLE[s.kind]}Title`) }}</h2>
              <p class="text-sm text-slate-500 dark:text-slate-400">{{ $t(`copilot.${TITLE[s.kind]}Hint`) }}</p>
            </div>
          </div>

          <textarea v-if="s.kind === 'entries'" v-model="text" rows="4" maxlength="4000" :placeholder="$t('copilot.step1Placeholder')" :aria-label="$t('copilot.step1Title')" class="zx-input mt-4 w-full resize-y py-2 text-sm" />
          <p v-if="s.blocked" class="mt-3 text-sm text-amber-700 dark:text-amber-300">{{ $t(`copilot.${s.blocked}`) }}</p>
          <div v-if="s.kind === 'loan'" class="mt-4 grid gap-3 sm:grid-cols-3">
            <div>
              <label class="block text-xs font-semibold text-slate-500 dark:text-slate-400">{{ $t('copilot.amount') }} ({{ currency }})<input v-model="loanForm.amount" type="number" min="1000000" step="1000000" inputmode="numeric" class="zx-input mt-1 h-11 w-full py-2 text-sm font-normal tabular-nums" aria-describedby="copilot-loan-hint" /></label>
              <p id="copilot-loan-hint" class="mt-1 min-h-4 text-xs tabular-nums text-slate-500 dark:text-slate-400" aria-live="polite">{{ amountHint(loanForm.amount) }}</p>
            </div>
            <label class="block text-xs font-semibold text-slate-500 dark:text-slate-400">{{ $t('copilot.months') }}<input v-model.number="loanForm.months" type="number" min="3" max="120" inputmode="numeric" class="zx-input mt-1 h-11 w-full py-2 text-sm font-normal tabular-nums" /></label>
            <label class="block text-xs font-semibold text-slate-500 dark:text-slate-400">{{ $t('copilot.purpose') }}
              <select v-model="loanForm.purpose" class="zx-input mt-1 h-11 w-full py-2 text-sm font-normal">
                <option v-for="o in ['working_capital', 'equipment', 'any']" :key="o" :value="o">{{ $t(`copilot.purpose_${o}`) }}</option>
              </select>
            </label>
          </div>

          <button
            type="button"
            :disabled="!!busy || s.disabled"
            :aria-busy="busy === s.kind"
            class="pill mt-4 flex min-h-11 items-center justify-center gap-2 bg-brand-600 px-5 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-brand-600 aria-busy:cursor-wait aria-busy:opacity-100"
            :data-run="s.kind"
            @click="s.run()"
          >
            <Icon :name="busy === s.kind ? 'refresh' : 'sparkles'" class="h-4 w-4 shrink-0" :class="busy === s.kind ? 'animate-spin' : ''" />{{ $t(`copilot.${TITLE[s.kind]}Run`) }}
          </button>
          <p v-if="busy === s.kind" class="mt-3 flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400" role="status"><AiAvatar thinking class="h-7 w-7" />{{ $t('copilot.working') }}</p>
          <p v-if="errors[s.kind]" role="alert" class="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-300">{{ errors[s.kind] }}</p>

          <!-- This step's proposal (or decision) -->
          <div v-if="shown[s.kind]" class="mt-4 border-t border-slate-100 pt-4 dark:border-hairline">
            <ActionResult :kind="s.kind" :payload="shown[s.kind].payload" :currency="currency" />
            <ApprovalPanel :action="shown[s.kind]" :labelledby="`copilot-step-${s.kind}`" @decided="decided(s.kind, $event)" />
          </div>
          <!-- …or what was approved before -->
          <div v-else-if="state.approved?.[s.kind]" class="mt-4 border-t border-slate-100 pt-4 dark:border-hairline">
            <p class="mb-2 text-xs font-bold text-emerald-700 dark:text-emerald-300"><span aria-hidden="true">✅ </span>{{ $t('copilot.approved') }}</p>
            <ActionResult :kind="s.kind" :payload="state.approved[s.kind]" :currency="currency" />
          </div>
        </li>
      </ol>
    </template>
  </div>
</template>
