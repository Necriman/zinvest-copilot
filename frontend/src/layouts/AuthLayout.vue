<script setup>
/**
 * Split-screen shell for sign-in / sign-up, with a bear who pays attention.
 *
 * The forms report what is happening (useAuthBear) and the bear answers, the
 * Telegram monkey's trick: he leans in and reads along while an address is
 * typed, hides his eyes for the password, peeks when it is shown, looks along
 * the code boxes, frowns at a mistake and cheers when you are in. A speech
 * bubble says the same in words. On wide screens he stands in the side panel;
 * narrower, the panel goes and he sits above the form, head and shoulders.
 *
 * Deliberately not nested under LandingLayout: the marketing navbar and footer
 * compete with a form, and the panel already carries the brand.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AuthTabs from '@/components/auth/AuthTabs.vue'
import BearMascot from '@/components/mascot/BearMascot.vue'
import BrandMark from '@/components/ui/BrandMark.vue'
import Icon from '@/components/ui/Icon.vue'
import LanguageSwitcher from '@/components/ui/LanguageSwitcher.vue'
import ThemeToggle from '@/components/ui/ThemeToggle.vue'
import { useAuthBear } from '@/composables/useAuthBear'
import { flushPendingScroll } from '@/router/navScroll'

const POINTS = ['p1', 'p2', 'p3', 'p4']

const route = useRoute()
const { t } = useI18n()
const bear = useAuthBear()
const bearRef = ref(null)

// --- which bear, where --------------------------------------------------------
const wideQuery = typeof window !== 'undefined' ? window.matchMedia('(min-width: 1024px)') : null
const wide = ref(wideQuery?.matches ?? true)
const onWide = (e) => (wide.value = e.matches)

// A gesture per door when nothing is happening; the forms' state otherwise.
const ROUTE_IDLE = { register: 'welcome', login: 'ready', forgotPassword: 'think', resetPassword: 'ready', verifyEmail: 'happy' }
const STATUS_MOOD = { reading: 'reading', shy: 'shy', peek: 'peek', code: 'reading', error: 'confused', success: 'celebrate' }
const mood = computed(() => STATUS_MOOD[bear.status] || ROUTE_IDLE[route.name] || 'welcome')

// Toward the form: to the right of the side panel, or down from above it.
const gaze = computed(() => {
  // Turned away over a password: the head stays put instead of following the mouse.
  if (bear.status === 'shy' || bear.status === 'peek') return [0, 0]
  const g = bear.gaze
  if (!g) return null
  return wide.value ? [0.2 + g[0] * 0.8, 0.35] : [(g[0] - 0.5) * 1.3, 0.85]
})

const bubble = computed(() => {
  if (bear.status !== 'idle') return t(`auth.bear.${bear.status}`)
  if (route.name === 'register') return t('auth.bear.idleRegister')
  if (route.name === 'login') return t('auth.bear.idleLogin')
  return t('mascot.authHello')
})

watch(
  () => bear.reaction.n,
  () => bearRef.value?.react(bear.reaction.name),
)

const showTabs = computed(() => ['login', 'register'].includes(route.name) && bear.step === 'form')

// --- sign-in ⇄ sign-up transition -----------------------------------------
// The height is reserved rather than animated: the wrapper keeps the tallest
// form it has seen as a min-height and the content sits at the top of it, so
// swapping forms never jolts the page. Measured, not hardcoded — the forms
// are taller in RU and UZ.
const panel = ref(null)
const reserved = ref(0)

function remember() {
  nextTick(() => {
    if (wideQuery?.matches && panel.value) reserved.value = Math.max(reserved.value, panel.value.scrollHeight)
  })
}

// A floor that already clears sign-up, so the first swap does not step.
const RESERVE_FLOOR = 600

onMounted(async () => {
  wideQuery?.addEventListener('change', onWide)
  if (wideQuery?.matches) reserved.value = RESERVE_FLOOR
  await nextTick()
  remember()
})
onBeforeUnmount(() => wideQuery?.removeEventListener('change', onWide))
</script>

<template>
  <div class="auth-shell min-h-screen bg-canvas text-slate-900 dark:text-ink lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
    <!-- Brand panel: deep navy with a violet glow, so the white bear reads. -->
    <aside class="as hidden lg:flex">
      <RouterLink :to="{ name: 'landing' }" class="relative z-10 flex items-center gap-2.5">
        <BrandMark class="h-8 w-8 rounded-xl" />
        <span class="text-xl font-extrabold tracking-tight text-white">{{ $t('common.appName') }}</span>
      </RouterLink>

      <div class="as__stage">
        <div class="as__glow" aria-hidden="true" />
        <Transition name="as-bubble" mode="out-in">
          <p :key="bubble" class="as__bubble" aria-live="polite">{{ bubble }}</p>
        </Transition>
        <div class="as__bear">
          <BearMascot v-if="wide" ref="bearRef" :mood="mood" :gaze="gaze" :decorations="false" />
        </div>
        <div class="as__floor" aria-hidden="true" />
      </div>

      <div class="relative z-10">
        <h2 class="text-2xl font-extrabold leading-tight tracking-tight text-white xl:text-3xl">
          {{ $t('auth.aside.title') }}
        </h2>
        <ul class="mt-6 grid grid-cols-2 gap-x-5 gap-y-3">
          <li v-for="point in POINTS" :key="point" class="flex items-start gap-2.5 text-sm font-medium text-slate-200">
            <span class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/10 text-brand-200">
              <Icon name="check" class="h-3 w-3" />
            </span>
            {{ $t(`auth.aside.${point}`) }}
          </li>
        </ul>
      </div>
    </aside>

    <!-- Form column -->
    <div class="flex min-h-screen flex-col">
      <header class="flex items-center justify-between px-6 py-5 sm:px-10">
        <RouterLink
          :to="{ name: 'landing' }"
          class="flex items-center gap-2 text-sm font-semibold text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
        >
          <Icon name="arrowLeft" class="h-4 w-4" />
          <span class="hidden sm:inline">{{ $t('nav.backHome') }}</span>
          <!-- On mobile the panel is gone, so this doubles as the wordmark. -->
          <span class="font-extrabold text-slate-900 sm:hidden dark:text-white">{{ $t('common.appName') }}</span>
        </RouterLink>
        <div class="flex items-center gap-1">
          <ThemeToggle />
          <LanguageSwitcher />
        </div>
      </header>

      <main id="main" tabindex="-1" class="flex flex-1 items-start justify-center px-6 pb-10 sm:px-10 lg:items-center">
        <div
          ref="panel"
          data-auth-panel
          class="w-full max-w-[26.5rem]"
          :style="reserved ? { minHeight: `${reserved}px` } : null"
        >
          <!-- Narrow screens: the bear sits above the form, head and shoulders. -->
          <div v-if="!wide" class="mb">
            <div class="mb__bear">
              <BearMascot ref="bearRef" :mood="mood" :gaze="gaze" framing="bust" :decorations="false" />
            </div>
            <Transition name="as-bubble" mode="out-in">
              <p :key="bubble" class="mb__bubble" aria-live="polite">{{ bubble }}</p>
            </Transition>
          </div>

          <Transition name="fade">
            <AuthTabs v-if="showTabs" class="mb-7" />
          </Transition>

          <router-view v-slot="{ Component }">
            <Transition name="fade-slide" mode="out-in" @before-enter="flushPendingScroll" @enter="remember">
              <component :is="Component" />
            </Transition>
          </router-view>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.as {
  position: relative;
  flex-direction: column;
  justify-content: space-between;
  gap: 2rem;
  padding: 2.5rem 3rem;
  overflow: hidden;
  background:
    radial-gradient(70% 55% at 50% 42%, rgba(125, 87, 214, 0.42), transparent 70%),
    radial-gradient(60% 40% at 85% 0%, rgba(96, 165, 250, 0.16), transparent 70%),
    linear-gradient(180deg, #1b2442 0%, #151c34 100%);
}
.as::after {
  /* hairline against the form column, so two dark panels never merge */
  content: '';
  position: absolute;
  inset: 0 0 0 auto;
  width: 1px;
  background: rgba(255, 255, 255, 0.08);
}
.as__stage {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  min-height: 22rem;
}
.as__glow {
  position: absolute;
  left: 50%;
  bottom: 8%;
  width: 26rem;
  height: 26rem;
  transform: translateX(-50%);
  border-radius: 50%;
  background: radial-gradient(closest-side, rgba(183, 166, 255, 0.28), transparent);
  pointer-events: none;
}
.as__bear {
  position: relative;
  width: min(19rem, 70%);
  height: min(26rem, 52vh);
}
.as__floor {
  width: 15rem;
  height: 1.4rem;
  margin-top: -0.9rem;
  border-radius: 50%;
  background: radial-gradient(closest-side, rgba(0, 0, 0, 0.35), transparent);
}
.as__bubble {
  position: relative;
  z-index: 2;
  max-width: 17rem;
  margin-bottom: -0.25rem;
  padding: 0.8rem 1.1rem;
  border-radius: 1.2rem;
  background: #fff;
  color: #1e2a44;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.4;
  text-align: center;
  box-shadow: 0 18px 40px -18px rgba(0, 0, 0, 0.55);
}
.as__bubble::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: -7px;
  width: 16px;
  height: 16px;
  transform: translateX(-50%) rotate(45deg);
  border-radius: 3px;
  background: #fff;
}

/* narrow screens: the bust above the form */
.mb {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: -0.5rem auto 1.25rem;
}
.mb__bear {
  width: 9.5rem;
  height: 9.5rem;
}
.mb__bubble {
  margin-top: 0.4rem;
  padding: 0.45rem 0.9rem;
  border-radius: 999px;
  background: var(--surface-2);
  color: var(--text);
  font-size: 0.85rem;
  font-weight: 600;
  text-align: center;
}

.as-bubble-enter-active,
.as-bubble-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}
.as-bubble-enter-from {
  opacity: 0;
  transform: translateY(6px) scale(0.97);
}
.as-bubble-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .as-bubble-enter-active,
  .as-bubble-leave-active {
    transition: none;
  }
}
</style>

<style>
/* Shared by the sign-in and sign-up views (children of this layout). */
.auth-shell .auth-title {
  font-size: clamp(1.9rem, 1.6rem + 1vw, 2.35rem);
  font-weight: 800;
  letter-spacing: -0.025em;
  line-height: 1.1;
  color: var(--text);
}
.auth-shell .auth-lead {
  margin-top: 0.55rem;
  font-size: 0.97rem;
  line-height: 1.55;
  color: var(--text-muted);
}
.auth-shell .auth-note {
  margin-top: 1.25rem;
  display: flex;
  gap: 0.6rem;
  padding: 0.75rem 1rem;
  border-radius: 1rem;
  font-size: 0.875rem;
  line-height: 1.45;
}
.auth-shell form .auth-note {
  margin-top: 0;
}
.auth-shell .auth-note--error {
  background: rgba(229, 72, 77, 0.1);
  color: #c4282d;
}
.dark .auth-shell .auth-note--error,
.auth-shell.dark .auth-note--error {
  color: #ff9592;
}
.auth-shell .auth-note--warn {
  background: rgba(245, 158, 11, 0.12);
  color: #a15c07;
}
.dark .auth-shell .auth-note--warn {
  color: #fbbf24;
}
.auth-shell .auth-or {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  margin: 1.4rem 0;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.auth-shell .auth-or::before,
.auth-shell .auth-or::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}
.auth-shell .auth-submit {
  display: flex;
  width: 100%;
  min-height: 3.4rem;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  border-radius: 1rem;
  background: var(--brand-600);
  color: #fff;
  font-weight: 700;
  font-size: 1rem;
  box-shadow: 0 12px 26px -14px color-mix(in oklab, var(--brand-600) 80%, transparent);
  transition:
    background-color 0.2s ease,
    transform 0.15s ease,
    opacity 0.2s ease;
}
.auth-shell .auth-submit:hover:not(:disabled) {
  background: var(--brand-700);
}
.auth-shell .auth-submit:active:not(:disabled) {
  transform: translateY(1px);
}
.auth-shell .auth-submit:disabled {
  opacity: 0.55;
}
.auth-shell .auth-submit:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 3px;
}
.auth-shell .auth-spin {
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  animation: auth-spin 0.8s linear infinite;
}
@keyframes auth-spin {
  to {
    transform: rotate(360deg);
  }
}
.auth-shell .auth-link {
  font-weight: 600;
  color: var(--text-muted);
  transition: color 0.2s ease;
}
.auth-shell .auth-link:hover {
  color: var(--brand-600);
}
.auth-shell .auth-fine {
  text-align: center;
  font-size: 0.78rem;
  line-height: 1.5;
  color: var(--text-faint);
}
.auth-shell .auth-strength {
  display: grid;
  grid-template-columns: repeat(4, 1fr) auto;
  align-items: center;
  gap: 0.35rem;
  margin-top: 0.6rem;
}
.auth-shell .auth-strength span {
  height: 4px;
  border-radius: 99px;
  background: var(--surface-2);
  transition: background-color 0.25s ease;
}
.auth-shell .auth-strength em {
  margin-left: 0.4rem;
  font-style: normal;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-muted);
}
.auth-shell .auth-strength[data-level='1'] span.on {
  background: #e5484d;
}
.auth-shell .auth-strength[data-level='2'] span.on {
  background: #f5a524;
}
.auth-shell .auth-strength[data-level='3'] span.on {
  background: #3b9eff;
}
.auth-shell .auth-strength[data-level='4'] span.on {
  background: #30a46c;
}
</style>
