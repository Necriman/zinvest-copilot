<script setup>
/**
 * Sign up: Google, or name, email and password, and then the six-digit code
 * from the letter (CodeStep). Nothing is created until the code is right; a
 * new account goes on to the ten-question onboarding, which can be skipped.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { passwordProblem, serverDown } from '@/api/authErrors'
import AuthField from '@/components/auth/AuthField.vue'
import CodeStep from '@/components/auth/CodeStep.vue'
import ConsentCheck from '@/components/auth/ConsentCheck.vue'
import GoogleButton from '@/components/auth/GoogleButton.vue'
import GoogleConsentNote from '@/components/auth/GoogleConsentNote.vue'
import Icon from '@/components/ui/Icon.vue'
import { authBear } from '@/composables/useAuthBear'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const router = useRouter()
const { t } = useI18n()

const form = ref({ first_name: '', last_name: '', email: '', password: '', accept_terms: false, age_ok: false })
const consentTried = ref(false) // red boxes only after a submit without them
const error = ref('')
const loading = ref(false)
const challenge = ref(null)

// Local strength hint only — the backend's validators remain the authority, and
// a weak-but-accepted password is never blocked here.
const STRENGTH = ['auth.strength.weak', 'auth.strength.fair', 'auth.strength.good', 'auth.strength.strong']
const strength = computed(() => {
  const value = form.value.password
  if (!value) return null
  let score = 0
  if (value.length >= 10) score++
  if (value.length >= 14) score++
  if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++
  if (/\d/.test(value) && /[^\w\s]/.test(value)) score++
  const level = Math.max(1, Math.min(score, 4))
  return { level, label: STRENGTH[level - 1] }
})

async function onSubmit() {
  error.value = ''
  if (!form.value.first_name.trim() || !form.value.email.trim() || !form.value.password) {
    error.value = t('auth.register.missing')
    authBear.flash('error')
    authBear.react('shake')
    return
  }
  if (!form.value.accept_terms || !form.value.age_ok) {
    consentTried.value = true
    error.value = t('auth.consent.missing')
    authBear.flash('error')
    authBear.react('shake')
    return
  }
  loading.value = true
  try {
    const data = await auth.register({ ...form.value, email: form.value.email.trim() })
    if (data.code_required) {
      challenge.value = data
      authBear.setStep('code')
    } else {
      // Codes switched off on the server: the old flow, sign in right away.
      const signed = await auth.login(form.value.email.trim(), form.value.password)
      if (signed.code_required) {
        challenge.value = signed
        authBear.setStep('code')
      } else router.push({ name: 'onboarding' })
    }
  } catch (e) {
    if (serverDown(e)) error.value = t('errors.serverDown')
    else error.value = passwordProblem(e) || e.response.data?.detail || t('auth.register.failed')
    authBear.flash('error')
    authBear.react('shake')
  } finally {
    loading.value = false
  }
}

function done(data) {
  // New accounts go straight to the questions that build their plan.
  router.push(data.created ? { name: 'onboarding' } : { name: 'dashboard' })
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
    <CodeStep v-if="challenge" :key="challenge.challenge" :challenge="challenge" @back="back" @done="done" />

    <div v-else key="form">
      <h1 class="auth-title">{{ $t('auth.register.title') }}</h1>
      <p class="auth-lead">{{ $t('auth.register.subtitle') }}</p>

      <div class="mt-7">
        <GoogleButton :label="$t('auth.google.button')" />
        <GoogleConsentNote />
      </div>
      <div class="auth-or"><span>{{ $t('auth.or') }}</span></div>

      <form class="space-y-4" novalidate @submit.prevent="onSubmit">
        <p v-if="error" role="alert" class="auth-note auth-note--error">
          <Icon name="shield" class="mt-0.5 h-4 w-4 shrink-0" />
          {{ error }}
        </p>

        <div class="grid gap-4 sm:grid-cols-2">
          <AuthField v-model="form.first_name" icon="user" autocomplete="given-name" :label="$t('auth.fields.firstName')" />
          <AuthField v-model="form.last_name" autocomplete="family-name" :label="$t('auth.fields.lastName')" />
        </div>

        <AuthField v-model="form.email" type="email" icon="mail" autocomplete="email" :label="$t('auth.fields.email')" />

        <div>
          <!-- The length rule stays on screen until it is met. It used to vanish
               on the first keystroke, when the strength bar appeared — exactly
               when a nine-character password was about to be refused. -->
          <AuthField
            v-model="form.password"
            type="password"
            icon="lock"
            autocomplete="new-password"
            :label="$t('auth.fields.password')"
            :hint="form.password.length < 10 ? $t('auth.fields.passwordHint') : ''"
            :reveal-label="$t('auth.showPassword')"
            :hide-label="$t('auth.hidePassword')"
          />
          <div v-if="strength" class="auth-strength" :data-level="strength.level">
            <span v-for="tier in 4" :key="tier" :class="{ on: tier <= strength.level }" />
            <em>{{ $t(strength.label) }}</em>
          </div>
        </div>

        <div class="space-y-3 pt-1">
          <ConsentCheck v-model="form.accept_terms" :invalid="consentTried && !form.accept_terms">
            <i18n-t keypath="auth.consent.terms" scope="global">
              <template #terms>
                <RouterLink :to="{ name: 'legal', params: { doc: 'terms' } }" target="_blank">{{ $t('auth.consent.termsLink') }}</RouterLink>
              </template>
              <template #privacy>
                <RouterLink :to="{ name: 'legal', params: { doc: 'privacy' } }" target="_blank">{{ $t('auth.consent.privacyLink') }}</RouterLink>
              </template>
            </i18n-t>
          </ConsentCheck>
          <ConsentCheck v-model="form.age_ok" :invalid="consentTried && !form.age_ok">
            {{ $t('auth.consent.age') }}
          </ConsentCheck>
        </div>

        <button type="submit" :disabled="loading" class="auth-submit">
          <span v-if="loading" class="auth-spin" />
          {{ loading ? $t('auth.register.submitting') : $t('auth.register.submit') }}
          <Icon v-if="!loading" name="arrowRight" class="h-4 w-4" />
        </button>

      </form>
    </div>
  </Transition>
</template>
