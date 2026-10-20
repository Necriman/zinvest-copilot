<script setup>
// The people behind the panel, whether their two-factor is on, and what each
// role is allowed to do (the same table the API enforces).
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AdminCard from '@/components/admin/AdminCard.vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminRoleBadge from '@/components/admin/AdminRoleBadge.vue'
import AdminTable from '@/components/admin/AdminTable.vue'
import Icon from '@/components/ui/Icon.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'

const { t, te } = useI18n()
const router = useRouter()
const admin = useAdmin()
const fmt = useAdminFormat()

const data = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    data.value = await admin.act(() => adminApi.staff())
  } catch (e) {
    error.value = admin.errorText(e, t)
  }
})

const columns = computed(() => [
  { key: 'email', label: t('admin.users.user') },
  { key: 'role', label: t('admin.users.role') },
  { key: 'totp_enabled', label: t('admin.team.twoFactor') },
  { key: 'last_seen', label: t('admin.users.lastSeen') },
])

const permLabel = (perm) => {
  const key = `admin.perms.${perm.replace(/\./g, '_')}`
  return te(key) ? t(key) : perm
}
</script>

<template>
  <div>
    <AdminHeader :title="$t('admin.team.title')" :intro="$t('admin.team.intro')" />

    <p v-if="error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>

    <AdminTable
      :columns="columns"
      :rows="data?.results || []"
      :loading="!data && !error"
      :clickable="admin.can('users.view')"
      @open="(row) => router.push({ name: 'adminUser', params: { id: row.id } })"
    >
      <template #cell-email="{ row }">
        <p class="font-semibold text-slate-800 dark:text-slate-100">{{ row.name || row.email.split('@')[0] }}</p>
        <p class="text-xs text-slate-400">{{ row.email }}<template v-if="!row.is_active"> · {{ $t('admin.common.disabled') }}</template></p>
      </template>
      <template #cell-role="{ row }">
        <AdminRoleBadge :role="row.role" />
      </template>
      <template #cell-totp_enabled="{ row }">
        <PillBadge :color="row.totp_enabled ? 'cash' : 'amber'" size="sm" :icon="row.totp_enabled ? 'shield' : 'alert'">
          {{ row.totp_enabled ? $t('admin.common.on') : $t('admin.common.off') }}
        </PillBadge>
      </template>
      <template #cell-last_seen="{ row }">
        <span class="text-slate-500">{{ fmt.ago(row.last_seen) }}</span>
      </template>
    </AdminTable>

    <p class="mt-3 flex items-center gap-2 text-sm text-slate-500">
      <Icon name="plus" class="h-4 w-4" /> <span><b class="font-semibold">{{ $t('admin.team.add') }}:</b> {{ $t('admin.team.addHint') }}</span>
    </p>

    <AdminCard v-if="data?.permissions" :title="$t('admin.team.matrix')" class="mt-6">
      <div class="-mx-4 overflow-x-auto sm:-mx-5">
        <table class="w-full min-w-[640px] text-sm">
          <thead>
            <tr>
              <th class="px-4 pb-2 sm:px-5" />
              <th v-for="role in data.roles" :key="role" class="px-2 pb-2 text-center text-xs font-semibold text-slate-500">
                {{ $t(`admin.roles.${role}`) }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(roles, perm) in data.permissions" :key="perm" class="border-t border-slate-100 dark:border-hairline/60">
              <td class="px-4 py-2 text-slate-600 sm:px-5 dark:text-slate-300">{{ permLabel(perm) }}</td>
              <td v-for="role in data.roles" :key="role" class="px-2 py-2 text-center">
                <template v-if="roles.includes(role)">
                  <Icon name="check" class="mx-auto h-4 w-4 text-green-600 dark:text-green-400" />
                  <span class="sr-only">{{ $t('admin.common.yes') }}</span>
                </template>
                <template v-else>
                  <span class="text-slate-300 dark:text-slate-600" aria-hidden="true">—</span>
                  <span class="sr-only">{{ $t('admin.common.no') }}</span>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </AdminCard>
  </div>
</template>
