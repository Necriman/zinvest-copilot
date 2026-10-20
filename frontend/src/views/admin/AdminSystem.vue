<script setup>
// How this deployment is set up: a checklist of security, sign-in and service
// settings (each one ok / worth a look / broken), who can sign in how, and the
// runtime. Values are yes/no and counts only; the server never sends secrets.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import AdminCard from '@/components/admin/AdminCard.vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStat from '@/components/admin/AdminStat.vue'
import AppButton from '@/components/ui/AppButton.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'

const { t } = useI18n()
const admin = useAdmin()
const fmt = useAdminFormat()

const data = ref(null)
const error = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await admin.act(() => adminApi.system())
  } catch (e) {
    error.value = admin.errorText(e, t)
  } finally {
    loading.value = false
  }
}
load()

const GROUPS = {
  security: ['debug_off', 'https_origin', 'secure_cookies', 'allowed_hosts', 'admin_2fa_required', 'staff_2fa', 'django_admin_off', 'superusers', 'access_ttl', 'telegram_webhook_secret'],
  signin: ['mail', 'login_codes', 'google', 'registration'],
  services: ['gemini', 'database', 'db_latency', 'migrations'],
}

const byKey = computed(() => Object.fromEntries((data.value?.checks || []).map((c) => [c.key, c])))
const groups = computed(() =>
  Object.entries(GROUPS).map(([name, keys]) => ({ name, checks: keys.map((k) => byKey.value[k]).filter(Boolean) })),
)
const counts = computed(() => {
  const all = data.value?.checks || []
  return { fail: all.filter((c) => c.status === 'fail').length, warn: all.filter((c) => c.status === 'warn').length }
})

function value(check) {
  const v = check.value
  if (v === null || v === undefined || v === '') return ''
  switch (check.key) {
    case 'db_latency':
      return t('admin.system.ms', { n: v })
    case 'access_ttl':
      return t('admin.system.minutes', { n: v })
    case 'registration':
      return v ? t('admin.system.open') : t('admin.system.closed')
    case 'migrations':
      return v.length ? v.join(', ') : ''
    default:
      return String(v)
  }
}

const a = computed(() => data.value?.accounts || {})
const r = computed(() => data.value?.runtime || {})
</script>

<template>
  <div>
    <AdminHeader :title="$t('admin.system.title')" :intro="$t('admin.system.intro')">
      <AppButton variant="outline" size="sm" icon="refresh" :disabled="loading" @click="load">{{ $t('admin.system.recheck') }}</AppButton>
    </AdminHeader>

    <p v-if="error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>

    <div class="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
      <AdminStat :label="$t('admin.system.failing')" icon="alert" :tone="counts.fail ? 'red' : 'green'" :loading="!data" :value="fmt.num(counts.fail)" />
      <AdminStat :label="$t('admin.system.toReview')" icon="flag" :tone="counts.warn ? 'amber' : 'green'" :loading="!data" :value="fmt.num(counts.warn)" />
      <AdminStat :label="$t('admin.system.staff')" icon="key" tone="brand" :loading="!data" :value="fmt.num(a.staff)" :hint="$t('admin.system.without2fa', { n: a.staff_without_2fa ?? 0 })" />
      <AdminStat :label="$t('admin.system.accounts')" icon="users" tone="slate" :loading="!data" :value="fmt.num(a.total)" />
    </div>

    <div class="mt-4 grid gap-4 xl:grid-cols-3">
      <AdminCard v-for="g in groups" :key="g.name" :title="$t(`admin.system.groups.${g.name}`)">
        <div v-if="!data" class="space-y-3">
          <LoadingSkeleton v-for="n in 4" :key="n" height="h-12" rounded="rounded-xl" />
        </div>
        <ul v-else class="divide-y divide-slate-100 dark:divide-hairline">
          <li v-for="c in g.checks" :key="c.key" class="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
            <span class="sys-dot" :data-status="c.status" :aria-label="$t(`admin.system.status.${c.status}`)" role="img" />
            <div class="min-w-0 flex-1">
              <p class="text-sm font-semibold text-slate-800 dark:text-slate-100">{{ $t(`admin.system.checks.${c.key}.label`) }}</p>
              <p class="mt-0.5 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                {{ $t(`admin.system.checks.${c.key}.${c.status === 'ok' || c.status === 'info' ? 'ok' : 'fix'}`) }}
              </p>
              <p v-if="value(c)" class="mt-1 break-all font-mono text-xs text-slate-600 dark:text-slate-300">{{ value(c) }}</p>
            </div>
            <span class="sys-badge" :data-status="c.status">{{ $t(`admin.system.status.${c.status}`) }}</span>
          </li>
        </ul>
      </AdminCard>
    </div>

    <div class="mt-4 grid gap-4 lg:grid-cols-2">
      <AdminCard :title="$t('admin.system.signinTitle')">
        <dl class="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div v-for="k in ['google_linked', 'passwordless', 'email_verified', 'consented']" :key="k">
            <dt class="text-slate-500 dark:text-slate-400">{{ $t(`admin.system.acc.${k}`) }}</dt>
            <dd class="mt-0.5 text-lg font-bold tabular-nums">{{ data ? fmt.num(a[k]) : '…' }}</dd>
          </div>
        </dl>
      </AdminCard>
      <AdminCard :title="$t('admin.system.runtimeTitle')">
        <dl class="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div v-for="k in ['region', 'commit', 'python', 'django', 'deployment', 'server_time']" :key="k">
            <dt class="text-slate-500 dark:text-slate-400">{{ $t(`admin.system.rt.${k}`) }}</dt>
            <dd class="mt-0.5 break-all font-mono text-xs">{{ k === 'server_time' && r[k] ? fmt.dateTime(r[k]) : r[k] || '—' }}</dd>
          </div>
        </dl>
      </AdminCard>
    </div>
  </div>
</template>

<style scoped>
.sys-dot {
  flex-shrink: 0;
  width: 0.65rem;
  height: 0.65rem;
  margin-top: 0.35rem;
  border-radius: 50%;
  background: #94a3b8;
}
.sys-dot[data-status='ok'] {
  background: #30a46c;
}
.sys-dot[data-status='warn'] {
  background: #f5a524;
}
.sys-dot[data-status='fail'] {
  background: #e5484d;
}
.sys-badge {
  flex-shrink: 0;
  padding: 0.15rem 0.55rem;
  border-radius: 99px;
  font-size: 0.7rem;
  font-weight: 700;
  background: #f1f5f9;
  color: #475569;
}
.sys-badge[data-status='ok'] {
  background: rgba(48, 164, 108, 0.12);
  color: #1a6b45;
}
.sys-badge[data-status='warn'] {
  background: rgba(245, 165, 36, 0.16);
  color: #8a5100;
}
.sys-badge[data-status='fail'] {
  background: rgba(229, 72, 77, 0.12);
  color: #a8232a;
}
:where(.dark) .sys-badge {
  background: rgba(148, 163, 184, 0.14);
  color: #cbd5e1;
}
:where(.dark) .sys-badge[data-status='ok'] {
  color: #6fdba5;
}
:where(.dark) .sys-badge[data-status='warn'] {
  color: #fbbf24;
}
:where(.dark) .sys-badge[data-status='fail'] {
  color: #ff9592;
}
</style>
