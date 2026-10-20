<script setup>
/**
 * The top of Today, answering one question: what should I do now?
 *
 * One card, one button. It names the next step, how long it takes and what it
 * pays, and where it sits in its unit. The bar is the unit's progress, not the
 * course's, because "3 of 6" is a distance you can feel and "14% of the
 * course" is not — and it is tinted in the unit's own colour, the same one the
 * study map uses, so Home and the map read as one place.
 *
 * Beside it, the three numbers people check anyway: streak, coins, league.
 * The bear stays, with one line that is about this learner right now instead
 * of a rotating tip — and five taps still make him dance.
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

import BearMascot from '@/components/mascot/BearMascot.vue'
import { accentOf } from '@/components/study/accents'
import Icon from '@/components/ui/Icon.vue'
import { useNarrator } from '@/voice/narrator'
import { cardRoute } from './planCards'

const props = defineProps({
  name: { type: String, default: '' },
  stats: { type: Object, default: null },
  plan: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})

const { t, locale } = useI18n()
const narrator = useNarrator()

const study = computed(() => props.plan?.cards?.[0] || null)

// lesson | test: something to do; rested: today's study is already done;
// finished: the whole plan is behind them.
const mode = computed(() => {
  const card = study.value
  if (!card) return props.loading || !props.plan ? 'loading' : 'finished'
  if (card.key === 'challenges') return 'finished'
  if (card.done) return 'rested'
  return card.key === 'test' ? 'test' : 'lesson'
})

const accent = computed(() => accentOf(study.value?.unit_color || 'brand'))
const unitDone = computed(() => study.value?.unit_done ?? 0)
const unitTotal = computed(() => study.value?.unit_total ?? 0)
const unitPct = computed(() => (unitTotal.value ? Math.round((unitDone.value / unitTotal.value) * 100) : 0))

const kicker = computed(
  () =>
    ({
      lesson: t('focus.continueKicker'),
      test: t('focus.testKicker'),
      rested: t('focus.restedKicker'),
      finished: t('focus.finishedKicker'),
    })[mode.value] || '',
)

const title = computed(() => {
  if (mode.value === 'rested') return t('deck.lessonDone')
  if (mode.value === 'finished') return t('focus.finishedTitle')
  return study.value?.title || ''
})

const meta = computed(() => {
  const card = study.value
  if (!card || mode.value === 'finished') return ''
  if (mode.value === 'rested') return t('today.streakDone', { n: props.stats?.day_streak || 0 })
  const parts = [t('deck.minutes', { n: card.minutes })]
  if (card.coins) parts.push(t('deck.coins', { n: card.coins }))
  return parts.join(' · ')
})

const button = computed(() => {
  if (mode.value === 'finished') return { to: { name: 'drills' }, label: t('today.challenges') }
  if (mode.value === 'test') return { to: cardRoute(study.value), label: t('focus.takeCheckpoint') }
  if (mode.value === 'rested') return { to: cardRoute(study.value), label: t('focus.oneMore') }
  return { to: cardRoute(study.value), label: t('today.continue') }
})

// What the bear says: about where this learner is, not a generic tip.
const secret = ref(false)
const line = computed(() => {
  if (secret.value) return t('hero.secret')
  if (mode.value === 'lesson') {
    const left = unitTotal.value - unitDone.value
    return left > 1 ? t('focus.toCheckpoint', { n: left }) : t('focus.lastLesson')
  }
  if (mode.value === 'test') return t('focus.checkpointReady')
  if (mode.value === 'rested') return t('hero.nextChip', { title: study.value?.title || '' })
  if (mode.value === 'finished') return t('today.allDone')
  return ''
})

const mood = computed(() => {
  if (secret.value) return 'celebrate'
  if (mode.value === 'rested' || mode.value === 'finished') return 'happy'
  return 'proud' // paws on the hips: ready for today
})

// Five quick taps: the dance the old greeting promised in its tips.
const bear = ref(null)
let taps = 0
let tapTimer
let secretTimer
function onPoke() {
  taps++
  clearTimeout(tapTimer)
  tapTimer = setTimeout(() => (taps = 0), 2500)
  if (taps < 5) return
  taps = 0
  secret.value = true
  bear.value?.react('spin')
  narrator.speak(t('hero.secret'), { owner: 'focus', lang: locale.value })
  clearTimeout(secretTimer)
  secretTimer = setTimeout(() => (secret.value = false), 4200)
}
const talking = computed(() => narrator.state.speaking && narrator.state.owner === 'focus')

onBeforeUnmount(() => {
  clearTimeout(tapTimer)
  clearTimeout(secretTimer)
  if (narrator.state.owner === 'focus') narrator.stop()
})

// ---- the three numbers ----
const league = computed(() => props.stats?.league || null)
const streak = computed(() => props.stats?.day_streak ?? 0)
const streakToday = computed(() => !!props.stats?.streak_active_today)
</script>

<template>
  <section class="@container mb-5">
    <header class="mb-4">
      <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-brand-600 dark:text-brand-300">
        {{ $t('today.hello', { name }) }}
      </p>
      <h1 class="mt-1.5 text-[1.75rem] font-bold leading-tight tracking-tight text-ink @2xl:text-[2.1rem]">
        {{ $t('focus.question') }}
      </h1>
    </header>

    <div class="tf-grid">
      <!-- The one card -->
      <article class="tf-card relative overflow-hidden rounded-[28px] bg-lavender">
        <div v-if="mode === 'loading'" class="h-56 animate-pulse" />

        <div v-else class="grid items-center @xl:grid-cols-[minmax(0,1fr)_11rem]">
          <div class="px-6 pb-6 pt-6 @xl:py-8 @xl:pl-8 @xl:pr-2">
            <p class="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] font-bold uppercase tracking-[0.14em]">
              <span :class="mode === 'rested' || mode === 'finished' ? 'text-mint-ink' : 'text-brand-700 dark:text-brand-300'">
                {{ kicker }}
              </span>
              <template v-if="(mode === 'lesson' || mode === 'test') && study?.unit_title">
                <span class="text-ink-faint" aria-hidden="true">·</span>
                <span class="normal-case tracking-normal text-ink-muted">
                  {{ study.unit_code }} {{ study.unit_title }}
                </span>
              </template>
            </p>

            <h2 class="mt-2 text-2xl font-bold leading-tight tracking-tight text-ink @2xl:text-[1.9rem]">
              {{ title }}
            </h2>
            <p v-if="meta" class="mt-1.5 text-sm font-medium text-ink-muted">{{ meta }}</p>

            <!-- The unit's bar, in the unit's colour. -->
            <div v-if="(mode === 'lesson' || mode === 'test') && unitTotal" class="mt-5 max-w-sm">
              <div
                class="h-2 overflow-hidden rounded-full bg-white/80 dark:bg-surface-2"
                role="progressbar"
                :aria-valuenow="unitPct"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-label="$t('focus.unitProgress', { done: unitDone, total: unitTotal })"
              >
                <div class="h-full rounded-full transition-[width] duration-700 ease-out" :class="accent.fill" :style="{ width: unitPct + '%' }" />
              </div>
              <p class="mt-1.5 text-xs font-semibold text-ink-muted">
                {{ $t('focus.unitProgress', { done: unitDone, total: unitTotal }) }}
              </p>
            </div>

            <div class="mt-6 flex flex-wrap items-center gap-x-5 gap-y-3">
              <RouterLink
                :to="button.to"
                class="group inline-flex min-h-12 items-center gap-2 rounded-2xl px-6 font-semibold transition duration-200 hover:-translate-y-0.5 motion-reduce:hover:translate-y-0"
                :class="
                  mode === 'rested'
                    ? 'bg-white text-brand-700 shadow-sm hover:bg-white/90 dark:bg-surface dark:text-brand-300'
                    : 'bg-brand-600 text-white shadow-[0_10px_24px_-14px_var(--brand-600)] hover:bg-brand-700'
                "
              >
                {{ button.label }}
                <Icon name="arrowRight" class="h-4 w-4 transition-transform duration-200 group-hover:translate-x-[3px] motion-reduce:transition-none" />
              </RouterLink>
              <RouterLink
                :to="{ name: 'studyPlan' }"
                class="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-brand-700 hover:underline dark:text-brand-300"
              >
                <Icon name="map" class="h-4 w-4" /> {{ $t('hero.map') }}
              </RouterLink>
            </div>
          </div>

          <!-- The bear, with one line about where this learner is. -->
          <div class="flex flex-col items-center px-6 pb-6 @xl:pb-0 @xl:pl-0 @xl:pr-6">
            <p class="tf-bubble relative z-10 w-full max-w-[13rem] rounded-2xl bg-white px-3.5 py-2 text-center text-[12.5px] font-medium leading-snug text-ink shadow-[0_6px_20px_-10px_rgba(40,36,53,0.35)] dark:bg-surface" aria-live="polite">
              <Transition name="tf-fade" mode="out-in">
                <span :key="line">{{ line }}</span>
              </Transition>
            </p>
            <div class="relative mt-2 h-36 w-32 @xl:h-40 @xl:w-36">
              <span class="tf-disc pointer-events-none absolute left-1/2 top-[18%] aspect-square w-[92%] -translate-x-1/2 rounded-full" aria-hidden="true" />
              <BearMascot ref="bear" :mood="mood" interactive :label="$t('mascot.tap')" :voice="talking ? narrator.level : null" @poke="onPoke" />
            </div>
          </div>
        </div>
      </article>

      <!-- The three numbers people check anyway. From 1280px the right rail
           shows the same three with more detail, so here they step aside —
           one screen should never show the same number twice. -->
      <dl class="tf-stats overflow-hidden rounded-[22px] border border-hairline bg-surface">
        <div class="tf-stat">
          <dt class="tf-statLabel">
            <span class="tf-chip" :class="streakToday ? 'bg-amber-100 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300' : 'bg-surface-2 text-ink-faint'">
              <Icon name="flame" class="h-3.5 w-3.5" />
            </span>
            <span class="sr-only">{{ $t('focus.streak') }}</span>
          </dt>
          <dd class="tf-statValue">{{ streak }}</dd>
          <dd class="tf-statNote">
            {{ $t('focus.streak') }}
            <span class="block text-[11px]" :class="streakToday ? 'text-mint-ink' : 'text-ink-faint'">
              {{ streakToday ? $t('focus.streakToday') : $t('focus.streakPending') }}
            </span>
          </dd>
        </div>

        <div class="tf-stat">
          <dt class="tf-statLabel">
            <span class="tf-chip bg-emerald-100 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300">
              <Icon name="coin" class="h-3.5 w-3.5" />
            </span>
            <span class="sr-only">{{ $t('focus.coins') }}</span>
          </dt>
          <dd class="tf-statValue">{{ stats?.coins ?? 0 }}</dd>
          <dd class="tf-statNote">{{ $t('focus.coins') }}</dd>
        </div>

        <RouterLink :to="{ name: 'leaderboard' }" class="tf-stat tf-stat--link group">
          <dt class="tf-statLabel">
            <span class="tf-chip bg-violet-100 text-violet-600 dark:bg-violet-500/15 dark:text-violet-300">
              <Icon name="trophy" class="h-3.5 w-3.5" />
            </span>
            <span class="sr-only">{{ $t('focus.league') }}</span>
          </dt>
          <dd class="tf-statValue truncate">{{ league ? $t(`league.div_${league.division}`) : '—' }}</dd>
          <dd class="tf-statNote">
            <span class="group-hover:text-ink">{{ league?.seated && league.rank ? $t('focus.rank', { n: league.rank }) : $t('focus.leagueOpen') }}</span>
          </dd>
        </RouterLink>
      </dl>
    </div>
  </section>
</template>

<style scoped>
.tf-card {
  background-image: radial-gradient(90% 80% at 100% 0%, color-mix(in srgb, var(--brand-100) 65%, transparent) 0%, transparent 70%);
}
.dark .tf-card {
  background-image: radial-gradient(90% 80% at 100% 0%, color-mix(in srgb, var(--brand-600) 14%, transparent) 0%, transparent 70%);
}
.tf-disc {
  background: radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.35) 62%, transparent 71%);
}
.dark .tf-disc {
  background: radial-gradient(circle at 50% 40%, color-mix(in srgb, var(--brand-400) 18%, transparent), color-mix(in srgb, var(--brand-400) 6%, transparent) 60%, transparent 71%);
}
/* The bubble's tail points down at the bear. */
.tf-bubble::after {
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
.tf-fade-enter-active,
.tf-fade-leave-active {
  transition:
    opacity 0.3s ease,
    transform 0.3s ease;
}
.tf-fade-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
.tf-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.tf-grid {
  display: grid;
  gap: 1rem;
}
.tf-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

/* Rules between the numbers, never around each: the column is one object. */
.tf-stat {
  display: block;
  padding: 0.95rem 1rem 1rem;
  min-width: 0;
}
.tf-stat + .tf-stat {
  border-left: 1px solid var(--color-hairline);
}

/* Beside the card: a column, each number on one line with its icon, sharing
   the card's height evenly rather than stretching it with empty space. */
@container (min-width: 48rem) {
  .tf-grid {
    grid-template-columns: minmax(0, 1fr) 12.5rem;
  }
  .tf-stats {
    grid-template-columns: 1fr;
    grid-auto-rows: 1fr;
  }
  .tf-stat {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    column-gap: 0.75rem;
    align-content: center;
    padding: 0.85rem 1.1rem;
  }
  .tf-stat + .tf-stat {
    border-left: 0;
    border-top: 1px solid var(--color-hairline);
  }
  .tf-statLabel {
    grid-row: span 2;
    align-self: center;
  }
  .tf-stat .tf-statValue {
    margin-top: 0;
  }
}

/* The right rail is on screen from here and carries these three. */
@media (min-width: 1280px) {
  .tf-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .tf-stats {
    display: none;
  }
}
.tf-stat--link {
  transition: background-color 200ms ease;
}
.tf-stat--link:hover {
  background-color: var(--surface-2);
}
.tf-stat--link:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: -2px;
}
.tf-statLabel {
  display: flex;
}
.tf-chip {
  display: grid;
  place-items: center;
  width: 1.7rem;
  aspect-ratio: 1;
  border-radius: 0.6rem;
}
.tf-statValue {
  margin-top: 0.55rem;
  font-size: 1.45rem;
  font-weight: 800;
  line-height: 1.05;
  letter-spacing: -0.02em;
  color: var(--color-ink);
}
.tf-statNote {
  margin-top: 0.2rem;
  font-size: 0.75rem;
  line-height: 1.35;
  color: var(--color-ink-muted);
}

@media (prefers-reduced-motion: reduce) {
  .tf-fade-enter-active,
  .tf-fade-leave-active {
    transition: none;
  }
}
</style>
