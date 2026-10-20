<script setup>
// Automatic bans (accounts.bans) and the live counters behind them: who is
// sending how many requests in the current window, and how close that is to
// a ban. Owners and admins lift a ban here.
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AdminCard from '@/components/admin/AdminCard.vue'
import AdminModal from '@/components/admin/AdminModal.vue'
import AdminPager from '@/components/admin/AdminPager.vue'
import AdminStat from '@/components/admin/AdminStat.vue'
import AppButton from '@/components/ui/AppButton.vue'
import Icon from '@/components/ui/Icon.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'

const { t } = useI18n()
const admin = useAdmin()
const fmt = useAdminFormat()

const show = ref('active')
const state = reactive({ rows: [], page: 1, pages: 1, total: 0, summary: null, counters: null, policy: null, loading: false, error: '' })
const lifting = ref(null)
const busy = ref(false)

async function load() {
  state.loading = true
  state.error = ''
  try {
    const data = await admin.act(() => adminApi.bans({ show: show.value, page: state.page }))
    Object.assign(state, {
      rows: data.results, pages: data.pages, total: data.total, page: data.page,
      summary: data.summary, counters: data.counters, policy: data.policy,
    })
  } catch (e) {
    state.error = admin.errorText(e, t)
  } finally {
    state.loading = false
  }
}

async function lift() {
  const ban = lifting.value
  if (!ban || busy.value) return
  // Close first: if the server wants a fresh "it's me", that dialog must not sit under this one.
  lifting.value = null
  busy.value = true
  state.error = ''
  try {
    await admin.act(() => adminApi.liftBan(ban.id))
    await load()
  } catch (e) {
    state.error = admin.errorText(e, t)
  } finally {
    busy.value = false
  }
}

watch(show, () => {
  if (state.page !== 1) state.page = 1
  else load()
})
watch(() => state.page, (value, old) => value !== old && load())
load()

// The counters live for a minute: refresh them while the page is open.
const timer = setInterval(() => !state.loading && !lifting.value && document.visibilityState === 'visible' && load(), 15000)
onBeforeUnmount(() => clearInterval(timer))

const s = computed(() => state.summary || {})
const canLift = computed(() => admin.can('security.manage'))

const fill = (c) => (c.ban_at ? Math.min(100, Math.round((c.hits / c.ban_at) * 100)) : null)
const tone = (c) => {
  if (!c.limit) return 'bg-slate-400'
  if (c.ban_at && c.hits >= c.ban_at) return 'bg-red-600'
  if (c.hits > c.limit) return 'bg-amber-500'
  return 'bg-emerald-500'
}
const status = (b) => {
  if (b.lifted_at) return t('admin.security.lifted', { who: b.lifted_by || '—' })
  if (!b.active) return t('admin.security.expired')
  return b.forever ? t('admin.security.forever') : fmt.dateTime(b.expires_at)
}
</script>

<template>
  <section class="mt-6" aria-labelledby="bans-title">
    <div class="mb-3 flex flex-wrap items-end justify-between gap-3">
      <div class="min-w-0 max-w-3xl">
        <h2 id="bans-title" class="text-base font-bold text-slate-900 dark:text-slate-100">{{ $t('admin.security.bans') }}</h2>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {{ $t('admin.security.bansIntro', { factor: state.policy?.factor || 2 }) }}
        </p>
        <p v-if="state.policy && !state.policy.enabled" class="mt-1 text-sm font-semibold text-amber-600 dark:text-amber-400">
          {{ $t('admin.security.bansOff') }}
        </p>
      </div>
      <div class="inline-flex rounded-full bg-slate-100 p-1 dark:bg-surface-2" role="group" :aria-label="$t('admin.security.bans')">
        <button
          v-for="opt in ['active', 'all']"
          :key="opt"
          type="button"
          class="rounded-full px-3 py-1.5 text-xs font-semibold transition"
          :class="show === opt ? 'bg-white text-slate-900 shadow-sm dark:bg-surface dark:text-white' : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'"
          :aria-pressed="show === opt"
          @click="show = opt"
        >
          {{ opt === 'active' ? $t('admin.security.showActive') : $t('admin.security.showAll') }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4">
      <AdminStat :label="$t('admin.security.bannedAccounts')" icon="users" :tone="s.accounts ? 'red' : 'slate'" :loading="!state.summary" :value="fmt.num(s.accounts)" />
      <AdminStat :label="$t('admin.security.bannedAddresses')" icon="shield" :tone="s.addresses ? 'amber' : 'slate'" :loading="!state.summary" :value="fmt.num(s.addresses)" />
      <AdminStat class="col-span-2 sm:col-span-1" :label="$t('admin.security.bansWeek')" icon="alert" tone="slate" :loading="!state.summary" :value="fmt.num(s.week)" />
    </div>

    <p v-if="state.error" class="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ state.error }}</p>

    <div class="mt-4 grid gap-4 xl:grid-cols-5">
      <!-- Bans -->
      <AdminCard class="xl:col-span-3">
        <p v-if="!state.loading && !state.rows.length" class="py-6 text-center text-sm text-slate-400">{{ $t('admin.security.noBans') }}</p>
        <ul v-else class="divide-y divide-slate-100 dark:divide-white/5" :aria-busy="state.loading">
          <li v-for="b in state.rows" :key="b.id" class="flex flex-wrap items-center gap-x-4 gap-y-2 py-3 first:pt-0 last:pb-0">
            <span
              class="grid h-9 w-9 shrink-0 place-items-center rounded-xl"
              :class="b.kind === 'user' ? 'bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400' : 'bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400'"
              aria-hidden="true"
            >
              <Icon :name="b.kind === 'user' ? 'user' : 'globe'" class="h-4 w-4" />
            </span>
            <div class="min-w-[min(100%,15rem)] flex-1">
              <p class="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                <span class="sr-only">{{ b.kind === 'user' ? $t('admin.security.kindUser') : $t('admin.security.kindIp') }}: </span>
                <router-link v-if="b.user" :to="{ name: 'adminUser', params: { id: b.user.id } }" class="hover:underline">{{ b.user.email }}</router-link>
                <span v-else class="font-mono">{{ b.value }}</span>
              </p>
              <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                <span class="font-mono">{{ b.reason }}</span>
                · {{ $t('admin.security.requests', { hits: b.hits, limit: b.limit }) }}
                <template v-if="b.kind === 'ip'"> · {{ $t('admin.security.strike', { n: b.strike }) }}</template>
                · {{ fmt.dateTime(b.at) }}
              </p>
            </div>
            <div class="ml-auto flex items-center gap-3">
              <span
                class="whitespace-nowrap text-xs font-semibold"
                :class="b.active ? (b.forever ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400') : 'text-slate-400'"
              >
                <span class="sr-only">{{ $t('admin.security.until') }}: </span>{{ status(b) }}
              </span>
              <AppButton v-if="canLift && !b.lifted_at" variant="ghost" size="sm" :disabled="busy" @click="lifting = b">{{ $t('admin.security.lift') }}</AppButton>
            </div>
          </li>
        </ul>
        <AdminPager v-if="state.pages > 1" v-model:page="state.page" :pages="state.pages" :total="state.total" class="mt-4" />
      </AdminCard>

      <!-- Live counters -->
      <AdminCard class="xl:col-span-2" :title="$t('admin.security.counters')" :hint="state.counters ? $t('admin.security.countersHint') : ''">
        <p v-if="state.summary && !state.counters" class="text-sm text-slate-400">{{ $t('admin.security.countersOff') }}</p>
        <p v-else-if="state.counters && !state.counters.length" class="text-sm text-slate-400">{{ $t('admin.security.noCounters') }}</p>
        <ul v-else-if="state.counters" class="space-y-3">
          <li v-for="c in state.counters" :key="c.scope + c.who">
            <div class="flex items-baseline justify-between gap-3 text-xs">
              <span class="min-w-0 truncate font-mono text-slate-700 dark:text-slate-200" :title="c.who">{{ c.who }}</span>
              <span class="shrink-0 tabular-nums font-semibold text-slate-800 dark:text-slate-100">
                {{ c.hits }}<template v-if="c.limit"> / {{ c.limit }}</template>
              </span>
            </div>
            <div
              v-if="fill(c) !== null"
              class="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-white/10"
              role="meter"
              :aria-label="c.who"
              aria-valuemin="0"
              :aria-valuemax="c.ban_at"
              :aria-valuenow="c.hits"
            >
              <div class="h-full rounded-full transition-[width] duration-500" :class="tone(c)" :style="{ width: fill(c) + '%' }" />
            </div>
            <p class="mt-0.5 text-[11px] text-slate-400">
              <span class="font-mono">{{ c.scope }}</span> · {{ $t('admin.security.resetsIn', { s: c.resets_in }) }}
            </p>
          </li>
        </ul>
      </AdminCard>
    </div>

    <AdminModal :open="!!lifting" :title="$t('admin.security.lift')" :text="$t('admin.security.liftConfirm')" @close="lifting = null">
      <p class="mb-4 break-all font-mono text-sm text-slate-700 dark:text-slate-200">{{ lifting?.user?.email || lifting?.value }}</p>
      <div class="flex justify-end gap-2">
        <AppButton variant="ghost" size="sm" @click="lifting = null">{{ $t('admin.common.cancel') }}</AppButton>
        <AppButton size="sm" :disabled="busy" @click="lift">{{ $t('admin.security.lift') }}</AppButton>
      </div>
    </AdminModal>
  </section>
</template>
