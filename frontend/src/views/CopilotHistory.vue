<script setup>
/**
 * Everything the Copilot did for this business, newest first: when, what the
 * AI did, the owner's decision and what it changed, with the full result.
 * Downloads as CSV (from the server) or PDF (the browser's print to PDF; the
 * print layout shows only this report, with every entry expanded).
 * `?print=1` opens every entry, for automated exports.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import ActionResult from '@/components/copilot/ActionResult.vue'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import { downloadHistoryCsv, getCopilotHistory, getCopilotState } from '@/api/copilot'
import { getStartupProfile } from '@/api/startup'
import { dateTime } from '@/utils/format'

const { t, locale } = useI18n()
const route = useRoute()

const actions = ref([])
const currency = ref('UZS')
const company = ref('')
const loading = ref(true)
const error = ref('')
const csvBusy = ref(false)
const expanded = ref(!!route.query.print)

onMounted(async () => {
  try {
    const [h, s, p] = await Promise.all([getCopilotHistory(), getCopilotState(), getStartupProfile().catch(() => null)])
    actions.value = h.actions
    currency.value = s.currency || 'UZS'
    company.value = p?.name || ''
  } catch (e) {
    error.value = e?.response?.data?.detail || t('errors.generic')
  } finally {
    loading.value = false
  }
})

const when = (iso) => dateTime(iso, locale.value)
const today = computed(() => dateTime(new Date(), locale.value, 'long'))
// Newest first on screen; a report (print, export) reads in the order things happened.
const listed = computed(() => (expanded.value ? [...actions.value].reverse() : actions.value))
const outcomeText = (o) => t(`copilot.out_${o.type}`, { count: o.count ?? '', what: o.what ? t(`copilot.what_${o.what}`) : '' }, Number(o.count) || 0)
const BADGE = {
  approved: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300',
  rejected: 'bg-slate-100 text-slate-600 dark:bg-surface-2 dark:text-slate-300',
  pending: 'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
}
const ICON = { approved: '✅', rejected: '❌', pending: '⏳' }

async function csv() {
  if (csvBusy.value) return
  csvBusy.value = true
  error.value = ''
  try {
    const blob = await downloadHistoryCsv()
    const url = URL.createObjectURL(blob)
    const a = Object.assign(document.createElement('a'), { href: url, download: 'zinvest-copilot-history.csv' })
    a.click()
    // Revoked a moment later: revoking at once can cancel the download in Firefox/Safari.
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (e) {
    error.value = e?.response?.data?.detail || t('errors.generic')
  } finally {
    csvBusy.value = false
  }
}

// Printing opens every entry; the browser's dialog saves it as a PDF. The
// report always prints in the light theme: dark cards with light ink would
// come out as a black page (or white text on white paper).
let wasDark = false
const before = () => {
  expanded.value = true
  wasDark = document.documentElement.classList.contains('dark')
  if (wasDark) document.documentElement.classList.remove('dark')
}
const after = () => {
  expanded.value = !!route.query.print
  if (wasDark) document.documentElement.classList.add('dark')
  wasDark = false
}
onMounted(() => {
  window.addEventListener('beforeprint', before)
  window.addEventListener('afterprint', after)
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeprint', before)
  window.removeEventListener('afterprint', after)
  if (wasDark) document.documentElement.classList.add('dark')
})
function pdf() {
  expanded.value = true
  requestAnimationFrame(() => window.print())
}
</script>

<template>
  <div class="mx-auto max-w-4xl">
    <div class="no-print mb-3">
      <RouterLink :to="{ name: 'copilot' }" class="-ml-1 inline-flex min-h-11 items-center gap-1.5 rounded-lg px-1 text-sm font-semibold text-slate-500 hover:text-brand-600 dark:text-slate-400 dark:hover:text-brand-300">
        <Icon name="arrowLeft" class="h-4 w-4 shrink-0" />{{ $t('copilot.title') }}
      </RouterLink>
    </div>

    <div id="copilot-report">
      <div class="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div class="min-w-0">
          <p class="text-xs font-bold uppercase tracking-widest text-brand-600 dark:text-brand-300">{{ $t('copilot.title') }}</p>
          <h1 class="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">{{ $t('copilot.history') }}</h1>
          <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">{{ company ? $t('copilot.reportFor', { name: company }) + ' · ' : '' }}{{ $t('copilot.historyIntro') }}</p>
          <p class="print-only mt-1 text-xs text-slate-400">{{ $t('copilot.exported', { date: today }) }}</p>
        </div>
        <div v-if="!loading && actions.length" class="no-print flex flex-wrap gap-2">
          <button type="button" :disabled="csvBusy" :aria-busy="csvBusy" class="flex min-h-11 items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 text-sm font-semibold text-slate-700 hover:border-brand-300 disabled:cursor-wait disabled:opacity-60 dark:border-hairline dark:bg-surface dark:text-slate-200 dark:hover:border-brand-500/50" @click="csv">
            <Icon :name="csvBusy ? 'refresh' : 'download'" class="h-4 w-4 shrink-0" :class="csvBusy ? 'animate-spin' : ''" />{{ $t('copilot.csv') }}
          </button>
          <button type="button" class="pill min-h-11 bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-700" @click="pdf">
            <Icon name="download" class="h-4 w-4 shrink-0" />{{ $t('copilot.pdf') }}
          </button>
        </div>
      </div>

      <p v-if="error" role="alert" class="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>
      <LoadingSkeleton v-if="loading" height="h-64" rounded="rounded-2xl" role="status" :aria-label="$t('common.loading')" />
      <p v-else-if="!actions.length" class="card p-6 text-sm text-slate-500 dark:text-slate-400">{{ $t('copilot.emptyHistory') }}</p>

      <ol v-else class="space-y-3">
        <li v-for="a in listed" :key="a.id" class="card break-words p-4">
          <div class="flex flex-wrap items-start gap-x-3 gap-y-1 break-inside-avoid">
            <time :datetime="a.created_at" class="w-full shrink-0 text-xs font-bold tabular-nums text-slate-500 sm:w-28 sm:pt-0.5 sm:text-sm sm:text-slate-900 dark:text-slate-400 sm:dark:text-white">{{ when(a.created_at) }}</time>
            <div class="min-w-0 flex-1">
              <p class="font-bold text-slate-900 dark:text-white">{{ $t(`copilot.kind_${a.kind}`) }}</p>
              <p v-if="a.summary" class="text-sm text-slate-600 dark:text-slate-300">{{ a.summary }}</p>
            </div>
            <span class="shrink-0 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-bold" :class="BADGE[a.status]"><span aria-hidden="true">{{ ICON[a.status] }} </span>{{ $t(`copilot.${a.status}`) }}</span>
          </div>
          <p v-if="a.outcome?.length || a.decided_at" class="mt-1 text-xs text-slate-500 sm:pl-[7.75rem] dark:text-slate-400">
            {{ (a.outcome || []).map(outcomeText).join(' · ') }}<template v-if="a.decided_at">{{ a.outcome?.length ? ' · ' : '' }}{{ $t('copilot.decidedAt', { time: when(a.decided_at) }) }}</template>
          </p>
          <details class="mt-2 sm:pl-[7.75rem]" :open="expanded">
            <summary class="no-print cursor-pointer rounded-lg py-1.5 text-xs font-semibold text-brand-600 hover:text-brand-700 dark:text-brand-300 dark:hover:text-brand-200">{{ $t('roadmap.details') }}</summary>
            <div class="mt-2"><ActionResult :kind="a.kind" :payload="a.payload" :currency="currency" /></div>
          </details>
        </li>
      </ol>
    </div>
  </div>
</template>

<style>
.print-only { display: none; }
@media print {
  @page { margin: 14mm; }
  /* The app's top bar and rails hide themselves (print:hidden in DashboardLayout). */
  .app-main { padding: 0 !important; }
  .app-main > div { max-width: none; padding: 0; }
  .no-print { display: none !important; }
  .zx-skip { display: none !important; }
  .print-only { display: block; }
  #copilot-report .card { box-shadow: none; border: 1px solid #e2e8f0; }
  html, body { background: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
