<script setup>
// One person's card: how they learn, what they use, where they are signed in,
// and what the team can do about the account. Every action is confirmed by the
// server (role, step-up, team-account rules); the buttons only hide what the
// current role could never do.
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AdminCard from '@/components/admin/AdminCard.vue'
import AdminModal from '@/components/admin/AdminModal.vue'
import AdminRoleBadge from '@/components/admin/AdminRoleBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import Avatar from '@/components/ui/Avatar.vue'
import CheckBox from '@/components/ui/CheckBox.vue'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
import { adminApi, download } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const admin = useAdmin()
const fmt = useAdminFormat()

const id = computed(() => String(route.params.id))
const user = ref(null)
const loading = ref(true)
const error = ref('')
const notice = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    user.value = await admin.act(() => adminApi.user(id.value))
  } catch (e) {
    error.value = e?.response?.status === 404 ? t('admin.common.empty') : admin.errorText(e, t)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const isMe = computed(() => !!user.value && user.value.email === admin.me.value?.email)
const isTeam = computed(() => !!user.value && (user.value.is_superuser || !!user.value.role))
const iAmOwner = computed(() => admin.me.value?.role === 'owner')
// Team accounts are looked after by owners only; nobody acts on themselves here.
const canTouch = computed(() => !!user.value && !isMe.value && (!isTeam.value || iAmOwner.value))

const learning = computed(() => user.value?.learning || {})
const progress = computed(() => {
  const total = learning.value.lessons_total || 0
  return total ? Math.round((100 * (learning.value.lessons_done || 0)) / total) : 0
})
const aiUsedPct = computed(() => {
  const ai = user.value?.ai
  return ai?.limit ? Math.min(100, Math.round((100 * ai.used) / ai.limit)) : 0
})

// ---- Actions ---------------------------------------------------------------
const dialog = ref('') // disable | reset | quota | coins | role | delete
const busy = ref(false)
const formError = ref('')
const form = reactive({ reason: '', link: '', expires: '', tier: 'free', limit: 0, resetUsage: false, delta: '', coinsReason: '', role: '', confirm: '' })

function openDialog(name) {
  formError.value = ''
  notice.value = ''
  if (name === 'disable') form.reason = ''
  if (name === 'quota') {
    form.tier = user.value.ai.tier
    form.limit = user.value.ai.limit
    form.resetUsage = false
  }
  if (name === 'coins') {
    form.delta = ''
    form.coinsReason = ''
  }
  if (name === 'role') form.role = user.value.role || ''
  if (name === 'delete') form.confirm = ''
  dialog.value = name
}

async function run(fn, { close = true, success = '' } = {}) {
  busy.value = true
  formError.value = ''
  try {
    const result = await admin.act(fn)
    if (close) dialog.value = ''
    if (success) notice.value = success
    return result ?? true
  } catch (e) {
    const text = admin.errorText(e, t)
    if (dialog.value) formError.value = text
    else if (text) error.value = text
    return null
  } finally {
    busy.value = false
  }
}

async function setActive(active) {
  if (active || form.reason.trim()) {
    const ok = await run(() => adminApi.setStatus(id.value, active, form.reason.trim()), { success: t('admin.common.saved') })
    if (ok) await load()
  }
}

async function signOut() {
  const result = await run(() => adminApi.revokeSessions(id.value))
  if (result) {
    notice.value = t('admin.users.signedOut', { n: result.sessions_revoked })
    await load()
  }
}

async function makeResetLink() {
  form.link = ''
  const result = await run(() => adminApi.resetLink(id.value), { close: false })
  if (result) {
    form.link = result.url
    form.expires = result.expires_at
    dialog.value = 'reset'
  }
}

const copied = ref(false)
async function copyLink() {
  try {
    await navigator.clipboard.writeText(form.link)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    /* the field is selectable as a fallback */
  }
}

async function saveQuota() {
  const ok = await run(
    () => adminApi.setQuota(id.value, { tier: form.tier, monthly_token_limit: Number(form.limit), reset_usage: form.resetUsage }),
    { success: t('admin.common.saved') },
  )
  if (ok) await load()
}

async function saveCoins() {
  const delta = parseInt(form.delta, 10)
  if (!delta || !form.coinsReason.trim()) return
  const ok = await run(() => adminApi.addCoins(id.value, delta, form.coinsReason.trim()), { success: t('admin.common.saved') })
  if (ok) await load()
}

async function saveRole() {
  const ok = await run(() => adminApi.setRole(id.value, form.role), { success: t('admin.common.saved') })
  if (ok) await load()
}

async function resetTotp() {
  const ok = await run(() => adminApi.resetTotp(id.value), { success: t('admin.common.saved') })
  if (ok) await load()
}

async function exportJson() {
  const blob = await run(() => adminApi.exportUser(id.value), { close: false })
  if (blob && blob instanceof Blob) download(blob, `zinvest-user-${id.value}.json`)
}

async function removeUser() {
  const ok = await run(() => adminApi.deleteUser(id.value, form.confirm.trim()))
  if (ok) router.replace({ name: 'adminUsers' })
}

const ROLES = ['', 'support', 'content', 'analyst', 'admin', 'owner']
const TIERS = ['free', 'plus', 'pro']

const ACTION = 'flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:opacity-50 dark:text-slate-200 dark:hover:bg-surface-2'
</script>

<template>
  <div>
    <RouterLink :to="{ name: 'adminUsers' }" class="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
      <Icon name="arrowLeft" class="h-4 w-4" /> {{ $t('admin.users.back') }}
    </RouterLink>

    <div v-if="loading && !user" class="space-y-4">
      <LoadingSkeleton width="w-72" height="h-10" />
      <LoadingSkeleton height="h-48" rounded="rounded-3xl" />
    </div>

    <p v-else-if="!user" class="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>

    <template v-else>
      <!-- Who -->
      <header class="flex flex-wrap items-center gap-4">
        <Avatar :name="user.name || user.email" :src="user.avatar_url || ''" size="h-14 w-14 text-lg" />
        <div class="min-w-0 flex-1">
          <h1 class="flex flex-wrap items-center gap-2 text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            <span class="truncate">{{ user.name || user.email.split('@')[0] }}</span>
            <AdminRoleBadge :role="user.role" />
          </h1>
          <p class="mt-0.5 truncate text-sm text-slate-500">{{ user.email }}</p>
          <div class="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <PillBadge :color="user.is_active ? 'cash' : 'slate'" size="sm">
              {{ user.is_active ? $t('admin.common.active') : $t('admin.common.disabled') }}
            </PillBadge>
            <PillBadge v-if="isTeam" :color="user.totp_enabled ? 'cash' : 'amber'" size="sm" icon="shield">
              {{ user.totp_enabled ? $t('admin.unlock.enabled') : $t('admin.unlock.notEnabled') }}
            </PillBadge>
            <span>{{ $t('admin.users.joined') }}: {{ fmt.date(user.date_joined) }}</span>
            <span>· {{ $t('admin.users.lastSeen') }}: {{ fmt.ago(user.last_seen) }}</span>
          </div>
        </div>
      </header>

      <p v-if="!user.is_active && user.disabled_reason" class="mt-4 rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-700 dark:bg-surface-2 dark:text-slate-200">
        {{ $t('admin.users.disabledBecause', { reason: user.disabled_reason }) }}
      </p>
      <RouterLink
        v-if="user.reports_open && admin.can('moderation.view')"
        :to="{ name: 'adminModeration' }"
        class="mt-4 flex items-center gap-2 rounded-2xl bg-amber-50 px-4 py-3 text-sm font-medium text-amber-800 hover:underline dark:bg-amber-500/10 dark:text-amber-200"
      >
        <Icon name="flag" class="h-4 w-4" /> {{ $t('admin.users.reportsOpen', { n: user.reports_open }) }}
      </RouterLink>
      <p v-if="notice" class="mt-4 rounded-2xl bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-500/10 dark:text-green-300" role="status">{{ notice }}</p>
      <p v-if="error" class="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>

      <div class="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div class="grid min-w-0 content-start gap-4">
          <!-- Learning -->
          <AdminCard :title="$t('admin.users.learning')">
            <div class="flex items-baseline justify-between gap-2 text-sm">
              <span class="text-slate-600 dark:text-slate-300">{{ $t('admin.users.progress', { done: learning.lessons_done, total: learning.lessons_total }) }}</span>
              <span class="font-bold tabular-nums text-slate-900 dark:text-white">{{ progress }}%</span>
            </div>
            <div class="mt-2 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-surface-2">
              <div class="h-full rounded-full bg-brand-500" :style="{ width: `${progress}%` }" />
            </div>
            <dl class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
              <div v-for="item in [
                { label: $t('admin.users.unitsPassed'), value: learning.units_passed },
                { label: $t('admin.users.tests'), value: learning.tests_taken },
                { label: $t('admin.users.bestScore'), value: `${learning.best_score}%` },
                { label: $t('admin.users.streak'), value: `${learning.streak} / ${learning.longest_streak}` },
                { label: $t('admin.users.coins'), value: fmt.num(learning.coins) },
                { label: $t('admin.users.level'), value: learning.level || '—' },
              ]" :key="item.label" class="flex flex-col-reverse rounded-2xl bg-slate-50 px-3 py-2.5 dark:bg-surface-2/60">
                <dt class="mt-0.5 text-xs text-slate-400">{{ item.label }}</dt>
                <dd class="text-lg font-bold tabular-nums text-slate-900 dark:text-white">{{ item.value }}</dd>
              </div>
            </dl>
          </AdminCard>

          <!-- AI -->
          <AdminCard :title="$t('admin.users.aiAllowance')">
            <template #actions>
              <PillBadge color="brand" size="sm">{{ $t(`admin.tiers.${user.ai.tier}`) }}</PillBadge>
            </template>
            <div class="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-surface-2">
              <div class="h-full rounded-full" :class="aiUsedPct >= 100 ? 'bg-red-500' : 'bg-brand-500'" :style="{ width: `${aiUsedPct}%` }" />
            </div>
            <p class="mt-2 text-xs text-slate-500">
              {{ $t('admin.users.used', { used: fmt.num(user.ai.used), limit: fmt.num(user.ai.limit), date: fmt.date(user.ai.reset_date) }) }}
            </p>
            <ul v-if="user.ai.by_feature.length" class="mt-3 divide-y divide-slate-100 text-sm dark:divide-hairline">
              <li v-for="row in user.ai.by_feature" :key="row.feature" class="flex justify-between gap-2 py-2">
                <span class="text-slate-600 dark:text-slate-300">{{ $te(`admin.ai.feature.${row.feature}`) ? $t(`admin.ai.feature.${row.feature}`) : row.feature }}</span>
                <span class="tabular-nums text-slate-500">{{ $t('admin.overview.requests', { n: row.requests }) }} · {{ fmt.compact(row.tokens) }}</span>
              </li>
            </ul>
          </AdminCard>

          <!-- Startup -->
          <AdminCard v-if="user.startup" :title="$t('admin.users.startup')">
            <p class="font-semibold text-slate-800 dark:text-slate-100">{{ user.startup.name }}</p>
            <p class="text-sm text-slate-500">{{ user.startup.industry }}</p>
            <div class="mt-3 flex flex-wrap gap-2 text-xs">
              <PillBadge :color="user.startup.public ? 'cash' : 'slate'" size="sm">
                {{ user.startup.public ? $t('admin.users.public') : $t('admin.users.private') }}
              </PillBadge>
              <PillBadge size="sm">{{ $t('admin.users.employees') }}: {{ user.startup.employees }}</PillBadge>
              <PillBadge size="sm">{{ $t('admin.users.products') }}: {{ user.startup.products }}</PillBadge>
              <PillBadge size="sm">{{ $t('admin.users.posts') }}: {{ user.startup.posts }}</PillBadge>
            </div>
          </AdminCard>

          <div class="grid gap-4 xl:grid-cols-2">
            <!-- Sessions -->
            <AdminCard :title="$t('admin.users.sessions')">
              <p v-if="!user.sessions.length" class="text-sm text-slate-400">{{ $t('admin.users.noSessions') }}</p>
              <ul v-else class="divide-y divide-slate-100 text-sm dark:divide-hairline">
                <li v-for="(s, i) in user.sessions" :key="i" class="py-2">
                  <p class="truncate font-medium text-slate-700 dark:text-slate-200">{{ s.device }}</p>
                  <p class="text-xs text-slate-400">{{ s.ip || '—' }} · {{ fmt.ago(s.last_active) }}</p>
                </li>
              </ul>
            </AdminCard>

            <!-- Security -->
            <AdminCard :title="$t('admin.users.securityLog')">
              <p v-if="!user.security.length" class="text-sm text-slate-400">{{ $t('admin.common.empty') }}</p>
              <ul v-else class="divide-y divide-slate-100 text-sm dark:divide-hairline">
                <li v-for="(e, i) in user.security" :key="i" class="py-2">
                  <p class="font-medium" :class="['token_reuse', 'login_locked', 'admin_denied'].includes(e.kind) ? 'text-red-600 dark:text-red-400' : 'text-slate-700 dark:text-slate-200'">
                    {{ fmt.eventLabel(e.kind, e.label) }}
                  </p>
                  <p class="text-xs text-slate-400">{{ e.ip || '—' }} · {{ fmt.dateTime(e.at) }}</p>
                </li>
              </ul>
            </AdminCard>
          </div>

          <!-- What the team did -->
          <AdminCard v-if="user.history.length" :title="$t('admin.users.history')">
            <ul class="divide-y divide-slate-100 text-sm dark:divide-hairline">
              <li v-for="(h, i) in user.history" :key="i" class="py-2">
                <p class="font-medium text-slate-700 dark:text-slate-200">{{ fmt.actionLabel(h.action) }}</p>
                <p class="text-xs text-slate-400">{{ h.summary }}</p>
                <p class="text-xs text-slate-400">{{ h.actor }} · {{ fmt.dateTime(h.at) }}</p>
              </li>
            </ul>
          </AdminCard>
        </div>

        <!-- Actions -->
        <aside class="min-w-0">
          <AdminCard :title="$t('admin.users.actions')" class="lg:sticky lg:top-24">
            <p v-if="isTeam && !canTouch && !isMe" class="mb-2 text-xs text-slate-400">{{ $t('admin.users.roleHint') }}</p>
            <div class="-mx-2 grid gap-0.5">
              <template v-if="admin.can('users.manage') && canTouch">
                <button v-if="user.is_active" type="button" :class="ACTION" @click="openDialog('disable')">
                  <Icon name="lock" class="h-4 w-4 text-slate-400" /> {{ $t('admin.users.disable') }}
                </button>
                <button v-else type="button" :class="ACTION" :disabled="busy" @click="setActive(true)">
                  <Icon name="checkCircle" class="h-4 w-4 text-slate-400" /> {{ $t('admin.users.enable') }}
                </button>
                <button type="button" :class="ACTION" :disabled="busy" @click="signOut">
                  <Icon name="logout" class="h-4 w-4 text-slate-400" /> {{ $t('admin.users.signOut') }}
                </button>
                <button v-if="user.is_active" type="button" :class="ACTION" :disabled="busy" @click="makeResetLink">
                  <Icon name="key" class="h-4 w-4 text-slate-400" /> {{ $t('admin.users.resetLink') }}
                </button>
              </template>
              <button v-if="admin.can('users.quota')" type="button" :class="ACTION" @click="openDialog('quota')">
                <Icon name="bot" class="h-4 w-4 text-slate-400" /> {{ $t('admin.users.quota') }}
              </button>
              <button v-if="admin.can('users.coins')" type="button" :class="ACTION" @click="openDialog('coins')">
                <Icon name="coin" class="h-4 w-4 text-slate-400" /> {{ $t('admin.users.coinsAdjust') }}
              </button>
              <template v-if="admin.can('staff.manage') && !isMe && !user.is_superuser">
                <button v-if="user.is_active" type="button" :class="ACTION" @click="openDialog('role')">
                  <Icon name="shield" class="h-4 w-4 text-slate-400" /> {{ $t('admin.users.role') }}
                </button>
                <button v-if="user.totp_enabled" type="button" :class="ACTION" :disabled="busy" @click="resetTotp">
                  <Icon name="refresh" class="h-4 w-4 text-slate-400" /> {{ $t('admin.users.resetTotp') }}
                </button>
              </template>
              <button v-if="admin.can('users.export')" type="button" :class="ACTION" :disabled="busy" @click="exportJson">
                <Icon name="download" class="h-4 w-4 text-slate-400" /> {{ $t('admin.users.exportJson') }}
              </button>
              <button
                v-if="admin.can('users.delete') && canTouch && !user.is_superuser"
                type="button"
                :class="ACTION"
                class="!text-red-600 hover:!bg-red-50 dark:!text-red-400 dark:hover:!bg-red-500/10"
                @click="openDialog('delete')"
              >
                <Icon name="trash" class="h-4 w-4" /> {{ $t('admin.users.delete') }}
              </button>
            </div>
          </AdminCard>
        </aside>
      </div>

      <!-- Disable -->
      <AdminModal :open="dialog === 'disable'" :title="$t('admin.users.disable')" @close="dialog = ''">
        <form class="space-y-4" @submit.prevent="setActive(false)">
          <div>
            <label for="disable-reason" class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.common.reason') }}</label>
            <textarea id="disable-reason" v-model="form.reason" rows="3" maxlength="300" class="zx-input" :placeholder="$t('admin.users.disableReason')" />
          </div>
          <p v-if="formError" class="text-sm text-red-600 dark:text-red-400">{{ formError }}</p>
          <div class="flex justify-end gap-2">
            <AppButton variant="ghost" size="sm" type="button" @click="dialog = ''">{{ $t('admin.common.cancel') }}</AppButton>
            <AppButton size="sm" type="submit" icon="lock" :disabled="busy || !form.reason.trim()">{{ $t('admin.users.disable') }}</AppButton>
          </div>
        </form>
      </AdminModal>

      <!-- Reset link -->
      <AdminModal :open="dialog === 'reset'" :title="$t('admin.users.resetLink')" :text="$t('admin.users.resetHint')" @close="dialog = ''">
        <div class="flex gap-2">
          <input :value="form.link" readonly class="zx-input min-w-0 flex-1 font-mono text-xs" aria-label="URL" @focus="$event.target.select()" />
          <AppButton size="sm" :icon="copied ? 'check' : 'copy'" type="button" @click="copyLink">{{ copied ? $t('admin.common.copied') : $t('admin.common.copy') }}</AppButton>
        </div>
        <p class="mt-2 text-xs text-slate-400">{{ fmt.dateTime(form.expires) }}</p>
      </AdminModal>

      <!-- AI allowance -->
      <AdminModal :open="dialog === 'quota'" :title="$t('admin.users.quota')" @close="dialog = ''">
        <form class="space-y-4" @submit.prevent="saveQuota">
          <div class="grid gap-3 sm:grid-cols-2">
            <div>
              <label for="quota-tier" class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.users.tier') }}</label>
              <select id="quota-tier" v-model="form.tier" class="zx-input py-2.5">
                <option v-for="tier in TIERS" :key="tier" :value="tier">{{ $t(`admin.tiers.${tier}`) }}</option>
              </select>
            </div>
            <div>
              <label for="quota-limit" class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.users.limit') }}</label>
              <input id="quota-limit" v-model.number="form.limit" type="number" min="0" max="100000000" step="1000" class="zx-input py-2.5" />
            </div>
          </div>
          <CheckBox v-model="form.resetUsage" shape="square" :label="$t('admin.users.resetUsage')" />
          <p v-if="formError" class="text-sm text-red-600 dark:text-red-400">{{ formError }}</p>
          <div class="flex justify-end gap-2">
            <AppButton variant="ghost" size="sm" type="button" @click="dialog = ''">{{ $t('admin.common.cancel') }}</AppButton>
            <AppButton size="sm" type="submit" :disabled="busy">{{ $t('admin.common.save') }}</AppButton>
          </div>
        </form>
      </AdminModal>

      <!-- Coins -->
      <AdminModal :open="dialog === 'coins'" :title="$t('admin.users.coinsAdjust')" @close="dialog = ''">
        <form class="space-y-4" @submit.prevent="saveCoins">
          <div>
            <label for="coins-delta" class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.users.delta') }}</label>
            <input id="coins-delta" v-model="form.delta" type="number" min="-100000" max="100000" step="1" class="zx-input py-2.5" placeholder="50" />
          </div>
          <div>
            <label for="coins-reason" class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.users.coinsReason') }}</label>
            <input id="coins-reason" v-model="form.coinsReason" maxlength="200" class="zx-input py-2.5" />
          </div>
          <p v-if="formError" class="text-sm text-red-600 dark:text-red-400">{{ formError }}</p>
          <div class="flex justify-end gap-2">
            <AppButton variant="ghost" size="sm" type="button" @click="dialog = ''">{{ $t('admin.common.cancel') }}</AppButton>
            <AppButton size="sm" type="submit" :disabled="busy || !parseInt(form.delta, 10) || !form.coinsReason.trim()">{{ $t('admin.common.save') }}</AppButton>
          </div>
        </form>
      </AdminModal>

      <!-- Role -->
      <AdminModal :open="dialog === 'role'" :title="$t('admin.users.role')" :text="$t('admin.users.roleHint')" @close="dialog = ''">
        <form class="space-y-4" @submit.prevent="saveRole">
          <div class="grid gap-1.5">
            <CheckBox v-for="role in ROLES" :key="role || 'learner'" v-model="form.role" type="radio" :value="role">
              {{ $t(`admin.roles.${role || 'learner'}`) }}
            </CheckBox>
          </div>
          <p v-if="formError" class="text-sm text-red-600 dark:text-red-400">{{ formError }}</p>
          <div class="flex justify-end gap-2">
            <AppButton variant="ghost" size="sm" type="button" @click="dialog = ''">{{ $t('admin.common.cancel') }}</AppButton>
            <AppButton size="sm" type="submit" :disabled="busy || form.role === (user.role || '')">{{ $t('admin.common.save') }}</AppButton>
          </div>
        </form>
      </AdminModal>

      <!-- Delete -->
      <AdminModal :open="dialog === 'delete'" :title="$t('admin.users.delete')" :text="$t('admin.users.deleteText', { email: user.email })" @close="dialog = ''">
        <form class="space-y-4" @submit.prevent="removeUser">
          <input v-model="form.confirm" class="zx-input py-2.5" :placeholder="user.email" autocomplete="off" spellcheck="false" :aria-label="user.email" />
          <p v-if="formError" class="text-sm text-red-600 dark:text-red-400">{{ formError }}</p>
          <div class="flex justify-end gap-2">
            <AppButton variant="ghost" size="sm" type="button" @click="dialog = ''">{{ $t('admin.common.cancel') }}</AppButton>
            <button
              type="submit"
              class="pill justify-center bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
              :disabled="busy || form.confirm.trim().toLowerCase() !== user.email.toLowerCase()"
            >
              <Icon name="trash" class="h-4 w-4" /> {{ $t('admin.users.delete') }}
            </button>
          </div>
        </form>
      </AdminModal>
    </template>
  </div>
</template>
