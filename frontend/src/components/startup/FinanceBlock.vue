<script setup>
/**
 * Monthly Finances block: income vs expense entries and their derived net (±).
 * Reuses the existing /startup/cashflow API and the CashFlow view's totals-tiles
 * + add-form + entry-list pattern, condensed into a workspace card.
 */
import { computed, reactive, ref, watch } from 'vue'

import Icon from '@/components/ui/Icon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import BlockCard from './BlockCard.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { addCashFlow, deleteCashFlow, listCashFlow } from '@/api/cashflow'
import { money } from '@/utils/format'

const today=new Date();const todayISO=[today.getFullYear(),String(today.getMonth()+1).padStart(2,'0'),String(today.getDate()).padStart(2,'0')].join('-')
const period=ref(todayISO.slice(0,7)),error=ref('')
let loadVersion=0
const { data, reload } = useAsyncData(async()=>{const version=++loadVersion;const result=await listCashFlow({period:period.value});if(version!==loadVersion)return data.value;return result})
watch(period,()=>{if(/^\d{4}-\d{2}$/.test(period.value))reload().catch(e=>error.value=e?.response?.data?.detail||e.message)})
const entries = computed(() => data.value?.entries || [])
const totals = computed(() => data.value?.totals || { revenue: '0', spending: '0', net: '0' })
const netPositive = computed(() => Number(totals.value.net) >= 0)

const form = reactive({ entry_type: 'revenue', category: '', amount: '', cost_type:'variable', occurred_on:todayISO })
const busy = ref(false)

async function add() {
  if (!form.amount || busy.value) return
  busy.value = true
  try {
    await addCashFlow({
      entry_type: form.entry_type,
      category: form.category || 'General',
      amount: form.amount,
      cost_type:form.cost_type,
      occurred_on:form.occurred_on,
    })
    form.category = ''
    form.amount = ''
    await reload()
  } catch(e){error.value=e?.response?.data?.detail||e.message} finally {
    busy.value = false
  }
}

async function remove(id) {
  try{await deleteCashFlow(id);await reload()}catch(e){error.value=e?.response?.data?.detail||e.message}
}
</script>

<template>
  <BlockCard
    icon="wallet"
    iconColor="text-emerald-600"
    iconBg="bg-emerald-50 dark:bg-emerald-500/15"
    :title="$t('startup.finance.title')"
    :subtitle="$t('startup.finance.subtitle')"
  >
    <!-- Totals -->
    <label class="mb-4 block text-sm">{{ $t('business.period') }}<input v-model="period" type="month" required class="zx-input mt-1 w-full" /></label>
    <p v-if="error" role="alert" class="mb-3 text-sm text-red-600">{{ error }}</p>
    <div class="mb-4 grid grid-cols-3 gap-2">
      <div class="min-w-0 rounded-2xl bg-mint/60 p-3 dark:bg-mint">
        <p class="truncate text-xs font-medium text-ink-muted">{{ $t('startup.finance.income') }}</p>
        <p class="mt-1 truncate text-base font-bold tabular-nums text-mint-ink">{{ money(totals.revenue) }}</p>
      </div>
      <div class="min-w-0 rounded-2xl bg-red-50 p-3 dark:bg-red-500/10">
        <p class="truncate text-xs font-medium text-ink-muted">{{ $t('startup.finance.expense') }}</p>
        <p class="mt-1 truncate text-base font-bold tabular-nums text-red-700 dark:text-red-300">{{ money(totals.spending) }}</p>
      </div>
      <div class="min-w-0 rounded-2xl p-3" :class="netPositive ? 'bg-brand-50 dark:bg-brand-500/10' : 'bg-amber-50 dark:bg-amber-500/10'">
        <p class="truncate text-xs font-medium text-ink-muted">{{ $t('startup.finance.net') }}</p>
        <p class="mt-1 truncate text-base font-bold tabular-nums" :class="netPositive ? 'text-brand-700 dark:text-brand-300' : 'text-amber-700 dark:text-amber-300'">
          {{ money(totals.net) }}
        </p>
      </div>
    </div>

    <!-- Add form -->
    <form class="mb-4 flex flex-wrap items-center gap-2 rounded-2xl bg-slate-50 p-3 dark:bg-surface-2" @submit.prevent="add">
      <select v-model="form.entry_type" class="zx-input py-2">
        <option value="revenue">{{ $t('startup.finance.income') }}</option>
        <option value="spending">{{ $t('startup.finance.expense') }}</option>
      </select>
      <input v-model="form.category" :placeholder="$t('startup.finance.categoryPlaceholder')" class="zx-input min-w-0 flex-1 py-2" />
      <input v-model="form.amount" type="number" min="0" step="0.01" :placeholder="$t('startup.finance.amountPlaceholder')" class="zx-input w-28 py-2" />
      <label class="w-full text-xs">{{ $t('business.date') }}<input v-model="form.occurred_on" type="date" required class="zx-input mt-1 w-full" /></label>
      <label v-if="form.entry_type==='spending'" class="w-full text-xs">{{ $t('business.costType') }}<select v-model="form.cost_type" class="zx-input mt-1 w-full"><option value="fixed">{{ $t('business.fixed') }}</option><option value="variable">{{ $t('business.variable') }}</option></select></label>
      <button type="submit" :disabled="busy || !form.amount" class="pill shrink-0 bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40">
        <Icon name="plus" class="h-4 w-4" /> {{ $t('common.add') }}
      </button>
    </form>

    <EmptyState v-if="!entries.length" bear="phone" :message="$t('startup.finance.empty')" />

    <ul v-else class="divide-y divide-slate-100 dark:divide-hairline">
      <li v-for="e in entries" :key="e.id" class="group flex items-center gap-3 py-2.5">
        <span
          class="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl"
          :class="e.entry_type === 'revenue' ? 'bg-green-50 text-green-600 dark:bg-green-500/15' : 'bg-red-50 text-red-600 dark:bg-red-500/15'"
        >
          <Icon :name="e.entry_type === 'revenue' ? 'trending' : 'wallet'" class="h-4 w-4" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-medium text-slate-800 dark:text-ink">{{ e.category }}</p>
          <p class="text-xs text-slate-400">{{ e.occurred_on }}<span v-if="e.entry_type==='spending'"> · {{ $t(`business.${e.cost_type||'variable'}`) }}</span></p>
        </div>
        <span class="shrink-0 text-sm font-bold tabular-nums" :class="e.entry_type === 'revenue' ? 'text-green-600' : 'text-red-600'">
          {{ e.entry_type === 'revenue' ? '+' : '−' }}{{ money(e.amount) }}
        </span>
        <button type="button" class="shrink-0 rounded-lg p-1.5 text-slate-300 opacity-0 transition hover:bg-slate-100 hover:text-red-500 group-hover:opacity-100 dark:hover:bg-surface-2" :title="$t('common.delete')" @click="remove(e.id)">
          <Icon name="x" class="h-3.5 w-3.5" />
        </button>
      </li>
    </ul>
  </BlockCard>
</template>
