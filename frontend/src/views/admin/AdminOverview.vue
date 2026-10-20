<script setup>
// The morning numbers: growth, who came back, who got started, learning, the
// founder network, AI spend and anything odd on the security side.
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AdminCard from '@/components/admin/AdminCard.vue'
import AdminChart from '@/components/admin/AdminChart.vue'
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
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await admin.act(() => adminApi.overview())
  } catch (e) {
    error.value = admin.errorText(e, t)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const u = computed(() => data.value?.users || {})
const a = computed(() => data.value?.activity || {})
const act = computed(() => data.value?.activation || {})
const l = computed(() => data.value?.learning || {})
const n = computed(() => data.value?.network || {})
const ai = computed(() => data.value?.ai || {})
const s = computed(() => data.value?.security || {})

const growth = computed(() => {
  const now = u.value.new_week || 0
  const before = u.value.new_prev_week || 0
  if (!before) return null
  return Math.round(((now - before) / before) * 100)
})

const funnel = computed(() => [
  { label: t('admin.overview.onboarded'), value: act.value.onboarded, pct: act.value.onboarded_pct },
  { label: t('admin.overview.firstLesson'), value: act.value.first_lesson, pct: act.value.first_lesson_pct },
])

const topMax = computed(() => Math.max(1, ...(data.value?.top_units || []).map((r) => r.n)))
</script>

<template>
  <div>
    <AdminHeader :title="$t('admin.overview.title')" :intro="data ? $t('admin.overview.updated', { time: fmt.dateTime(data.generated_at) }) : ''">
      <AppButton variant="outline" size="sm" icon="refresh" :disabled="loading" @click="load">
        {{ $t('admin.common.refresh') }}
      </AppButton>
    </AdminHeader>

    <p v-if="error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>

    <!-- Growth and activity -->
    <div class="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
      <AdminStat
        :label="$t('admin.overview.users')"
        icon="users"
        :loading="!data"
        :value="fmt.num(u.total)"
        :hint="`+${fmt.num(u.new_today)} ${$t('admin.overview.today')}`"
      />
      <AdminStat
        :label="$t('admin.overview.newWeek')"
        icon="trending"
        tone="green"
        :loading="!data"
        :value="fmt.num(u.new_week)"
        :hint="$t('admin.overview.vsPrev', { n: fmt.num(u.new_prev_week) })"
      >
        <span
          v-if="growth !== null"
          class="mt-2 inline-flex w-fit rounded-full px-2 py-0.5 text-xs font-bold tabular-nums"
          :class="growth >= 0 ? 'bg-green-50 text-green-700 dark:bg-green-500/15 dark:text-green-300' : 'bg-red-50 text-red-600 dark:bg-red-500/15 dark:text-red-300'"
        >
          {{ growth >= 0 ? '+' : '' }}{{ growth }}%
        </span>
      </AdminStat>
      <AdminStat
        :label="$t('admin.overview.visited')"
        icon="eye"
        tone="amber"
        :loading="!data"
        :value="`${fmt.num(a.visited_day)} / ${fmt.num(a.visited_week)} / ${fmt.num(a.visited_month)}`"
        :hint="$t('admin.overview.visitedHint')"
      />
      <AdminStat
        :label="$t('admin.overview.retention')"
        icon="target"
        tone="slate"
        :loading="!data"
        :value="`${a.retention_week1 ?? 0}%`"
        :hint="$t('admin.overview.retentionHint', { n: fmt.num(a.retention_cohort) })"
      />
    </div>

    <!-- 30 days -->
    <div class="mt-4 grid gap-3 sm:gap-4 lg:grid-cols-3">
      <template v-if="data">
        <AdminChart :title="$t('admin.overview.chartSignups')" :points="data.series.signups" tone="green" />
        <AdminChart :title="$t('admin.overview.chartVisitors')" :points="data.series.visitors" />
        <AdminChart :title="$t('admin.overview.chartLessons')" :points="data.series.lessons" tone="amber" />
      </template>
      <template v-else>
        <LoadingSkeleton v-for="i in 3" :key="i" height="h-48" rounded="rounded-3xl" />
      </template>
    </div>

    <div v-if="data" class="mt-4 grid gap-3 sm:gap-4 lg:grid-cols-3">
      <!-- Activation funnel -->
      <AdminCard :title="$t('admin.overview.activation')">
        <ul class="space-y-3.5">
          <li v-for="step in funnel" :key="step.label">
            <div class="flex items-baseline justify-between gap-2 text-sm">
              <span class="text-slate-600 dark:text-slate-300">{{ step.label }}</span>
              <span class="font-bold tabular-nums text-slate-900 dark:text-white">{{ step.pct }}%</span>
            </div>
            <div class="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-surface-2">
              <div class="h-full rounded-full bg-brand-500" :style="{ width: `${step.pct}%` }" />
            </div>
            <p class="mt-1 text-xs tabular-nums text-slate-400">{{ fmt.num(step.value) }} / {{ fmt.num(u.total) }}</p>
          </li>
          <li class="flex items-baseline justify-between gap-2 border-t border-slate-100 pt-3 text-sm dark:border-hairline">
            <span class="text-slate-600 dark:text-slate-300">{{ $t('admin.overview.startups') }}</span>
            <span class="font-bold tabular-nums text-slate-900 dark:text-white">{{ fmt.num(act.startup_profiles) }}</span>
          </li>
        </ul>
      </AdminCard>

      <!-- Learning -->
      <AdminCard :title="$t('admin.overview.learning')">
        <dl class="space-y-3 text-sm">
          <div class="flex items-baseline justify-between gap-2">
            <dt class="text-slate-600 dark:text-slate-300">{{ $t('admin.overview.studied') }}</dt>
            <dd class="font-bold tabular-nums text-slate-900 dark:text-white">{{ fmt.num(a.studied_week) }}</dd>
          </div>
          <div class="flex items-baseline justify-between gap-2">
            <dt class="text-slate-600 dark:text-slate-300">{{ $t('admin.overview.lessonsWeek') }}</dt>
            <dd class="font-bold tabular-nums text-slate-900 dark:text-white">{{ fmt.num(l.lessons_week) }}</dd>
          </div>
          <div class="flex items-baseline justify-between gap-2">
            <dt class="text-slate-600 dark:text-slate-300">{{ $t('admin.overview.testsWeek') }}</dt>
            <dd class="text-right">
              <span class="font-bold tabular-nums text-slate-900 dark:text-white">{{ fmt.num(l.tests_week) }}</span>
              <span class="ml-1.5 text-xs text-slate-400">{{ $t('admin.overview.passRate', { p: l.tests_pass_pct }) }}</span>
            </dd>
          </div>
        </dl>
        <div v-if="data.top_units.length" class="mt-4 border-t border-slate-100 pt-4 dark:border-hairline">
          <p class="text-xs font-semibold text-slate-400">{{ $t('admin.overview.topUnits') }}</p>
          <ul class="mt-2 space-y-2">
            <li v-for="row in data.top_units" :key="row.lesson__unit__title" class="text-sm">
              <div class="flex justify-between gap-2">
                <span class="truncate text-slate-600 dark:text-slate-300">{{ row.lesson__unit__title }}</span>
                <span class="tabular-nums text-slate-500">{{ fmt.num(row.n) }}</span>
              </div>
              <div class="mt-1 h-1.5 rounded-full bg-slate-100 dark:bg-surface-2">
                <div class="h-full rounded-full bg-amber-400" :style="{ width: `${(row.n / topMax) * 100}%` }" />
              </div>
            </li>
          </ul>
        </div>
      </AdminCard>

      <div class="grid gap-3 sm:gap-4">
        <!-- Network -->
        <AdminCard :title="$t('admin.overview.network')">
          <dl class="space-y-2.5 text-sm">
            <div class="flex justify-between gap-2">
              <dt class="text-slate-600 dark:text-slate-300">{{ $t('admin.overview.posts') }}</dt>
              <dd class="font-bold tabular-nums text-slate-900 dark:text-white">{{ fmt.num(n.posts_week) }}</dd>
            </div>
            <div class="flex justify-between gap-2">
              <dt class="text-slate-600 dark:text-slate-300">{{ $t('admin.overview.messages') }}</dt>
              <dd class="font-bold tabular-nums text-slate-900 dark:text-white">{{ fmt.num(n.messages_week) }}</dd>
            </div>
            <div class="flex justify-between gap-2">
              <dt class="text-slate-600 dark:text-slate-300">{{ $t('admin.overview.openReports') }}</dt>
              <dd>
                <RouterLink
                  v-if="admin.can('moderation.view')"
                  :to="{ name: 'adminModeration' }"
                  class="font-bold tabular-nums hover:underline"
                  :class="n.open_reports ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'"
                >
                  {{ fmt.num(n.open_reports) }}
                </RouterLink>
                <span v-else class="font-bold tabular-nums">{{ fmt.num(n.open_reports) }}</span>
              </dd>
            </div>
          </dl>
        </AdminCard>

        <!-- AI -->
        <AdminCard :title="$t('admin.overview.ai')">
          <p class="text-2xl font-extrabold tabular-nums text-slate-900 dark:text-white">{{ fmt.compact(ai.tokens_month) }}</p>
          <p class="mt-1 text-xs text-slate-400">
            {{ $t('admin.overview.requests', { n: fmt.num(ai.requests_month) }) }} · {{ $t('admin.ai.people') }}: {{ fmt.num(ai.users_month) }}
          </p>
        </AdminCard>

        <!-- Security -->
        <AdminCard :title="$t('admin.overview.security')">
          <dl class="grid grid-cols-3 gap-2 text-center">
            <div class="flex flex-col-reverse justify-end">
              <dt class="mt-0.5 text-[11px] leading-tight text-slate-400">{{ $t('admin.overview.failedLogins') }}</dt>
              <dd class="text-xl font-extrabold tabular-nums" :class="s.failed_logins_day > 50 ? 'text-amber-600' : 'text-slate-900 dark:text-white'">{{ fmt.num(s.failed_logins_day) }}</dd>
            </div>
            <div class="flex flex-col-reverse justify-end">
              <dt class="mt-0.5 text-[11px] leading-tight text-slate-400">{{ $t('admin.overview.lockouts') }}</dt>
              <dd class="text-xl font-extrabold tabular-nums" :class="s.lockouts_day ? 'text-amber-600' : 'text-slate-900 dark:text-white'">{{ fmt.num(s.lockouts_day) }}</dd>
            </div>
            <div class="flex flex-col-reverse justify-end">
              <dt class="mt-0.5 text-[11px] leading-tight text-slate-400">{{ $t('admin.overview.tokenReuse') }}</dt>
              <dd class="text-xl font-extrabold tabular-nums" :class="s.token_reuse_week ? 'text-red-600' : 'text-slate-900 dark:text-white'">{{ fmt.num(s.token_reuse_week) }}</dd>
            </div>
          </dl>
          <RouterLink
            v-if="admin.can('security.view')"
            :to="{ name: 'adminSecurity' }"
            class="mt-3 inline-flex text-xs font-semibold text-brand-600 hover:underline dark:text-brand-300"
          >
            {{ $t('admin.nav.security') }} →
          </RouterLink>
        </AdminCard>
      </div>
    </div>

    <div v-if="data?.signin" class="mt-4 grid gap-3 sm:gap-4 lg:grid-cols-2">
      <!-- How people sign in -->
      <AdminCard :title="$t('admin.overview.signin')">
        <dl class="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div>
            <dt class="text-slate-500 dark:text-slate-400">{{ $t('admin.system.acc.google_linked') }}</dt>
            <dd class="mt-0.5 text-lg font-bold tabular-nums">{{ fmt.num(data.signin.google_linked) }}</dd>
          </div>
          <div>
            <dt class="text-slate-500 dark:text-slate-400">{{ $t('admin.system.acc.passwordless') }}</dt>
            <dd class="mt-0.5 text-lg font-bold tabular-nums">{{ fmt.num(data.signin.passwordless) }}</dd>
          </div>
          <div>
            <dt class="text-slate-500 dark:text-slate-400">{{ $t('admin.system.acc.email_verified') }}</dt>
            <dd class="mt-0.5 text-lg font-bold tabular-nums">{{ fmt.num(data.signin.email_verified) }} <span class="text-sm font-semibold text-slate-500">· {{ data.signin.email_verified_pct }}%</span></dd>
          </div>
          <div>
            <dt class="text-slate-500 dark:text-slate-400">{{ $t('admin.system.acc.consented') }}</dt>
            <dd class="mt-0.5 text-lg font-bold tabular-nums">{{ fmt.num(data.signin.consented) }}</dd>
          </div>
        </dl>
      </AdminCard>

      <!-- Market checks from the startup intake -->
      <AdminCard :title="$t('admin.startups.verdicts')">
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ $t('admin.overview.checked', { n: fmt.num(data.startups.checked) }) }}</p>
        <ul class="mt-3 grid grid-cols-2 gap-2 text-sm">
          <li v-for="(n, v) in data.startups.verdicts" :key="v" class="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 dark:bg-surface-2">
            <span>{{ $t(`startup.research.verdict.${v}`) }}</span>
            <b class="tabular-nums">{{ fmt.num(n) }}</b>
          </li>
        </ul>
        <RouterLink
          v-if="admin.can('startups.view')"
          :to="{ name: 'adminStartups' }"
          class="mt-3 inline-flex text-xs font-semibold text-brand-600 hover:underline dark:text-brand-300"
        >
          {{ $t('admin.nav.startups') }} →
        </RouterLink>
      </AdminCard>
    </div>
  </div>
</template>
