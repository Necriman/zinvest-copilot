<script setup>
/**
 * Account — sign-in email, the ways in, and the password.
 *
 * Email and password sign-in and "Continue with Google" lead to one and the
 * same account when the address matches (accounts.google). An account made
 * with Google has no password yet; it gets one through the emailed link, and
 * from then on both ways in work. Changing the email or the password needs the
 * current password, so both forms wait until there is one. A new email only
 * takes over once the link mailed to it is opened.
 */
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { changeEmail, changePassword, forgotPassword } from '@/api/account'
import Icon from '@/components/ui/Icon.vue'
import { useTask } from '@/composables/useTask'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const { locale } = useI18n()
const email = useTask()
const password = useTask()
const setPassword = useTask()

// Older sessions may hold a user object from before these fields existed:
// treat a missing flag as "has a password", the old default.
const hasPassword = computed(() => auth.user?.has_password !== false)
const googleLinked = computed(() => !!auth.user?.google_linked)

// Stays on once sent: the letter is the next step, not a passing toast.
const linkSent = ref(false)
async function mailPasswordLink() {
  linkSent.value = await setPassword.run(() => forgotPassword(auth.user.email, locale.value))
}

const emailForm = reactive({ open: false, new_email: '', password: '' })
const pwForm = reactive({ current: '', next: '', confirm: '' })

const mismatch = computed(() => !!pwForm.confirm && pwForm.next !== pwForm.confirm)

// The address a confirmation link went to: the email changes only once it is opened.
const pendingEmail = ref('')
function saveEmail() {
  email.run(async () => {
    const { pending_email: pending, detail, ...me } = await changeEmail(emailForm.password, emailForm.new_email, locale.value)
    auth.setUser(me)
    pendingEmail.value = pending || ''
    Object.assign(emailForm, { open: false, new_email: '', password: '' })
  })
}

async function savePassword() {
  if (mismatch.value) return
  const ok = await password.run(() => changePassword(pwForm.current, pwForm.next))
  if (ok) Object.assign(pwForm, { current: '', next: '', confirm: '' })
}
</script>

<template>
  <div>
    <h2 class="text-base font-bold text-slate-900 dark:text-white">{{ $t('settings.account') }}</h2>
    <p class="mt-1 text-sm text-slate-500">{{ $t('settings.accountHint') }}</p>

    <!-- Email -->
    <div class="mt-6 border-b border-slate-100 pb-6 dark:border-hairline">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0">
          <p class="text-xs font-semibold text-slate-500">{{ $t('settings.email') }}</p>
          <p class="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{{ auth.user?.email }}</p>
        </div>
        <button
          v-if="hasPassword"
          type="button"
          class="shrink-0 text-sm font-semibold text-brand-600 hover:underline"
          @click="emailForm.open = !emailForm.open"
        >
          {{ $t(emailForm.open ? 'common.cancel' : 'settings.changeEmail') }}
        </button>
      </div>

      <form v-if="emailForm.open" class="mt-4 grid gap-3 sm:grid-cols-2" @submit.prevent="saveEmail">
        <label class="block">
          <span class="mb-1.5 block text-xs font-semibold text-slate-500">{{ $t('settings.newEmail') }}</span>
          <input v-model="emailForm.new_email" type="email" required class="zx-input" />
        </label>
        <label class="block">
          <span class="mb-1.5 block text-xs font-semibold text-slate-500">{{ $t('settings.currentPassword') }}</span>
          <input v-model="emailForm.password" type="password" required autocomplete="current-password" class="zx-input" />
        </label>
        <div class="flex items-center gap-3 sm:col-span-2">
          <button
            type="submit"
            :disabled="email.state.busy"
            class="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            {{ email.state.busy ? $t('settings.saving') : $t('settings.updateEmail') }}
          </button>
          <span v-if="email.state.error" class="text-sm text-red-500">{{ email.state.error }}</span>
        </div>
      </form>
      <p v-if="pendingEmail" class="mt-2 text-sm text-green-600 dark:text-green-400" role="status">
        {{ $t('settings.emailPending', { email: pendingEmail }) }}
      </p>
    </div>

    <!-- Ways in: one account, by password or by Google -->
    <div class="mt-6 border-b border-slate-100 pb-6 dark:border-hairline">
      <p class="text-xs font-semibold text-slate-500">{{ $t('settings.signIn.title') }}</p>
      <ul class="mt-3 grid gap-2">
        <li class="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 dark:border-hairline">
          <svg class="h-5 w-5 shrink-0" viewBox="0 0 48 48" aria-hidden="true">
            <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
            <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
            <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
            <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
          </svg>
          <div class="min-w-0">
            <p class="text-sm font-semibold text-slate-800 dark:text-slate-100">Google</p>
            <p class="text-xs text-slate-500">
              {{ googleLinked ? $t('settings.signIn.googleOn') : $t('settings.signIn.googleOff') }}
            </p>
          </div>
          <Icon v-if="googleLinked" name="check" class="ml-auto h-4 w-4 shrink-0 text-green-600 dark:text-green-400" />
        </li>
        <li class="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 dark:border-hairline">
          <Icon name="lock" class="h-5 w-5 shrink-0 text-slate-400" />
          <div class="min-w-0">
            <p class="text-sm font-semibold text-slate-800 dark:text-slate-100">{{ $t('settings.password') }}</p>
            <p class="text-xs text-slate-500">
              {{ hasPassword ? $t('settings.signIn.passwordOn') : $t('settings.signIn.passwordOff') }}
            </p>
          </div>
          <Icon v-if="hasPassword" name="check" class="ml-auto h-4 w-4 shrink-0 text-green-600 dark:text-green-400" />
        </li>
      </ul>
      <p class="mt-2 text-xs text-slate-400">{{ $t('settings.signIn.oneAccount') }}</p>
    </div>

    <!-- No password yet (made with Google): set one through the emailed link -->
    <div v-if="!hasPassword" class="mt-6">
      <p class="text-xs font-semibold text-slate-500">{{ $t('settings.password') }}</p>
      <p class="mt-2 text-sm text-slate-600 dark:text-slate-300">{{ $t('settings.signIn.setPasswordBody') }}</p>
      <div class="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="button"
          :disabled="setPassword.state.busy || linkSent"
          class="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
          @click="mailPasswordLink"
        >
          {{ setPassword.state.busy ? $t('settings.saving') : $t('settings.signIn.setPassword') }}
        </button>
        <span v-if="setPassword.state.error" class="text-sm text-red-500">{{ setPassword.state.error }}</span>
        <span v-if="linkSent" class="text-sm text-green-600 dark:text-green-400">
          {{ $t('settings.signIn.linkSent', { email: auth.user?.email }) }}
        </span>
      </div>
    </div>

    <!-- Password -->
    <form v-else class="mt-6" @submit.prevent="savePassword">
      <p class="text-xs font-semibold text-slate-500">{{ $t('settings.password') }}</p>
      <div class="mt-3 grid gap-3 sm:grid-cols-3">
        <label class="block">
          <span class="mb-1.5 block text-xs text-slate-400">{{ $t('settings.currentPassword') }}</span>
          <input v-model="pwForm.current" type="password" required autocomplete="current-password" class="zx-input" />
        </label>
        <label class="block">
          <span class="mb-1.5 block text-xs text-slate-400">{{ $t('settings.newPassword') }}</span>
          <input v-model="pwForm.next" type="password" required autocomplete="new-password" class="zx-input" />
        </label>
        <label class="block">
          <span class="mb-1.5 block text-xs text-slate-400">{{ $t('settings.confirmPassword') }}</span>
          <input
            v-model="pwForm.confirm"
            type="password"
            required
            autocomplete="new-password"
            class="zx-input"
            :class="mismatch ? 'border-red-400' : ''"
          />
        </label>
      </div>
      <p class="mt-2 text-xs text-slate-400">{{ $t('settings.passwordHint') }}</p>
      <div class="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="submit"
          :disabled="password.state.busy || mismatch"
          class="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
        >
          {{ password.state.busy ? $t('settings.saving') : $t('settings.updatePassword') }}
        </button>
        <span v-if="mismatch" class="text-sm text-red-500">{{ $t('settings.passwordMismatch') }}</span>
        <span v-else-if="password.state.error" class="text-sm text-red-500">{{ password.state.error }}</span>
        <span v-if="password.state.saved" class="text-sm text-green-600 dark:text-green-400">
          {{ $t('settings.passwordUpdated') }}
        </span>
      </div>
    </form>
  </div>
</template>
