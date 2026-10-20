<script setup>
/**
 * The top of "Today": a greeting, where the learner stands, one button to the
 * next step, and the bear with one speech bubble. The bubble rotates between
 * useful habits and one secret (tap the bear five times and it dances).
 * Laid out by the width of the column, not the window: between two sidebars
 * the column is much narrower than the screen.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

import BearMascot from '@/components/mascot/BearMascot.vue'
import Icon from '@/components/ui/Icon.vue'
import { useNarrator } from '@/voice/narrator'
import { CARD_ICON, cardRoute, cardText } from './planCards'

const props = defineProps({
  name: { type: String, default: '' },
  progress: { type: Number, default: 0 },
  streak: { type: Number, default: 0 },
  activeToday: { type: Boolean, default: false },
  plan: { type: Object, default: null },
})

const { t, locale } = useI18n()
const narrator = useNarrator()
const bearTalking = computed(() => narrator.state.speaking && narrator.state.owner === 'hero')

const study = computed(() => props.plan?.cards?.[0] || null)
const action = computed(() => {
  const card = study.value
  if (!card) return { to: { name: 'studyPlan' }, label: 'today.continue' }
  if (card.key === 'test') return { to: cardRoute(card), label: 'today.test' }
  if (card.key === 'challenges') return { to: cardRoute(card), label: 'today.challenges' }
  return { to: cardRoute(card), label: 'today.continue' }
})
const next = computed(() => {
  const card = study.value
  if (!card || card.done || card.key === 'challenges') return null
  return { title: cardText(card, t).title, minutes: card.minutes, icon: CARD_ICON[card.key] }
})

const status = computed(() => {
  if (props.activeToday) return t('today.streakDone', { n: props.streak })
  if (props.streak > 0) return t('today.keepStreak', { n: props.streak })
  return t('today.startStreak')
})

// --- the bear: waves hello, then idles; reacts to taps; five taps is a secret
const hello = ref(true)
const party = ref(false)
const bear = ref(null)
const mood = computed(() => (party.value ? 'celebrate' : hello.value ? (props.activeToday ? 'happy' : 'wave') : 'idle'))
let taps = 0, tapTimer, partyTimer, helloTimer

// --- rotating hint in the speech bubble
const TIPS = ['hero.tip1', 'hero.tip2', 'hero.tip3', 'hero.tip4', 'hero.tip5']
const tipIndex = ref(0)
const secretShown = ref(false)
const bubble = computed(() => (secretShown.value ? t('hero.secret') : t(TIPS[tipIndex.value])))
let tipTimer
const reduce = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function onPoke() {
  taps++
  clearTimeout(tapTimer)
  tapTimer = setTimeout(() => (taps = 0), 2500)
  if (taps < 5) return
  taps = 0
  party.value = true
  secretShown.value = true
  bear.value?.react('spin')
  narrator.speak(t('hero.secret'), { owner: 'hero', lang: locale.value })
  clearTimeout(partyTimer)
  partyTimer = setTimeout(() => { party.value = false; secretShown.value = false }, 4200)
}

onMounted(() => {
  helloTimer = setTimeout(() => (hello.value = false), 2600)
  if (!reduce) tipTimer = setInterval(() => { if (!secretShown.value) tipIndex.value = (tipIndex.value + 1) % TIPS.length }, 7000)
})
onBeforeUnmount(() => {
  clearTimeout(helloTimer)
  clearTimeout(tapTimer)
  clearTimeout(partyTimer)
  clearInterval(tipTimer)
  if (narrator.state.owner === 'hero') narrator.stop()
})
</script>

<template>
  <section class="zh @container mb-5 overflow-hidden rounded-[28px] bg-lavender">
    <div class="grid items-center @xl:grid-cols-[minmax(0,1fr)_15rem] @3xl:grid-cols-[minmax(0,1fr)_18rem]">
      <!-- The bear with one bubble -->
      <div class="relative flex flex-col items-center px-6 pt-6 @xl:order-2 @xl:pb-6 @xl:pl-0 @xl:pr-6">
        <p class="zh-bubble relative z-10 flex min-h-[3.25rem] w-full max-w-[15rem] items-center justify-center rounded-2xl bg-white px-4 py-2.5 text-center text-[13px] font-medium leading-snug text-ink shadow-[0_6px_20px_-10px_rgba(40,36,53,0.35)] dark:bg-surface" aria-live="polite">
          <Transition name="zh-fade" mode="out-in">
            <span :key="bubble">{{ bubble }}</span>
          </Transition>
        </p>
        <div class="relative mt-2 h-44 w-40 @xl:h-52 @xl:w-44">
          <span class="zh-disc pointer-events-none absolute left-1/2 top-[18%] aspect-square w-[92%] -translate-x-1/2 rounded-full" aria-hidden="true" />
          <BearMascot ref="bear" :mood="mood" interactive :label="$t('mascot.tap')" :voice="bearTalking ? narrator.level : null" @poke="onPoke" />
        </div>
      </div>

      <!-- Greeting and the next step -->
      <div class="px-6 pb-7 pt-3 @xl:order-1 @xl:py-9 @xl:pl-9 @xl:pr-4">
        <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-brand-600 dark:text-brand-300">{{ $t('hero.eyebrow') }}</p>
        <h1 class="mt-2 text-3xl font-bold tracking-tight text-ink @2xl:text-4xl">{{ $t('today.hello', { name }) }}</h1>
        <p class="mt-1 text-lg font-semibold tracking-tight text-brand-600 @2xl:text-xl dark:text-brand-300">{{ $t('hero.lineStart') }} {{ $t('hero.linePace') }}</p>
        <p class="mt-3 max-w-md text-[15px] leading-relaxed text-ink-muted">{{ status }}</p>

        <div class="mt-5 max-w-sm">
          <p class="text-xs font-semibold text-ink-muted">{{ $t('today.progress', { p: progress }) }}</p>
          <div class="mt-1.5 h-2 overflow-hidden rounded-full bg-white/80 dark:bg-surface-2" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100" :aria-label="$t('today.progress', { p: progress })">
            <div class="h-full rounded-full bg-brand-600 transition-[width] duration-700" :style="{ width: progress + '%' }" />
          </div>
        </div>

        <div class="mt-6 flex flex-wrap items-center gap-x-5 gap-y-3">
          <RouterLink :to="action.to" class="inline-flex min-h-12 items-center gap-2 rounded-2xl bg-brand-600 px-6 font-semibold text-white shadow-[0_10px_24px_-14px_var(--brand-600)] transition hover:-translate-y-0.5 hover:bg-brand-700">
            {{ $t(action.label) }} <Icon name="arrowRight" class="h-4 w-4" />
          </RouterLink>
          <RouterLink :to="{ name: 'studyPlan' }" class="inline-flex min-h-11 items-center gap-2 font-semibold text-brand-700 hover:underline dark:text-brand-300">
            <Icon name="map" class="h-4 w-4" /> {{ $t('hero.map') }}
          </RouterLink>
        </div>
        <p v-if="next" class="mt-3 flex min-w-0 items-center gap-1.5 text-sm text-ink-muted">
          <Icon :name="next.icon" class="h-4 w-4 shrink-0" />
          <span class="flex min-w-0">
            <span class="truncate">{{ $t('hero.nextChip', { title: next.title }) }}</span>
            <span class="shrink-0">&nbsp;· {{ $t('deck.minutes', { n: next.minutes }) }}</span>
          </span>
        </p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zh { background-image: radial-gradient(90% 80% at 100% 0%, color-mix(in srgb, var(--brand-100) 65%, transparent) 0%, transparent 70%); }
.dark .zh { background-image: radial-gradient(90% 80% at 100% 0%, color-mix(in srgb, var(--brand-600) 14%, transparent) 0%, transparent 70%); }
/* A soft spot behind the bear instead of lines across it. */
.zh-disc { background: radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.35) 62%, transparent 71%); }
.dark .zh-disc { background: radial-gradient(circle at 50% 40%, color-mix(in srgb, var(--brand-400) 18%, transparent), color-mix(in srgb, var(--brand-400) 6%, transparent) 60%, transparent 71%); }
/* The bubble's tail points down at the bear. */
.zh-bubble::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: -6px;
  width: 12px;
  height: 12px;
  background: inherit;
  transform: translateX(-50%) rotate(45deg);
  border-radius: 2px;
}
.zh-fade-enter-active, .zh-fade-leave-active { transition: opacity 0.35s ease, transform 0.35s ease; }
.zh-fade-enter-from { opacity: 0; transform: translateY(4px); }
.zh-fade-leave-to { opacity: 0; transform: translateY(-4px); }
@media (prefers-reduced-motion: reduce) {
  .zh-fade-enter-active, .zh-fade-leave-active { transition: none; }
}
</style>
