<script setup>
/**
 * "Check your email": the second step of both sign-in and sign-up. The six
 * digits go to /api/auth/code/verify the moment the last one is typed; a wrong
 * code shakes the boxes (and the bear), a dead one offers a fresh letter, and
 * "Send again" unlocks after the server's cooldown.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { serverDown } from '@/api/authErrors'
import Icon from '@/components/ui/Icon.vue'
import { authBear } from '@/composables/useAuthBear'
import { useAuthStore } from '@/store/auth'
import CodeInput from './CodeInput.vue'

const props = defineProps({
  // the answer of /auth/login or /auth/register: { challenge, email, resend_in, code_length }
  challenge: { type: Object, required: true },
})
const emit = defineEmits(['back', 'done'])

const auth = useAuthStore()
const { t } = useI18n()

const code = ref('')
const boxes = ref(null)
const busy = ref(false)
const error = ref('')
const invalid = ref(false)
const expired = ref(false)
const notice = ref('')
const wait = ref(props.challenge.resend_in || 45)
const current = ref({ ...props.challenge })
let timer = null

const canResend = computed(() => wait.value <= 0 && !busy.value)

function tick() {
  clearInterval(timer)
  timer = setInterval(() => {
    wait.value = Math.max(0, wait.value - 1)
    if (wait.value === 0) clearInterval(timer)
  }, 1000)
}

async function verify(value) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  invalid.value = false
  try {
    const data = await auth.verifyCode(current.value.challenge, value)
    authBear.flash('success', 2200, 'success')
    authBear.react('hop')
    emit('done', data)
  } catch (e) {
    const data = e.response?.data || {}
    if (serverDown(e)) error.value = t('errors.serverDown')
    else if (data.code === 'code_invalid') {
      error.value = t('auth.code.wrong', { n: data.attempts_left })
      invalid.value = true
    } else if (data.code === 'code_expired') {
      error.value = t('auth.code.expired')
      expired.value = true
    } else error.value = data.detail || t('auth.code.failed')
    authBear.flash('error', 1600, 'code')
    authBear.react('shake')
    setTimeout(() => {
      invalid.value = false
      boxes.value?.clear()
    }, 450)
  } finally {
    busy.value = false
  }
}

async function resend() {
  if (!canResend.value && !expired.value) return
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    const data = await auth.resendCode(current.value.challenge)
    current.value = { ...current.value, ...data }
    wait.value = data.resend_in || 45
    expired.value = false
    notice.value = t('auth.code.sent')
    tick()
    boxes.value?.clear()
  } catch (e) {
    const data = e.response?.data || {}
    if (data.code === 'code_cooldown') {
      wait.value = data.resend_in || 30
      tick()
    } else if (data.code === 'code_expired') {
      // The challenge itself is gone: the only way on is to start over.
      error.value = t('auth.code.startOver')
      expired.value = true
    } else error.value = serverDown(e) ? t('errors.serverDown') : data.detail || t('auth.code.failed')
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  authBear.set('code')
  tick()
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="cs">
    <button type="button" class="cs__back" @click="emit('back')">
      <Icon name="arrowLeft" class="h-4 w-4" />
      {{ $t('auth.code.change') }}
    </button>

    <div class="cs__icon" aria-hidden="true"><Icon name="mail" class="h-6 w-6" /></div>
    <h1 class="cs__title">{{ $t('auth.code.title') }}</h1>
    <p class="cs__lead">
      {{ $t('auth.code.lead') }}
      <b class="cs__email">{{ current.email }}</b>
    </p>

    <div class="mt-7">
      <CodeInput
        ref="boxes"
        v-model="code"
        :length="current.code_length || 6"
        :disabled="busy"
        :invalid="invalid"
        :label="$t('auth.code.label')"
        @complete="verify"
      />
    </div>

    <p v-if="error" role="alert" class="cs__error">
      <Icon name="shield" class="mt-0.5 h-4 w-4 shrink-0" />
      <span>{{ error }}</span>
    </p>
    <p v-else-if="notice" role="status" class="cs__notice">
      <Icon name="check" class="mt-0.5 h-4 w-4 shrink-0" />
      <span>{{ notice }}</span>
    </p>

    <button
      type="button"
      class="cs__submit"
      :disabled="busy || code.length < (current.code_length || 6)"
      @click="verify(code)"
    >
      <span v-if="busy" class="cs__spin" />
      {{ busy ? $t('auth.code.checking') : $t('auth.code.submit') }}
    </button>

    <div class="cs__foot">
      <span>{{ $t('auth.code.noLetter') }}</span>
      <button type="button" class="cs__resend" :disabled="!canResend && !expired" @click="resend">
        <Icon name="refresh" class="h-3.5 w-3.5" />
        {{ canResend || expired ? $t('auth.code.resend') : $t('auth.code.resendIn', { s: wait }) }}
      </button>
    </div>
    <p class="cs__spam">{{ $t('auth.code.spam') }}</p>
  </div>
</template>

<style scoped>
.cs__back {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-muted);
  transition: color 0.2s ease;
}
.cs__back:hover {
  color: var(--text);
}
.cs__icon {
  display: grid;
  place-items: center;
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 1rem;
  background: color-mix(in oklab, var(--brand-500) 14%, transparent);
  color: var(--brand-600);
}
:where(.dark) .cs__icon {
  color: var(--brand-300);
}
.cs__title {
  margin-top: 1.1rem;
  font-size: 1.9rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--text);
}
.cs__lead {
  margin-top: 0.5rem;
  font-size: 0.95rem;
  line-height: 1.55;
  color: var(--text-muted);
}
.cs__email {
  color: var(--text);
  font-weight: 700;
}
.cs__error,
.cs__notice {
  margin-top: 1rem;
  display: flex;
  gap: 0.6rem;
  padding: 0.75rem 1rem;
  border-radius: 1rem;
  font-size: 0.875rem;
}
.cs__error {
  background: rgba(229, 72, 77, 0.1);
  color: #c4282d;
}
:where(.dark) .cs__error {
  color: #ff9592;
}
.cs__notice {
  background: color-mix(in oklab, var(--mint) 80%, transparent);
  color: var(--mint-ink);
}
.cs__submit {
  margin-top: 1.5rem;
  display: flex;
  width: 100%;
  min-height: 3.4rem;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  border-radius: 1rem;
  background: var(--brand-600);
  color: #fff;
  font-weight: 700;
  font-size: 1rem;
  box-shadow: 0 10px 24px -12px color-mix(in oklab, var(--brand-600) 70%, transparent);
  transition:
    background-color 0.2s ease,
    transform 0.15s ease,
    opacity 0.2s ease;
}
.cs__submit:hover:not(:disabled) {
  background: var(--brand-700);
}
.cs__submit:active:not(:disabled) {
  transform: translateY(1px);
}
.cs__submit:disabled {
  opacity: 0.45;
}
.cs__spin {
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  animation: cs-spin 0.8s linear infinite;
}
@keyframes cs-spin {
  to {
    transform: rotate(360deg);
  }
}
.cs__foot {
  margin-top: 1.4rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}
.cs__resend {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-height: 2.75rem;
  padding: 0 0.5rem;
  font-weight: 700;
  color: var(--brand-600);
}
:where(.dark) .cs__resend {
  color: var(--brand-300);
}
.cs__resend:disabled {
  color: var(--text-faint);
  font-variant-numeric: tabular-nums;
}
.cs__spam {
  margin-top: 0.25rem;
  text-align: center;
  font-size: 0.78rem;
  color: var(--text-faint);
}
</style>
