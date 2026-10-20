<script setup>
// Every founder's workspace: where they launch, how far along, and what the
// intake's market check said. A row opens the answers and the full check.
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import AdminCard from '@/components/admin/AdminCard.vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminModal from '@/components/admin/AdminModal.vue'
import AdminPager from '@/components/admin/AdminPager.vue'
import AdminStat from '@/components/admin/AdminStat.vue'
import AdminTable from '@/components/admin/AdminTable.vue'
import MarketResearch from '@/components/startup/MarketResearch.vue'
import InlineLoader from '@/components/ui/InlineLoader.vue'
import SearchField from '@/components/ui/SearchField.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'

const { t } = useI18n()
const admin = useAdmin()
const fmt = useAdminFormat()

const VERDICTS = ['strong', 'promising', 'uncertain', 'weak']
const q = ref('')
const verdict = ref('')
const state = reactive({ rows: [], page: 1, pages: 1, total: 0, summary: null, loading: false, error: '' })

async function load() {
  state.loading = true
  state.error = ''
  try {
    const data = await admin.act(() => adminApi.startups({ q: q.value || undefined, verdict: verdict.value || undefined, page: state.page }))
    Object.assign(state, { rows: data.results, pages: data.pages, total: data.total, page: data.page, summary: data.summary })
  } catch (e) {
    state.error = admin.errorText(e, t)
  } finally {
    state.loading = false
  }
}

watch([q, verdict], () => {
  if (state.page !== 1) state.page = 1
  else load()
})
watch(() => state.page, (value, old) => value !== old && load())
load()

const s = computed(() => state.summary || {})
const columns = computed(() => [
  { key: 'name', label: t('admin.startups.name') },
  { key: 'location', label: t('admin.startups.location') },
  { key: 'stage', label: t('admin.startups.stage') },
  { key: 'verdict', label: t('admin.startups.verdict') },
  { key: 'updated_at', label: t('admin.startups.updated') },
])

// The answer codes (stage, market, team) read through the founder-side labels.
const label = (field, value) => (value ? t(`startup.intake.${field}.${value}`) : '—')

const open = ref(false)
const detail = ref(null)
const detailError = ref('')
async function show(row) {
  open.value = true
  detail.value = null
  detailError.value = ''
  try {
    detail.value = await admin.act(() => adminApi.startup(row.id))
  } catch (e) {
    detailError.value = admin.errorText(e, t)
  }
}
const ANSWERS = ['problem', 'description', 'alternatives', 'revenue_model']
</script>

<template>
  <div>
    <AdminHeader :title="$t('admin.startups.title')" :intro="$t('admin.startups.intro')" />

    <div class="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
      <AdminStat :label="$t('admin.startups.total')" icon="store" :loading="!state.summary" :value="fmt.num(s.total)" :hint="$t('admin.startups.week', { n: s.week ?? 0 })" />
      <AdminStat :label="$t('admin.startups.onboarded')" icon="checkCircle" tone="green" :loading="!state.summary" :value="fmt.num(s.onboarded)" />
      <AdminStat :label="$t('admin.startups.checked')" icon="search" tone="brand" :loading="!state.summary" :value="fmt.num(s.checked)" />
      <AdminStat :label="$t('admin.startups.public')" icon="globe" tone="slate" :loading="!state.summary" :value="fmt.num(s.public)" />
    </div>

    <AdminCard v-if="s.checked" :title="$t('admin.startups.verdicts')" class="mt-4">
      <div class="flex h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-surface-2" role="img" :aria-label="$t('admin.startups.verdicts')">
        <span v-for="v in VERDICTS" :key="v" class="as-bar" :data-verdict="v" :style="{ width: `${((s.verdicts?.[v] || 0) / s.checked) * 100}%` }" />
      </div>
      <ul class="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm">
        <li v-for="v in VERDICTS" :key="v" class="flex items-center gap-2">
          <span class="as-dot" :data-verdict="v" />
          {{ $t(`startup.research.verdict.${v}`) }} · <b class="tabular-nums">{{ s.verdicts?.[v] || 0 }}</b>
        </li>
      </ul>
    </AdminCard>

    <div class="mb-4 mt-6 flex flex-col gap-2 sm:flex-row">
      <SearchField v-model="q" :placeholder="$t('admin.startups.search')" class="sm:max-w-xs sm:flex-1" />
      <select v-model="verdict" class="zx-input w-auto py-2" :aria-label="$t('admin.startups.verdict')">
        <option value="">{{ $t('admin.startups.allVerdicts') }}</option>
        <option v-for="v in VERDICTS" :key="v" :value="v">{{ $t(`startup.research.verdict.${v}`) }}</option>
        <option value="none">{{ $t('admin.startups.notChecked') }}</option>
      </select>
    </div>

    <p v-if="state.error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ state.error }}</p>

    <AdminTable :columns="columns" :rows="state.rows" :loading="state.loading" clickable :empty="$t('admin.startups.empty')" @open="show">
      <template #cell-name="{ row }">
        <p class="font-semibold">{{ row.name || '—' }}</p>
        <p class="text-xs text-slate-500 dark:text-slate-400">{{ row.owner.email }}</p>
      </template>
      <template #cell-location="{ row }">{{ row.location || '—' }}</template>
      <template #cell-stage="{ row }">{{ label('stage', row.stage) }}</template>
      <template #cell-verdict="{ row }">
        <span v-if="row.verdict" class="as-pill" :data-verdict="row.verdict">{{ $t(`startup.research.verdict.${row.verdict}`) }}</span>
        <span v-else class="text-slate-500">—</span>
      </template>
      <template #cell-updated_at="{ row }">
        <span class="whitespace-nowrap text-slate-500">{{ fmt.dateTime(row.updated_at) }}</span>
      </template>
    </AdminTable>
    <AdminPager v-model:page="state.page" :pages="state.pages" :total="state.total" class="mt-4" />

    <AdminModal :open="open" wide :title="detail?.name || $t('admin.startups.title')" @close="open = false">
      <p v-if="detailError" class="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ detailError }}</p>
      <InlineLoader v-else-if="!detail" />
      <div v-else class="space-y-5">
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-600 dark:text-slate-300">
          <RouterLink :to="{ name: 'adminUser', params: { id: detail.owner.id } }" class="font-semibold text-brand-600 hover:underline">
            {{ detail.owner.name || detail.owner.email }}
          </RouterLink>
          <span>{{ detail.location || '—' }}</span>
          <span>{{ label('stage', detail.stage) }}</span>
          <span>{{ label('market', detail.market) }}</span>
          <span>{{ label('team', detail.team) }}</span>
        </div>

        <dl class="grid gap-3 sm:grid-cols-2">
          <div v-for="k in ANSWERS" :key="k" class="rounded-xl bg-slate-50 p-3 dark:bg-surface-2">
            <dt class="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{{ $t(`startup.intake.${k}.q`) }}</dt>
            <dd class="mt-1 whitespace-pre-wrap text-sm">{{ detail.answers?.[k] || '—' }}</dd>
          </div>
        </dl>

        <MarketResearch v-if="detail.research" :research="detail.research" :place="detail.location" />
        <p v-else class="whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300">{{ detail.analysis || $t('admin.startups.notChecked') }}</p>

        <p class="text-xs text-slate-500 dark:text-slate-400">
          {{ $t('admin.startups.counts', { e: detail.counts?.employees ?? 0, p: detail.counts?.products ?? 0, t: detail.counts?.todos ?? 0 }) }}
        </p>
      </div>
    </AdminModal>
  </div>
</template>

<style scoped>
.as-bar[data-verdict='strong'],
.as-dot[data-verdict='strong'] {
  background: #30a46c;
}
.as-bar[data-verdict='promising'],
.as-dot[data-verdict='promising'] {
  background: var(--brand-500);
}
.as-bar[data-verdict='uncertain'],
.as-dot[data-verdict='uncertain'] {
  background: #f5a524;
}
.as-bar[data-verdict='weak'],
.as-dot[data-verdict='weak'] {
  background: #e5484d;
}
.as-dot {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 50%;
}
.as-pill {
  display: inline-flex;
  padding: 0.15rem 0.6rem;
  border-radius: 99px;
  font-size: 0.75rem;
  font-weight: 700;
  white-space: nowrap;
  background: rgba(148, 163, 184, 0.16);
}
.as-pill[data-verdict='strong'] {
  color: #1a6b45;
}
.as-pill[data-verdict='promising'] {
  color: var(--brand-700);
}
.as-pill[data-verdict='uncertain'] {
  color: #8a5100;
}
.as-pill[data-verdict='weak'] {
  color: #a8232a;
}
:where(.dark) .as-pill[data-verdict='strong'] {
  color: #6fdba5;
}
:where(.dark) .as-pill[data-verdict='promising'] {
  color: var(--brand-300);
}
:where(.dark) .as-pill[data-verdict='uncertain'] {
  color: #fbbf24;
}
:where(.dark) .as-pill[data-verdict='weak'] {
  color: #ff9592;
}
</style>
