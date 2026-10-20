<script setup>
// The page the confirmation link opens. It confirms on arrival and says how it
// went; the token leaves the address bar immediately, like the reset page. A
// link mailed after an email change moves the account to the new address.
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import Icon from '@/components/ui/Icon.vue'
import { verifyEmail } from '@/api/account'
import { useAuthStore } from '@/store/auth'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const state = ref('checking') // checking | done | moved | failed
const error = ref('')
const moved = ref('') // the account's new address, after an email change

onMounted(async () => {
  const token = typeof route.query.token === 'string' ? route.query.token : ''
  if (route.query.token) router.replace({ query: {} })
  if (!token) {
    state.value = 'failed'
    error.value = t('admin.verify.failed')
    return
  }
  try {
    const result = await verifyEmail(token, locale.value)
    if (result?.changed) {
      // The account moved to this address and every session was ended: sign in again.
      moved.value = result.email || ''
      auth.clearSession()
      state.value = 'moved'
      return
    }
    state.value = 'done'
    // Someone already signed in sees the reminder disappear straight away.
    if (auth.isAuthenticated) auth.fetchMe().catch(() => {})
  } catch (e) {
    state.value = 'failed'
    const data = e?.response?.data
    error.value = data?.code === 'bad_token' ? t('admin.verify.failed') : data?.detail || t('admin.verify.failed')
  }
})
</script>

<template>
  <div>
    <h1 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">{{ $t('admin.verify.bannerTitle') }}</h1>

    <p v-if="state === 'checking'" class="mt-6 text-sm text-slate-500" role="status">{{ $t('admin.verify.checking') }}</p>

    <div v-else-if="state === 'done'" class="mt-6 space-y-4">
      <p class="flex items-start gap-2.5 rounded-2xl bg-green-50 px-4 py-3 text-sm text-green-800 dark:bg-green-500/10 dark:text-green-200" role="status">
        <Icon name="checkCircle" class="mt-0.5 h-4 w-4 shrink-0" />
        {{ $t('admin.verify.done') }}
      </p>
      <RouterLink
        :to="{ name: auth.isAuthenticated ? 'dashboard' : 'login' }"
        class="inline-flex rounded-full bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700"
      >
        {{ auth.isAuthenticated ? $t('admin.verify.toApp') : $t('admin.reset.signIn') }}
      </RouterLink>
    </div>

    <div v-else-if="state === 'moved'" class="mt-6 space-y-4">
      <p class="flex items-start gap-2.5 rounded-2xl bg-green-50 px-4 py-3 text-sm text-green-800 dark:bg-green-500/10 dark:text-green-200" role="status">
        <Icon name="checkCircle" class="mt-0.5 h-4 w-4 shrink-0" />
        {{ $t('settings.emailMoved', { email: moved }) }}
      </p>
      <RouterLink
        :to="{ name: 'login' }"
        class="inline-flex rounded-full bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700"
      >
        {{ $t('admin.reset.signIn') }}
      </RouterLink>
    </div>

    <div v-else class="mt-6 space-y-4">
      <p class="flex items-start gap-2.5 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300" role="alert">
        <Icon name="shield" class="mt-0.5 h-4 w-4 shrink-0" />
        {{ error }}
      </p>
      <RouterLink :to="{ name: 'login' }" class="inline-flex text-sm font-semibold text-brand-600 hover:underline dark:text-brand-300">
        {{ $t('admin.forgot.back') }}
      </RouterLink>
    </div>
  </div>
</template>
