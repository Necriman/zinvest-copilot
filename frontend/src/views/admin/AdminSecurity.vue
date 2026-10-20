<script setup>
// Sign-in trouble, token theft alerts and admin access, with the addresses
// behind the most failed sign-ins today; automatic bans and live counters.
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AdminBans from '@/components/admin/AdminBans.vue'
import AdminCard from '@/components/admin/AdminCard.vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminPager from '@/components/admin/AdminPager.vue'
import AdminStat from '@/components/admin/AdminStat.vue'
import AdminTable from '@/components/admin/AdminTable.vue'
import SearchField from '@/components/ui/SearchField.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'

const { t } = useI18n()
const admin = useAdmin()
const fmt = useAdminFormat()

const kind = ref('')
const q = ref('')
const state = reactive({ rows: [], page: 1, pages: 1, total: 0, summary: null, kinds: [], loading: false, error: '' })

async function load() {
  state.loading = true
  state.error = ''
  try {
    const data = await admin.act(() => adminApi.security({ kind: kind.value || undefined, q: q.value || undefined, page: state.page }))
    Object.assign(state, { rows: data.results, pages: data.pages, total: data.total, page: data.page, summary: data.summary, kinds: data.kinds })
  } catch (e) {
    state.error = admin.errorText(e, t)
  } finally {
    state.loading = false
  }
}

watch([kind, q], () => {
  if (state.page !== 1) state.page = 1
  else load()
})
watch(() => state.page, (value, old) => value !== old && load())
load()

const s = computed(() => state.summary || {})
const RED = new Set(['token_reuse', 'login_locked', 'admin_denied', 'admin_sudo_failed'])

const columns = computed(() => [
  { key: 'at', label: t('admin.security.when') },
  { key: 'kind', label: t('admin.security.kind') },
  { key: 'email', label: t('admin.security.who') },
  { key: 'ip', label: t('admin.security.ip') },
  { key: 'details', label: '' },
])

// Details are small key/value maps (by, count, permission…): show them flat.
const details = (row) =>
  Object.entries(row.details || {})
    .filter(([, v]) => v !== '' && v !== null && v !== undefined)
    .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`)
    .join(' · ')
</script>

<template>
  <div>
    <AdminHeader :title="$t('admin.security.title')" />

    <div class="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3 xl:grid-cols-6">
      <AdminStat :label="$t('admin.security.failedDay')" icon="lock" tone="amber" :loading="!state.summary" :value="fmt.num(s.failed_day)" />
      <AdminStat :label="$t('admin.security.lockedDay')" icon="alert" tone="amber" :loading="!state.summary" :value="fmt.num(s.locked_day)" />
      <AdminStat :label="$t('admin.security.reuseWeek')" icon="key" :tone="s.token_reuse_week ? 'red' : 'slate'" :loading="!state.summary" :value="fmt.num(s.token_reuse_week)" />
      <AdminStat :label="$t('admin.security.deniedWeek')" icon="shield" :tone="s.admin_denied_week ? 'red' : 'slate'" :loading="!state.summary" :value="fmt.num(s.admin_denied_week)" />
      <AdminStat :label="$t('admin.security.sessions')" icon="users" tone="green" :loading="!state.summary" :value="fmt.num(s.live_sessions)" />
      <AdminStat :label="$t('admin.security.staffNo2fa')" icon="shield" :tone="s.staff_without_2fa ? 'red' : 'green'" :loading="!state.summary" :value="fmt.num(s.staff_without_2fa)" />
    </div>

    <AdminCard v-if="s.top_ips?.length" :title="$t('admin.security.topIps')" class="mt-4">
      <ul class="flex flex-wrap gap-2">
        <li v-for="row in s.top_ips" :key="row.ip">
          <button
            type="button"
            class="rounded-full bg-slate-100 px-3 py-1.5 font-mono text-xs text-slate-700 transition hover:bg-slate-200 dark:bg-surface-2 dark:text-slate-200 dark:hover:bg-surface-2/70"
            @click="q = row.ip"
          >
            {{ row.ip }} · <b class="font-sans font-bold">{{ row.count }}</b>
          </button>
        </li>
      </ul>
    </AdminCard>

    <AdminBans />

    <h2 class="mt-8 text-base font-bold text-slate-900 dark:text-slate-100">{{ $t('admin.security.log') }}</h2>
    <div class="mb-4 mt-3 flex flex-col gap-2 sm:flex-row">
      <SearchField v-model="q" :placeholder="$t('admin.security.searchHint')" class="sm:max-w-xs sm:flex-1" />
      <select v-model="kind" class="zx-input w-auto py-2" :aria-label="$t('admin.security.kind')">
        <option value="">{{ $t('admin.security.allKinds') }}</option>
        <option v-for="k in state.kinds" :key="k.value" :value="k.value">{{ fmt.eventLabel(k.value, k.label) }}</option>
      </select>
    </div>

    <p v-if="state.error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ state.error }}</p>

    <AdminTable :columns="columns" :rows="state.rows" :loading="state.loading">
      <template #cell-at="{ row }">
        <span class="whitespace-nowrap text-slate-500">{{ fmt.dateTime(row.at) }}</span>
      </template>
      <template #cell-kind="{ row }">
        <span class="font-medium" :class="RED.has(row.kind) ? 'text-red-600 dark:text-red-400' : ''">{{ fmt.eventLabel(row.kind, row.label) }}</span>
      </template>
      <template #cell-email="{ row }">
        <span class="break-all">{{ row.email || '—' }}</span>
      </template>
      <template #cell-ip="{ row }">
        <button v-if="row.ip" type="button" class="font-mono text-xs hover:underline" @click="q = row.ip">{{ row.ip }}</button>
        <span v-else>—</span>
      </template>
      <template #cell-details="{ row }">
        <span class="text-xs text-slate-400">{{ details(row) }}</span>
      </template>
    </AdminTable>
    <AdminPager v-model:page="state.page" :pages="state.pages" :total="state.total" class="mt-4" />
  </div>
</template>
