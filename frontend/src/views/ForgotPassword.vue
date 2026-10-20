<script setup>
// "Forgot your password?" — the self-service half of the reset flow. The answer
// is the same whatever the address, so this page never says whether an account
// exists; it just reports that a letter is on its way if there is one.
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

import FormField from '@/components/ui/FormField.vue'
import Icon from '@/components/ui/Icon.vue'
import { forgotPassword } from '@/api/account'
import { serverDown } from '@/api/authErrors'

const { t, locale } = useI18n()

const email = ref('')
const loading = ref(false)
const error = ref('')
const sent = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await forgotPassword(email.value.trim(), locale.value)
    sent.value = true
  } catch (e) {
    error.value = serverDown(e) ? t('errors.serverDown') : e?.response?.data?.detail || t('admin.common.error')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">{{ $t('admin.forgot.title') }}</h1>
    <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">{{ $t('admin.forgot.text') }}</p>

    <div v-if="sent" class="mt-8 space-y-4">
      <p class="flex items-start gap-2.5 rounded-2xl bg-green-50 px-4 py-3 text-sm text-green-800 dark:bg-green-500/10 dark:text-green-200" role="status">
        <Icon name="mail" class="mt-0.5 h-4 w-4 shrink-0" />
        {{ $t('admin.forgot.sent') }}
      </p>
      <p class="text-xs text-slate-400">{{ $t('admin.forgot.spam') }}</p>
      <RouterLink :to="{ name: 'login' }" class="inline-flex text-sm font-semibold text-brand-600 hover:underline dark:text-brand-300">
        {{ $t('admin.forgot.back') }}
      </RouterLink>
    </div>

    <form v-else class="mt-8 space-y-5" novalidate @submit.prevent="submit">
      <p v-if="error" role="alert" class="flex items-start gap-2.5 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">
        <Icon name="shield" class="mt-0.5 h-4 w-4 shrink-0" />
        {{ error }}
      </p>

      <FormField
        v-model="email"
        type="email"
        icon="mail"
        required
        autocomplete="email"
        :label="$t('auth.fields.email')"
        :placeholder="$t('auth.fields.emailPlaceholder')"
      />

      <button
        type="submit"
        class="flex w-full items-center justify-center gap-2 rounded-full bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:opacity-50"
        :disabled="loading || !email.trim()"
      >
        {{ $t('admin.forgot.submit') }}
      </button>

      <RouterLink :to="{ name: 'login' }" class="block text-center text-sm font-semibold text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
        {{ $t('admin.forgot.back') }}
      </RouterLink>
    </form>
  </div>
</template>
