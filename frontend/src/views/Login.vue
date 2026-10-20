<script setup>
/**
 * Sign in: Google, or email and password, and then the six-digit code from
 * the letter (CodeStep). The password alone opens nothing any more.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { serverDown } from '@/api/authErrors'
import AuthField from '@/components/auth/AuthField.vue'
import CodeStep from '@/components/auth/CodeStep.vue'
import GoogleButton from '@/components/auth/GoogleButton.vue'
import GoogleConsentNote from '@/components/auth/GoogleConsentNote.vue'
import Icon from '@/components/ui/Icon.vue'
import { authBear } from '@/composables/useAuthBear'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const email = ref('')
const password = ref('')
const error = ref('')
const hint = ref('')
const loading = ref(false)
const challenge = ref(null)

// Only a path inside the app: never "//host" or "/\host", which browsers read as another site.
function safeRedirect() {
  const redirect = route.query.redirect
  return typeof redirect === 'string' && /^\/(?![/\\])/.test(redirect) ? redirect : ''
}

// Back from Google without a session: say why, in the reader's language.
const GOOGLE_REASONS = ['cancelled', 'failed', 'expired', 'unavailable', 'closed', 'disabled', 'conflict']
const googleProblem = GOOGLE_REASONS.includes(route.query.google) ? t(`auth.google.${route.query.google}`) : ''

function finish() {
  router.push(safeRedirect() || { name: 'dashboard' })
}

async function onSubmit() {
  error.value = ''
  hint.value = ''
  if (!email.value.trim() || !password.value) {
    error.value = t('auth.login.missing')
    authBear.flash('error')
    authBear.react('shake')
    return
  }
  loading.value = true
  try {
    const data = await auth.login(email.value.trim(), password.value)
    if (data.code_required) {
      challenge.value = data
      authBear.setStep('code')
    } else finish()
  } catch (e) {
    // A 401 is the only answer that means the password is wrong, and it gets
    // the translated line. Anything the server says in its own words (being
    // locked out, say) is already localized by the http layer.
    if (serverDown(e)) error.value = t('errors.serverDown')
    else if (e.response.status === 401) {
      error.value = t('auth.login.failed')
      // An account made with Google has no password until one is set; say so
      // for every wrong password, so it gives away nothing about the address.
      hint.value = t('auth.login.googleHint')
    } else error.value = e.response.data?.detail || t('auth.login.failed')
    authBear.flash('error')
    authBear.react('shake')
  } finally {
    loading.value = false
  }
}

function back() {
  challenge.value = null
  authBear.setStep('form')
  authBear.set('idle')
}

onMounted(() => authBear.reset())
onBeforeUnmount(() => authBear.reset())
</script>

<template>
  <Transition name="fade-slide" mode="out-in">
    <CodeStep v-if="challenge" :key="challenge.challenge" :challenge="challenge" @back="back" @done="finish" />

    <div v-else key="form">
      <h1 class="auth-title">{{ $t('auth.login.title') }}</h1>
      <p class="auth-lead">{{ $t('auth.login.subtitle') }}</p>

      <!-- A bounced session lands here with ?session=expired; say why rather than
           showing an empty form the user thinks they already filled in. -->
      <p v-if="route.query.session === 'expired'" class="auth-note auth-note--warn">
        <Icon name="bell" class="mt-0.5 h-4 w-4 shrink-0" />
        {{ $t('auth.login.expired') }}
      </p>
      <p v-if="googleProblem" class="auth-note auth-note--error" role="alert">
        <Icon name="shield" class="mt-0.5 h-4 w-4 shrink-0" />
        {{ googleProblem }}
      </p>

      <div class="mt-7">
        <GoogleButton :label="$t('auth.google.button')" :next="safeRedirect()" />
        <GoogleConsentNote />
      </div>
      <div class="auth-or"><span>{{ $t('auth.or') }}</span></div>

      <form class="space-y-4" novalidate @submit.prevent="onSubmit">
        <p v-if="error" role="alert" class="auth-note auth-note--error">
          <Icon name="shield" class="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            {{ error }}
            <span v-if="hint" class="mt-1 block opacity-80">{{ hint }}</span>
          </span>
        </p>

        <AuthField
          v-model="email"
          type="email"
          icon="mail"
          autocomplete="email"
          :label="$t('auth.fields.email')"
        />
        <AuthField
          v-model="password"
          type="password"
          icon="lock"
          autocomplete="current-password"
          :label="$t('auth.fields.password')"
          :reveal-label="$t('auth.showPassword')"
          :hide-label="$t('auth.hidePassword')"
        />

        <div class="flex justify-end">
          <RouterLink :to="{ name: 'forgotPassword' }" class="auth-link text-sm">
            {{ $t('admin.forgot.link') }}
          </RouterLink>
        </div>

        <button type="submit" :disabled="loading" class="auth-submit">
          <span v-if="loading" class="auth-spin" />
          {{ loading ? $t('auth.login.submitting') : $t('auth.login.submit') }}
          <Icon v-if="!loading" name="arrowRight" class="h-4 w-4" />
        </button>
        <p class="auth-fine">{{ $t('auth.login.codeNote') }}</p>
      </form>
    </div>
  </Transition>
</template>
