<script setup>
// What the AI features cost and who uses them, with the allowances that cap it.
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AdminCard from '@/components/admin/AdminCard.vue'
import AdminChart from '@/components/admin/AdminChart.vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStat from '@/components/admin/AdminStat.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'

const { t, te } = useI18n()
const admin = useAdmin()
const fmt = useAdminFormat()

const days = ref(30)
const data = ref(null)
const error = ref('')

async function load() {
  error.value = ''
  try {
    data.value = await admin.act(() => adminApi.ai(days.value))
  } catch (e) {
    error.value = admin.errorText(e, t)
  }
}
watch(days, load, { immediate: true })

const daily = computed(() => (data.value?.daily || []).map((d) => ({ date: d.date, value: d.requests })))
const featureMax = computed(() => Math.max(1, ...(data.value?.by_feature || []).map((f) => f.tokens || 0)))
const featureLabel = (f) => (te(`admin.ai.feature.${f}`) ? t(`admin.ai.feature.${f}`) : f)
const usd = (n) => new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(n || 0)
</script>

<template>
  <div>
    <AdminHeader :title="$t('admin.ai.title')">
      <div class="inline-flex rounded-xl bg-slate-100 p-1 dark:bg-surface-2" role="radiogroup">
        <button
          v-for="d in [7, 30, 90]"
          :key="d"
          type="button"
          role="radio"
          :aria-checked="days === d"
          class="rounded-lg px-3 py-1.5 text-sm font-semibold tabular-nums transition"
          :class="days === d ? 'bg-white text-slate-900 shadow-sm dark:bg-surface dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200'"
          @click="days = d"
        >
          {{ $t('admin.common.days', { n: d }) }}
        </button>
      </div>
    </AdminHeader>

    <p v-if="error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>

    <div class="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
      <AdminStat :label="$t('admin.ai.requests')" icon="bot" :loading="!data" :value="fmt.num(data?.requests)" />
      <AdminStat :label="$t('admin.ai.tokens')" icon="zap" tone="amber" :loading="!data" :value="fmt.compact(data?.tokens)" />
      <AdminStat :label="$t('admin.ai.people')" icon="users" tone="green" :loading="!data" :value="fmt.num(data?.users)" />
      <AdminStat :label="$t('admin.ai.cost')" icon="coin" tone="slate" :loading="!data" :value="usd(data?.estimated_cost_usd)" :hint="$t('admin.ai.costHint')" />
    </div>

    <p v-if="data?.stub_requests" class="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:bg-amber-500/10 dark:text-amber-200">
      {{ $t('admin.ai.stub', { n: fmt.num(data.stub_requests) }) }}
    </p>

    <div class="mt-4">
      <AdminChart v-if="data" :title="$t('admin.ai.daily')" :points="daily" />
      <LoadingSkeleton v-else height="h-48" rounded="rounded-3xl" />
    </div>

    <div v-if="data" class="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <AdminCard :title="$t('admin.ai.byFeature')">
        <p v-if="!data.by_feature.length" class="text-sm text-slate-400">{{ $t('admin.common.empty') }}</p>
        <ul v-else class="space-y-3">
          <li v-for="f in data.by_feature" :key="f.feature" class="text-sm">
            <div class="flex justify-between gap-2">
              <span class="text-slate-700 dark:text-slate-200">{{ featureLabel(f.feature) }}</span>
              <span class="tabular-nums text-slate-500">{{ $t('admin.overview.requests', { n: fmt.num(f.requests) }) }} · {{ fmt.compact(f.tokens) }}</span>
            </div>
            <div class="mt-1.5 h-1.5 rounded-full bg-slate-100 dark:bg-surface-2">
              <div class="h-full rounded-full bg-brand-500" :style="{ width: `${((f.tokens || 0) / featureMax) * 100}%` }" />
            </div>
          </li>
        </ul>
      </AdminCard>

      <div class="grid content-start gap-4">
        <AdminCard :title="$t('admin.ai.topUsers')">
          <p v-if="!data.top_users.length" class="text-sm text-slate-400">{{ $t('admin.common.empty') }}</p>
          <ol v-else class="divide-y divide-slate-100 text-sm dark:divide-hairline">
            <li v-for="(u, i) in data.top_users" :key="u.id" class="flex items-center gap-3 py-2">
              <span class="w-5 shrink-0 text-right text-xs tabular-nums text-slate-400">{{ i + 1 }}</span>
              <RouterLink
                v-if="admin.can('users.view')"
                :to="{ name: 'adminUser', params: { id: u.id } }"
                class="min-w-0 flex-1 truncate text-slate-700 hover:underline dark:text-slate-200"
              >
                {{ u.email }}
              </RouterLink>
              <span v-else class="min-w-0 flex-1 truncate">{{ u.email }}</span>
              <span class="shrink-0 tabular-nums text-slate-500">{{ fmt.compact(u.tokens) }}</span>
            </li>
          </ol>
        </AdminCard>

        <AdminCard :title="$t('admin.ai.quotas')">
          <p class="text-sm text-slate-600 dark:text-slate-300">{{ $t('admin.ai.defaultLimit', { n: fmt.num(data.quotas.default_limit) }) }}</p>
          <p class="mt-1 text-sm" :class="data.quotas.exhausted ? 'font-semibold text-amber-700 dark:text-amber-300' : 'text-slate-500'">
            {{ $t('admin.ai.exhausted', { n: fmt.num(data.quotas.exhausted) }) }}
          </p>
          <div class="mt-3 flex flex-wrap gap-2">
            <span v-for="row in data.quotas.by_tier" :key="row.tier" class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-surface-2 dark:text-slate-300">
              {{ $te(`admin.tiers.${row.tier}`) ? $t(`admin.tiers.${row.tier}`) : row.tier }}: {{ fmt.num(row.n) }}
            </span>
          </div>
        </AdminCard>
      </div>
    </div>
  </div>
</template>
