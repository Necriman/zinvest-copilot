<script setup>
// Reminder to confirm the address. Shown only while the account is unconfirmed,
// and hideable for a day — nagging someone every single visit is how people
// learn to ignore the whole top of the page.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import Icon from '@/components/ui/Icon.vue'
import { resendVerification } from '@/api/account'
import { useAuthStore } from '@/store/auth'

const { t, locale } = useI18n()
const auth = useAuthStore()

const STORAGE_KEY = 'zx-verify-hidden-until'
const DAY = 24 * 60 * 60 * 1000

function hiddenUntil() {
  try {
    return Number(localStorage.getItem(STORAGE_KEY) || 0)
  } catch {
    return 0
  }
}

const snoozed = ref(hiddenUntil() > Date.now())
const busy = ref(false)
const sent = ref(false)
const error = ref('')

const show = computed(() => auth.user && auth.user.email_verified === false && !snoozed.value)

function hide() {
  snoozed.value = true
  try {
    localStorage.setItem(STORAGE_KEY, String(Date.now() + DAY))
  } catch {
    /* private mode: hidden for this visit only */
  }
}

async function resend() {
  busy.value = true
  error.value = ''
  try {
    await resendVerification(locale.value)
    sent.value = true
  } catch (e) {
    error.value = e?.response?.data?.detail || t('admin.common.error')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div
    v-if="show"
    class="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-400/25 dark:bg-amber-500/10 dark:text-amber-100"
    role="status"
  >
    <Icon name="mail" class="mt-0.5 h-4 w-4 shrink-0 opacity-80" />
    <div class="min-w-0 flex-1">
      <p class="font-semibold">{{ $t('admin.verify.bannerTitle') }}</p>
      <p class="mt-0.5">{{ $t('admin.verify.bannerText', { email: auth.user.email }) }}</p>
      <p v-if="sent" class="mt-1.5 font-semibold">{{ $t('admin.verify.resent') }}</p>
      <p v-else-if="error" class="mt-1.5 font-semibold">{{ error }}</p>
      <button
        v-else
        type="button"
        class="mt-1.5 font-semibold underline underline-offset-2 disabled:opacity-50"
        :disabled="busy"
        @click="resend"
      >
        {{ $t('admin.verify.resend') }}
      </button>
    </div>
    <button
      type="button"
      class="-mr-1 -mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full opacity-60 transition hover:bg-black/5 hover:opacity-100 dark:hover:bg-white/10"
      :aria-label="$t('admin.banner.dismiss')"
      @click="hide"
    >
      <Icon name="x" class="h-4 w-4" />
    </button>
  </div>
</template>
