<script setup>
/**
 * Privacy & security — where you're signed in, downloading your data, and
 * deleting the account.
 *
 * Sessions are grouped per device (one refresh-token family each). The current
 * device can't be revoked from here; that's what Log out is for.
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import { deleteAccount, downloadMyData, listSessions, revokeOtherSessions, revokeSession } from '@/api/account'
import { useTask } from '@/composables/useTask'
import { relativeTime } from '@/utils/format'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const router = useRouter()
const sessionsTask = useTask()
const dangerTask = useTask()
const exportTask = useTask()

const sessions = ref([])
const loading = ref(true)
const confirmDelete = ref(false)
const deletePassword = ref('') // the password, or the email for a Google-only account
const needsReauth = ref(false) // a Google-only account signed in too long ago
// No password (signed up with Google): deletion is confirmed with the email.
const hasPassword = computed(() => auth.user?.has_password !== false)

const otherCount = computed(() => sessions.value.filter((s) => !s.current).length)

async function load() {
  loading.value = true
  try {
    sessions.value = await listSessions()
  } catch {
    sessions.value = []
  } finally {
    loading.value = false
  }
}
onMounted(load)

const signOut = (familyId) =>
  sessionsTask.run(async () => {
    await revokeSession(familyId)
    await load()
  })

const signOutOthers = () =>
  sessionsTask.run(async () => {
    await revokeOtherSessions()
    await load()
  })

async function confirmDeleteAccount() {
  needsReauth.value = false
  const proof = hasPassword.value ? { password: deletePassword.value } : { confirm: deletePassword.value }
  const ok = await dangerTask.run(async () => {
    try {
      await deleteAccount(proof)
    } catch (e) {
      needsReauth.value = e?.response?.data?.code === 'reauth_required'
      throw e
    }
  })
  if (!ok) return
  auth.clearSession()
  router.push({ name: 'landing' })
}

async function signInAgain() {
  await auth.logout()
  router.push({ name: 'login', query: { redirect: '/app/settings?tab=privacy' } })
}
</script>

<template>
  <div>
    <h2 class="text-base font-bold text-slate-900 dark:text-white">{{ $t('settings.privacy') }}</h2>
    <p class="mt-1 text-sm text-slate-500">{{ $t('settings.privacyHint') }}</p>

    <!-- Sessions -->
    <div class="mt-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <p class="text-xs font-semibold text-slate-500">{{ $t('settings.sessions') }}</p>
        <button
          v-if="otherCount"
          type="button"
          :disabled="sessionsTask.state.busy"
          class="text-sm font-semibold text-brand-600 hover:underline disabled:opacity-50"
          @click="signOutOthers"
        >
          {{ $t('settings.signOutOthers', { n: otherCount }) }}
        </button>
      </div>

      <LoadingSkeleton v-if="loading" height="h-16" rounded="rounded-2xl" class="mt-3" />
      <ul v-else class="mt-3 space-y-2">
        <li
          v-for="s in sessions"
          :key="s.family_id"
          class="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 dark:border-hairline"
        >
          <Icon name="shield" class="h-4 w-4 shrink-0" :class="s.current ? 'text-green-600' : 'text-slate-400'" />
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
              {{ s.device_name }}
              <span v-if="s.current" class="ml-1 text-xs font-bold text-green-600">
                · {{ $t('settings.thisDevice') }}
              </span>
            </p>
            <p class="truncate text-xs text-slate-400">
              {{ s.ip_address || '—' }} · {{ $t('settings.signedIn', { when: relativeTime(s.created_at) }) }}
            </p>
          </div>
          <button
            v-if="!s.current"
            type="button"
            :disabled="sessionsTask.state.busy"
            class="shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-500 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50 dark:hover:bg-red-500/10"
            @click="signOut(s.family_id)"
          >
            {{ $t('settings.signOut') }}
          </button>
        </li>
      </ul>
      <p v-if="sessionsTask.state.error" class="mt-2 text-sm text-red-500">{{ sessionsTask.state.error }}</p>
    </div>

    <!-- Your data: the same file the team hands out for a data request. -->
    <div class="mt-8 rounded-2xl border border-slate-200 p-5 dark:border-hairline">
      <p class="text-sm font-bold text-slate-900 dark:text-white">{{ $t('settings.yourData') }}</p>
      <p class="mt-1 text-sm text-slate-500">{{ $t('settings.yourDataHint') }}</p>
      <button
        type="button"
        :disabled="exportTask.state.busy"
        class="mt-4 inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50 dark:border-hairline dark:text-slate-200 dark:hover:bg-surface-2"
        @click="exportTask.run(downloadMyData)"
      >
        <Icon name="download" class="h-4 w-4" />
        {{ exportTask.state.busy ? $t('settings.preparingData') : $t('settings.downloadData') }}
      </button>
      <p v-if="exportTask.state.error" class="mt-2 text-sm text-red-500">{{ exportTask.state.error }}</p>
    </div>

    <!-- Danger zone. Confirmation is inline rather than a modal: deletion needs
         the password, and a modal would cover the field that collects it. -->
    <div class="mt-8 rounded-2xl border border-red-200 p-5 dark:border-red-500/30">
      <p class="text-sm font-bold text-red-600 dark:text-red-400">{{ $t('settings.deleteAccount') }}</p>
      <p class="mt-1 text-sm text-slate-500">{{ $t('settings.deleteAccountHint') }}</p>

      <button
        v-if="!confirmDelete"
        type="button"
        class="mt-4 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700"
        @click="confirmDelete = true"
      >
        {{ $t('settings.deleteAccount') }}
      </button>

      <form v-else class="mt-4" @submit.prevent="confirmDeleteAccount">
        <p class="text-sm font-semibold text-slate-700 dark:text-slate-200">
          {{ hasPassword ? $t('settings.deleteAccountConfirm') : $t('settings.deleteAccountConfirmEmail', { email: auth.user?.email }) }}
        </p>
        <label class="mt-3 block max-w-xs">
          <span class="mb-1.5 block text-xs font-semibold text-slate-500">
            {{ hasPassword ? $t('settings.currentPassword') : $t('settings.yourEmail') }}
          </span>
          <input
            v-if="hasPassword"
            v-model="deletePassword"
            type="password"
            required
            autocomplete="current-password"
            class="zx-input"
          />
          <input v-else v-model="deletePassword" type="email" required autocomplete="off" class="zx-input" />
        </label>
        <div class="mt-3 flex flex-wrap items-center gap-3">
          <button
            type="submit"
            :disabled="dangerTask.state.busy || !deletePassword"
            class="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
          >
            {{ dangerTask.state.busy ? $t('settings.saving') : $t('settings.deleteForever') }}
          </button>
          <button
            type="button"
            class="rounded-xl px-3 py-2 text-sm font-medium text-slate-500 transition hover:bg-slate-100 dark:hover:bg-surface-2"
            @click="confirmDelete = false; deletePassword = ''"
          >
            {{ $t('common.cancel') }}
          </button>
          <span v-if="dangerTask.state.error" class="text-sm text-red-600" role="alert">{{ dangerTask.state.error }}</span>
          <button
            v-if="needsReauth"
            type="button"
            class="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 dark:border-hairline dark:text-slate-200 dark:hover:bg-surface-2"
            @click="signInAgain"
          >
            {{ $t('settings.signInAgain') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
