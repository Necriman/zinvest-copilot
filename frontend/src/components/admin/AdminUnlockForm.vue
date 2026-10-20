<script setup>
// "Confirm it's you": the password, plus a code from the authenticator app once
// two-factor is on. Used to open the panel on a device and, later, to confirm a
// change when the last confirmation is older than the sudo window. If the team
// requires two-factor and it is not set up yet, the form turns into the setup.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import AdminTotpSetup from '@/components/admin/AdminTotpSetup.vue'
import AppButton from '@/components/ui/AppButton.vue'
import FormField from '@/components/ui/FormField.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAuthStore } from '@/store/auth'

const props = defineProps({
  mode: { type: String, default: 'unlock' }, // unlock | sudo
  cancellable: { type: Boolean, default: true },
})
const emit = defineEmits(['done', 'cancel'])

const { t } = useI18n()
const admin = useAdmin()

const password = ref('')
const code = ref('')
const busy = ref(false)
const error = ref('')
const errorField = ref('') // password | code
const needsSetup = ref(!!admin.me.value?.require_2fa && !admin.me.value?.totp_enabled)

const auth = useAuthStore()
const router = useRouter()
const withCode = computed(() => !!admin.me.value?.totp_enabled)
// A Google-only account has no password: the authenticator code is the proof,
// or, before two-factor is on, a sign-in from the last fifteen minutes.
const noPassword = computed(() => admin.me.value?.has_password === false)
const reauth = ref(false)
const ready = computed(
  () => (noPassword.value || !!password.value) && (!withCode.value || code.value.replace(/\D/g, '').length === 6),
)

async function signInAgain() {
  await auth.logout()
  router.push({ name: 'login', query: { redirect: '/admin-panel' } })
}

async function submit() {
  if (!ready.value || busy.value) return
  busy.value = true
  error.value = ''
  errorField.value = ''
  reauth.value = false
  try {
    const me = await adminApi.unlock(noPassword.value ? '' : password.value, withCode.value ? code.value.replace(/\D/g, '') : '')
    admin.setMe(me)
    password.value = ''
    code.value = ''
    emit('done', me)
  } catch (e) {
    const reason = e?.response?.data?.code
    if (reason === 'totp_setup_required') {
      needsSetup.value = true
    } else if (reason === 'reauth_required') {
      reauth.value = true
      error.value = t('admin.unlock.reauth')
      errorField.value = 'form'
    } else if (reason === 'bad_password') {
      error.value = t('admin.unlock.badPassword')
      errorField.value = 'password'
    } else if (reason === 'bad_code') {
      error.value = t('admin.unlock.badCode')
      errorField.value = 'code'
      code.value = ''
    } else if (reason === 'rate_limited') {
      error.value = t('admin.unlock.rateLimited')
      errorField.value = 'password'
    } else {
      error.value = admin.errorText(e, t)
      errorField.value = 'password'
    }
  } finally {
    busy.value = false
  }
}

const submitLabel = computed(() => t(props.mode === 'sudo' ? 'admin.unlock.confirm' : 'admin.unlock.submit'))
</script>

<template>
  <div v-if="needsSetup">
    <div class="mb-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:bg-amber-500/10 dark:text-amber-200">
      <p class="font-semibold">{{ $t('admin.unlock.setupTitle') }}</p>
      <p class="mt-0.5">{{ $t('admin.unlock.required') }}</p>
    </div>
    <AdminTotpSetup @done="emit('done', $event)" @cancel="emit('cancel')" />
  </div>

  <form v-else class="space-y-4" @submit.prevent="submit">
    <p v-if="noPassword" class="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{{ $t('admin.unlock.googleOnly') }}</p>
    <p v-if="errorField === 'form'" role="alert" class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
    <FormField
      v-if="!noPassword"
      v-model="password"
      type="password"
      :label="$t('admin.unlock.password')"
      autocomplete="current-password"
      required
      :error="errorField === 'password' ? error : ''"
    />

    <div v-if="withCode">
      <label for="admin-unlock-code" class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">
        {{ $t('admin.unlock.code') }}
      </label>
      <input
        id="admin-unlock-code"
        v-model="code"
        class="zx-input py-2.5 text-center font-mono text-lg tracking-[0.4em]"
        inputmode="numeric"
        autocomplete="one-time-code"
        maxlength="7"
        placeholder="000000"
        :aria-invalid="errorField === 'code' ? 'true' : undefined"
      />
      <p class="mt-1.5 text-xs" :class="errorField === 'code' ? 'text-red-600 dark:text-red-400' : 'text-slate-400'">
        {{ errorField === 'code' ? error : $t('admin.unlock.codeHint') }}
      </p>
    </div>

    <div class="flex justify-end gap-2 pt-1">
      <AppButton v-if="cancellable" variant="ghost" size="sm" type="button" @click="emit('cancel')">
        {{ $t('admin.common.cancel') }}
      </AppButton>
      <AppButton v-if="reauth" variant="outline" size="sm" type="button" icon="user" @click="signInAgain">
        {{ $t('admin.unlock.signInAgain') }}
      </AppButton>
      <AppButton size="sm" type="submit" icon="lock" :disabled="busy || !ready">
        {{ submitLabel }}
      </AppButton>
    </div>
  </form>
</template>
