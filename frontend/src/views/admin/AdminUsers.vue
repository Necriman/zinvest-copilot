<script setup>
// Everyone with an account: search, filter, sort, open a card, export.
// Filters live in the URL so a list can be shared or come back to.
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminPager from '@/components/admin/AdminPager.vue'
import AdminRoleBadge from '@/components/admin/AdminRoleBadge.vue'
import AdminTable from '@/components/admin/AdminTable.vue'
import AppButton from '@/components/ui/AppButton.vue'
import Avatar from '@/components/ui/Avatar.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
import SearchField from '@/components/ui/SearchField.vue'
import { adminApi, download } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const admin = useAdmin()
const fmt = useAdminFormat()

const q = ref(String(route.query.q || ''))
const status = ref(String(route.query.status || ''))
const who = ref(String(route.query.role || ''))
const joined = ref(String(route.query.joined || ''))
const sort = ref(String(route.query.sort || 'joined'))
const page = ref(Number(route.query.page) || 1)

const rows = ref([])
const pages = ref(1)
const total = ref(0)
const loading = ref(false)
const error = ref('')
const exporting = ref(false)

const columns = computed(() => [
  { key: 'user', label: t('admin.users.user') },
  { key: 'status', label: t('admin.users.status') },
  { key: 'joined', label: t('admin.users.joined') },
  { key: 'last_seen', label: t('admin.users.lastSeen') },
  { key: 'lessons_done', label: t('admin.users.lessons'), align: 'right' },
  { key: 'coins', label: t('admin.users.coins'), align: 'right' },
])

let seq = 0
async function load() {
  const mine = ++seq
  loading.value = true
  error.value = ''
  const params = { q: q.value || undefined, status: status.value || undefined, role: who.value || undefined, joined: joined.value || undefined, sort: sort.value, page: page.value }
  router.replace({ query: { ...params, sort: sort.value === 'joined' ? undefined : sort.value, page: page.value > 1 ? page.value : undefined } })
  try {
    const data = await admin.act(() => adminApi.users(params))
    if (mine !== seq) return
    rows.value = data.results
    pages.value = data.pages
    total.value = data.total
    page.value = data.page
  } catch (e) {
    if (mine === seq) error.value = admin.errorText(e, t)
  } finally {
    if (mine === seq) loading.value = false
  }
}

watch([q, status, who, joined, sort], () => {
  // Back to the first page; the page watcher loads if the page changed.
  if (page.value !== 1) page.value = 1
  else load()
})
watch(page, (value, old) => value !== old && load())
load()

async function exportCsv() {
  exporting.value = true
  try {
    const blob = await admin.act(() => adminApi.exportUsersCsv())
    download(blob, 'zinvest-users.csv')
  } catch (e) {
    error.value = admin.errorText(e, t)
  } finally {
    exporting.value = false
  }
}

const open = (row) => router.push({ name: 'adminUser', params: { id: row.id } })

const SELECT = 'zx-input w-auto min-w-0 py-2 pr-8'
</script>

<template>
  <div>
    <AdminHeader :title="$t('admin.users.title')">
      <AppButton v-if="admin.can('users.export')" variant="outline" size="sm" icon="download" :disabled="exporting" @click="exportCsv">
        {{ $t('admin.users.exportCsv') }}
      </AppButton>
    </AdminHeader>

    <div class="mb-4 flex flex-col gap-2 lg:flex-row lg:items-center">
      <SearchField v-model="q" :placeholder="$t('admin.users.search')" :clear-label="$t('admin.common.close')" class="lg:max-w-xs lg:flex-1" />
      <div class="flex flex-wrap gap-2">
        <select v-model="status" :class="SELECT" :aria-label="$t('admin.users.status')">
          <option value="">{{ $t('admin.users.status') }}: {{ $t('admin.common.all') }}</option>
          <option value="active">{{ $t('admin.common.active') }}</option>
          <option value="disabled">{{ $t('admin.common.disabled') }}</option>
        </select>
        <select v-model="who" :class="SELECT" :aria-label="$t('admin.users.who')">
          <option value="">{{ $t('admin.users.who') }}: {{ $t('admin.common.all') }}</option>
          <option value="learners">{{ $t('admin.users.learners') }}</option>
          <option value="team">{{ $t('admin.users.team') }}</option>
        </select>
        <select v-model="joined" :class="SELECT" :aria-label="$t('admin.users.joined')">
          <option value="">{{ $t('admin.users.anyTime') }}</option>
          <option value="1">{{ $t('admin.users.lastDays', { n: 1 }) }}</option>
          <option value="7">{{ $t('admin.users.lastDays', { n: 7 }) }}</option>
          <option value="30">{{ $t('admin.users.lastDays', { n: 30 }) }}</option>
        </select>
        <select v-model="sort" :class="SELECT" :aria-label="$t('admin.users.sort')">
          <option value="joined">{{ $t('admin.users.sortJoined') }}</option>
          <option value="seen">{{ $t('admin.users.sortSeen') }}</option>
          <option value="lessons">{{ $t('admin.users.sortLessons') }}</option>
          <option value="coins">{{ $t('admin.users.sortCoins') }}</option>
        </select>
      </div>
    </div>

    <p v-if="error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>

    <AdminTable :columns="columns" :rows="rows" :loading="loading" clickable @open="open">
      <template #cell-user="{ row }">
        <div class="flex min-w-0 items-center gap-3">
          <Avatar :name="row.name || row.email" :src="row.avatar_url || ''" size="h-8 w-8 text-xs" />
          <div class="min-w-0">
            <p class="flex items-center gap-2 truncate font-semibold text-slate-800 dark:text-slate-100">
              <span class="truncate">{{ row.name || row.email.split('@')[0] }}</span>
              <AdminRoleBadge :role="row.role" />
            </p>
            <p class="truncate text-xs text-slate-400">{{ row.email }}<template v-if="row.startup"> · {{ row.startup }}</template></p>
          </div>
        </div>
      </template>
      <template #cell-status="{ row }">
        <PillBadge :color="row.is_active ? 'cash' : 'slate'" size="sm">
          {{ row.is_active ? $t('admin.common.active') : $t('admin.common.disabled') }}
        </PillBadge>
      </template>
      <template #cell-joined="{ row }">
        <span class="whitespace-nowrap text-slate-500">{{ fmt.date(row.date_joined) }}</span>
      </template>
      <template #cell-last_seen="{ row }">
        <span class="whitespace-nowrap text-slate-500">{{ fmt.ago(row.last_seen) }}</span>
      </template>
    </AdminTable>

    <AdminPager v-model:page="page" :pages="pages" :total="total" class="mt-4" />
  </div>
</template>
