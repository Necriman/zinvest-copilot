<script setup>
// Every change made through the panel: who, what, when and from where.
// Read-only: the API offers no way to edit or erase it.
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminPager from '@/components/admin/AdminPager.vue'
import AdminTable from '@/components/admin/AdminTable.vue'
import SearchField from '@/components/ui/SearchField.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'

const { t } = useI18n()
const router = useRouter()
const admin = useAdmin()
const fmt = useAdminFormat()

const q = ref('')
const area = ref('')
const state = reactive({ rows: [], page: 1, pages: 1, total: 0, loading: false, error: '' })

async function load() {
  state.loading = true
  state.error = ''
  try {
    const data = await admin.act(() => adminApi.audit({ q: q.value || undefined, action: area.value || undefined, page: state.page }))
    Object.assign(state, { rows: data.results, pages: data.pages, total: data.total, page: data.page })
  } catch (e) {
    state.error = admin.errorText(e, t)
  } finally {
    state.loading = false
  }
}

watch([q, area], () => {
  if (state.page !== 1) state.page = 1
  else load()
})
watch(() => state.page, (value, old) => value !== old && load())
load()

const AREAS = [
  { value: 'user', label: 'admin.nav.users' },
  { value: 'staff', label: 'admin.nav.team' },
  { value: 'content', label: 'admin.nav.content' },
  { value: 'report', label: 'admin.moderation.reports' },
  { value: 'post', label: 'admin.moderation.posts' },
  { value: 'announcement', label: 'admin.nav.announcements' },
  { value: 'settings', label: 'admin.nav.settings' },
]

const columns = computed(() => [
  { key: 'at', label: t('admin.security.when') },
  { key: 'actor', label: t('admin.audit.actor') },
  { key: 'action', label: t('admin.audit.what') },
  { key: 'ip', label: t('admin.security.ip') },
])

function open(row) {
  if (row.target_type === 'user' && row.target_id && row.action !== 'user.deleted') {
    router.push({ name: 'adminUser', params: { id: row.target_id } })
  }
}
</script>

<template>
  <div>
    <AdminHeader :title="$t('admin.audit.title')" :intro="$t('admin.audit.intro')" />

    <div class="mb-4 flex flex-col gap-2 sm:flex-row">
      <SearchField v-model="q" :placeholder="$t('admin.audit.searchHint')" class="sm:max-w-xs sm:flex-1" />
      <select v-model="area" class="zx-input w-auto py-2" :aria-label="$t('admin.audit.what')">
        <option value="">{{ $t('admin.common.all') }}</option>
        <option v-for="a in AREAS" :key="a.value" :value="a.value">{{ $t(a.label) }}</option>
      </select>
    </div>

    <p v-if="state.error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ state.error }}</p>

    <AdminTable :columns="columns" :rows="state.rows" :loading="state.loading" clickable @open="open">
      <template #cell-at="{ row }">
        <span class="whitespace-nowrap text-slate-500">{{ fmt.dateTime(row.at) }}</span>
      </template>
      <template #cell-actor="{ row }">
        <span class="break-all">{{ row.actor || '—' }}</span>
      </template>
      <template #cell-action="{ row }">
        <p class="font-medium text-slate-800 dark:text-slate-100">{{ fmt.actionLabel(row.action) }}</p>
        <p class="text-xs text-slate-400">{{ row.summary }}</p>
      </template>
      <template #cell-ip="{ row }">
        <span class="font-mono text-xs text-slate-500">{{ row.ip || '—' }}</span>
      </template>
    </AdminTable>
    <AdminPager v-model:page="state.page" :pages="state.pages" :total="state.total" class="mt-4" />
  </div>
</template>
