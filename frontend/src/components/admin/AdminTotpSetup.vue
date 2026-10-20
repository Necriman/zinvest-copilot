<script setup>
// Turning on two-factor sign-in: confirm the password, scan the QR code (or
// type the key) into an authenticator app, then prove it with one code. The
// last step also opens the panel, so it ends with `done(me)`.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import qrcode from 'qrcode-generator'

import AppButton from '@/components/ui/AppButton.vue'
import FormField from '@/components/ui/FormField.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAuthStore } from '@/store/auth'

defineProps({
  showIntro: { type: Boolean, default: true },
})
const emit = defineEmits(['done', 'cancel'])

const { t } = useI18n()
const admin = useAdmin()
const auth = useAuthStore()
const router = useRouter()
// A Google-only account has no password: a recent sign-in is the proof here.
const noPassword = computed(() => admin.me.value?.has_password === false)
const reauth = ref(false)

async function signInAgain() {
  await auth.logout()
  router.push({ name: 'login', query: { redirect: '/admin-panel' } })
}

const step = ref('password') // password → scan
const password = ref('')
const code = ref('')
const setup = ref(null) // { secret, otpauth_uri }
const busy = ref(false)
const error = ref('')

const CODE_MESSAGES = { bad_password: 'badPassword', bad_code: 'badCode', rate_limited: 'rateLimited' }

function fail(e) {
  reauth.value = e?.response?.data?.code === 'reauth_required'
  if (reauth.value) {
    error.value = t('admin.unlock.reauth')
    return
  }
  const key = CODE_MESSAGES[e?.response?.data?.code]
  error.value = key ? t(`admin.unlock.${key}`) : admin.errorText(e, t)
}

async function start() {
  if ((!password.value && !noPassword.value) || busy.value) return
  busy.value = true
  error.value = ''
  try {
    setup.value = await adminApi.totpSetup(noPassword.value ? '' : password.value)
    password.value = ''
    step.value = 'scan'
  } catch (e) {
    fail(e)
  } finally {
    busy.value = false
  }
}

async function enable() {
  const clean = code.value.replace(/\D/g, '')
  if (clean.length !== 6 || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const me = await adminApi.totpEnable(clean)
    admin.setMe(me)
    emit('done', me)
  } catch (e) {
    code.value = ''
    fail(e)
  } finally {
    busy.value = false
  }
}

// The QR is drawn from our own otpauth:// link: only module paths end up in
// the SVG, no text from the server.
const qrSvg = computed(() => {
  if (!setup.value) return ''
  const qr = qrcode(0, 'M')
  qr.addData(setup.value.otpauth_uri)
  qr.make()
  return qr.createSvgTag({ cellSize: 4, margin: 4, scalable: true })
})

const groupedKey = computed(() => (setup.value?.secret || '').replace(/(.{4})/g, '$1 ').trim())
</script>

<template>
  <div>
    <template v-if="step === 'password'">
      <p v-if="showIntro" class="mb-4 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
        {{ $t('admin.unlock.setupText') }}
      </p>
      <form class="space-y-4" @submit.prevent="start">
        <FormField
          v-if="!noPassword"
          v-model="password"
          type="password"
          :label="$t('admin.unlock.password')"
          autocomplete="current-password"
          required
          :error="error"
        />
        <template v-else>
          <p class="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{{ $t('admin.unlock.googleOnly') }}</p>
          <p v-if="error" role="alert" class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
        </template>
        <div class="flex flex-wrap justify-end gap-2">
          <AppButton variant="ghost" size="sm" type="button" @click="emit('cancel')">
            {{ $t('admin.common.cancel') }}
          </AppButton>
          <AppButton v-if="reauth" variant="outline" size="sm" type="button" icon="user" @click="signInAgain">
            {{ $t('admin.unlock.signInAgain') }}
          </AppButton>
          <AppButton size="sm" type="submit" icon="key" :disabled="busy || (!password && !noPassword)">
            {{ $t('admin.unlock.setupStart') }}
          </AppButton>
        </div>
      </form>
    </template>

    <template v-else>
      <p class="text-sm text-slate-600 dark:text-slate-300">{{ $t('admin.unlock.scan') }}</p>
      <div class="mt-4 flex flex-col items-center gap-4 sm:flex-row sm:items-start">
        <!-- White card in both themes: scanners need the contrast. -->
        <div class="h-44 w-44 shrink-0 rounded-2xl border border-slate-200 bg-white p-1" v-html="qrSvg" />
        <div class="min-w-0 flex-1 text-sm">
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-400">{{ $t('admin.unlock.key') }}</p>
          <p class="mt-1 break-all font-mono text-[13px] font-semibold tracking-wide text-slate-800 select-all dark:text-slate-100">
            {{ groupedKey }}
          </p>
          <a
            :href="setup.otpauth_uri"
            class="mt-3 inline-flex text-sm font-semibold text-brand-600 hover:underline sm:hidden dark:text-brand-300"
          >
            {{ $t('admin.unlock.openInApp') }}
          </a>
        </div>
      </div>
      <form class="mt-5 space-y-4" @submit.prevent="enable">
        <div>
          <label for="totp-setup-code" class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">
            {{ $t('admin.unlock.code') }}
          </label>
          <input
            id="totp-setup-code"
            v-model="code"
            class="zx-input py-2.5 text-center font-mono text-lg tracking-[0.4em]"
            inputmode="numeric"
            autocomplete="one-time-code"
            maxlength="7"
            placeholder="000000"
            :aria-invalid="error ? 'true' : undefined"
          />
          <p class="mt-1.5 text-xs" :class="error ? 'text-red-600 dark:text-red-400' : 'text-slate-400'">
            {{ error || $t('admin.unlock.codeHint') }}
          </p>
        </div>
        <div class="flex justify-end gap-2">
          <AppButton variant="ghost" size="sm" type="button" @click="emit('cancel')">
            {{ $t('admin.common.cancel') }}
          </AppButton>
          <AppButton size="sm" type="submit" icon="shield" :disabled="busy || code.replace(/\D/g, '').length !== 6">
            {{ $t('admin.unlock.enable') }}
          </AppButton>
        </div>
      </form>
    </template>
  </div>
</template>

<style scoped>
div :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
