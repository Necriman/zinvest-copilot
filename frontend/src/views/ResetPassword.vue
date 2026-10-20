<script setup>
// Setting a new password from a one-time link the team made (Admin → Users).
// The token leaves the address bar as soon as the page reads it, so it does not
// linger in history or get copied along with the URL.
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import FormField from '@/components/ui/FormField.vue'
import Icon from '@/components/ui/Icon.vue'
import { resetPassword } from '@/api/account'
import { passwordProblem, serverDown } from '@/api/authErrors'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const token = ref(typeof route.query.token === 'string' ? route.query.token : '')
const password = ref('')
const repeat = ref('')
const error = ref('')
const loading = ref(false)
const done = ref(false)

onMounted(() => {
  if (route.query.token) router.replace({ query: {} })
})

async function submit() {
  error.value = ''
  if (password.value !== repeat.value) {
    error.value = t('admin.reset.mismatch')
    return
  }
  loading.value = true
  try {
    await resetPassword(token.value, password.value)
    done.value = true
    password.value = ''
    repeat.value = ''
  } catch (e) {
    const data = e?.response?.data
    if (serverDown(e)) error.value = t('errors.serverDown')
    else if (data?.code === 'bad_token') error.value = t('admin.reset.badToken')
    else error.value = passwordProblem(e) || data?.detail || t('admin.common.error')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">{{ $t('admin.reset.title') }}</h1>
    <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">{{ $t('admin.reset.text') }}</p>

    <div v-if="done" class="mt-8 rounded-2xl bg-green-50 px-4 py-4 text-sm text-green-800 dark:bg-green-500/10 dark:text-green-200" role="status">
      <p class="flex items-center gap-2 font-semibold"><Icon name="checkCircle" class="h-4 w-4" /> {{ $t('admin.reset.done') }}</p>
      <RouterLink :to="{ name: 'login' }" class="mt-3 inline-flex font-semibold text-brand-700 hover:underline dark:text-brand-300">
        {{ $t('admin.reset.signIn') }} →
      </RouterLink>
    </div>

    <p v-else-if="!token" class="mt-8 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:bg-amber-500/10 dark:text-amber-200" role="alert">
      {{ $t('admin.reset.noToken') }}
    </p>

    <form v-else class="mt-8 space-y-5" novalidate @submit.prevent="submit">
      <p v-if="error" role="alert" class="flex items-start gap-2.5 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">
        <Icon name="shield" class="mt-0.5 h-4 w-4 shrink-0" />
        {{ error }}
      </p>
      <FormField
        v-model="password"
        type="password"
        icon="lock"
        required
        autocomplete="new-password"
        :label="$t('admin.reset.password')"
        :hint="$t('admin.reset.hint')"
      />
      <FormField v-model="repeat" type="password" icon="lock" required autocomplete="new-password" :label="$t('admin.reset.repeat')" />
      <button
        type="submit"
        class="flex w-full items-center justify-center gap-2 rounded-full bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:opacity-50"
        :disabled="loading || password.length < 10 || !repeat"
      >
        {{ $t('admin.reset.submit') }}
      </button>
    </form>
  </div>
</template>
