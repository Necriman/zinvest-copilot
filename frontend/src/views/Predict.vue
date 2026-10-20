<script setup>
/**
 * "Up or down?" — a real moment from market history, cut where the learner
 * has to make the call. The game is not the point; the reveal is: the chart
 * carries on to what actually happened and the bear says why.
 *
 * Three rounds a day and each episode once, like in the bot (they share the
 * rounds: one played in Telegram is gone here). A right call pays a few
 * coins; a wrong one costs nothing. ↑ and ↓ make the call.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import AiAvatar from '@/components/ai/AiAvatar.vue'
import PriceChart from '@/components/games/PriceChart.vue'
import { formatChange, formatPrice } from '@/components/games/price'
import BearMascot from '@/components/mascot/BearMascot.vue'
import Icon from '@/components/ui/Icon.vue'
import { answerPredict, getPredict } from '@/api/games'
import { useAskAI } from '@/composables/useAskAI'
import { useSharedStats } from '@/composables/useSharedStats'

const { t } = useI18n()
const { askAbout } = useAskAI()
const { reload: reloadStats } = useSharedStats()

const game = ref(null) // GET /predict: rounds left, the record, today's round
const round = ref(null) // the round on screen; stays through the reveal
const result = ref(null)
const choice = ref('')
const loading = ref(true)
const sending = ref(false)
const failed = ref('')
const nextButton = ref(null)

const stats = computed(() => game.value?.stats || { played: 0, correct: 0, streak: 0, coins: 0 })
const perDay = computed(() => game.value?.rounds_per_day || 3)
const left = computed(() => game.value?.left_today ?? 0)
// The number of the round on screen: after the call it has already been counted.
const roundNo = computed(() => perDay.value - left.value + (result.value ? 0 : 1))
const mood = computed(() => {
  if (!result.value) return 'think'
  return result.value.correct ? 'celebrate' : 'confused'
})
const start = computed(() => (round.value ? round.value.before[round.value.before.length - 1] : 0))
const end = computed(() => (result.value ? result.value.after[result.value.after.length - 1] : 0))
const chartLabel = computed(() => {
  if (!round.value) return ''
  if (!result.value) return t('upDown.chart', { asset: round.value.asset, when: round.value.when })
  return t('upDown.chartAfter', {
    asset: round.value.asset,
    start: formatPrice(start.value, round.value.unit),
    end: formatPrice(end.value, round.value.unit),
  })
})
const move = computed(() => {
  if (!result.value || !round.value) return ''
  const change = formatChange(start.value, end.value)
  return `${formatPrice(start.value, round.value.unit)} → ${formatPrice(end.value, round.value.unit)}${change ? ` (${change})` : ''}`
})

async function load() {
  loading.value = true
  failed.value = ''
  try {
    game.value = await getPredict()
    round.value = game.value.round
    result.value = null
    choice.value = ''
  } catch (e) {
    failed.value = e?.response?.data?.detail || t('errors.generic')
  } finally {
    loading.value = false
  }
}

async function call(direction) {
  if (!round.value || result.value || sending.value) return
  sending.value = true
  failed.value = ''
  choice.value = direction
  try {
    const graded = await answerPredict(round.value.id, direction)
    result.value = graded
    game.value = { ...game.value, left_today: graded.left_today, stats: graded.stats }
    if (graded.coins) reloadStats() // the coin counter in the top bar
    await nextTick()
    // A button, or a RouterLink once today's rounds are done.
    const next = nextButton.value?.$el || nextButton.value
    next?.focus?.({ preventScroll: true })
  } catch (e) {
    choice.value = ''
    const code = e?.response?.data?.code
    if (code === 'played' || code === 'limit') {
      await load()
      failed.value = t(`upDown.${code}`)
    } else {
      failed.value = e?.response?.data?.detail || t('errors.generic')
    }
  } finally {
    sending.value = false
  }
}

function askWhy(event) {
  if (!result.value || !round.value) return
  const change = formatChange(start.value, end.value)
  askAbout(
    t('upDown.ask', {
      asset: round.value.asset,
      when: round.value.when,
      headline: round.value.headline,
      direction: t(`upDown.dir.${result.value.direction}`),
      start: formatPrice(start.value, round.value.unit),
      end: formatPrice(end.value, round.value.unit),
      change: change ? ` (${change})` : '',
    }),
    `${round.value.asset} · ${round.value.when}`,
    event?.currentTarget?.getBoundingClientRect?.() || null,
  )
}

function onKey(event) {
  if (result.value || !round.value || event.metaKey || event.ctrlKey || event.altKey) return
  if (event.target?.closest?.('input, textarea, select, [contenteditable="true"]')) return
  if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
    event.preventDefault()
    call(event.key === 'ArrowUp' ? 'up' : 'down')
  }
}

onMounted(() => {
  load()
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

</script>

<template>
  <div class="@container">
    <header class="mb-5 flex items-start justify-between gap-4">
      <div class="min-w-0">
        <h1 class="text-3xl font-extrabold text-ink">{{ $t('upDown.title') }}</h1>
        <p class="mt-2 max-w-2xl text-ink-muted">{{ $t('upDown.lead') }}</p>
      </div>
      <div class="hidden h-28 w-24 shrink-0 sm:block">
        <BearMascot :mood="mood" :decorations="false" />
      </div>
    </header>

    <!-- The record. -->
    <dl class="mb-5 grid grid-cols-2 gap-2 sm:max-w-2xl sm:grid-cols-4">
      <div class="game-stat">
        <dt>{{ $t('upDown.leftToday') }}</dt>
        <dd class="flex items-center gap-1.5">
          <span v-for="i in perDay" :key="i" class="game-pip" :class="{ 'is-used': i <= perDay - left }" />
          <span class="sr-only">{{ $t('upDown.leftValue', { n: left, total: perDay }) }}</span>
        </dd>
      </div>
      <div class="game-stat" :class="{ 'game-stat--hot': stats.streak >= 2 }">
        <dt>{{ $t('upDown.streak') }}</dt>
        <dd class="flex items-center gap-1">
          <Icon name="flame" class="h-4 w-4" :class="stats.streak ? 'text-orange-500' : 'text-slate-400'" />
          <span :key="stats.streak" class="game-bump">{{ stats.streak }}</span>
        </dd>
      </div>
      <div class="game-stat">
        <dt>{{ $t('upDown.record') }}</dt>
        <dd>{{ stats.correct }} / {{ stats.played }}</dd>
      </div>
      <div class="game-stat">
        <dt>{{ $t('upDown.earned') }}</dt>
        <dd class="flex items-center gap-1">
          <Icon name="coin" class="h-4 w-4 text-amber-500" />
          <span :key="stats.coins" class="game-bump">{{ stats.coins }}</span>
        </dd>
      </div>
    </dl>

    <p v-if="failed" role="alert" class="mb-4 text-sm text-red-600 dark:text-red-400">{{ failed }}</p>

    <div v-if="loading && !round" class="card space-y-4 p-5 sm:p-6" aria-hidden="true">
      <div class="h-5 w-1/3 animate-pulse rounded bg-surface-2" />
      <div class="h-64 animate-pulse rounded-2xl bg-surface-2" />
      <div class="h-12 animate-pulse rounded-xl bg-surface-2" />
    </div>

    <!-- Nothing to play: today's rounds are done, or every episode is. -->
    <section v-else-if="!round && game" class="card flex flex-col items-center gap-3 p-8 text-center">
      <div class="h-28 w-24"><BearMascot mood="happy" :decorations="false" /></div>
      <h2 class="text-xl font-bold text-ink">
        {{ game.remaining ? $t('upDown.doneToday', { n: perDay }) : $t('upDown.allDone') }}
      </h2>
      <p class="max-w-md text-ink-muted">
        {{ game.remaining ? $t('upDown.doneTodayBody') : $t('upDown.allDoneBody', { correct: stats.correct, played: stats.played }) }}
      </p>
      <RouterLink
        :to="{ name: 'practice' }"
        class="pill mt-2 bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700"
      >
        {{ $t('upDown.toPractice') }}
        <Icon name="arrowRight" class="h-4 w-4" />
      </RouterLink>
    </section>

    <section v-else-if="round" class="card overflow-hidden p-5 sm:p-6">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <p class="text-sm">
          <span class="font-extrabold text-ink">{{ round.asset }}</span>
          <span class="text-ink-muted"> · {{ round.when }}</span>
        </p>
        <p class="flex items-center gap-2 text-xs font-semibold text-ink-muted">
          <span>{{ $t('upDown.round', { n: roundNo, total: perDay }) }}</span>
          <span class="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300">
            <Icon name="coin" class="h-3.5 w-3.5" />
            {{ $t('upDown.pays', { coins: game?.coins_right || 5 }) }}
          </span>
        </p>
      </div>

      <p class="game-news mt-3">
        <Icon name="megaphone" class="mt-0.5 h-4 w-4 shrink-0 text-brand-600 dark:text-brand-400" />
        <span>{{ round.headline }}</span>
      </p>

      <div class="mt-4">
        <PriceChart
          :before="round.before"
          :after="result?.after || null"
          :unit="round.unit"
          :up="result?.direction === 'up'"
          :label="chartLabel"
        />
      </div>

      <!-- The call. -->
      <template v-if="!result">
        <p class="mt-4 text-lg font-semibold leading-snug text-ink">{{ round.question }}</p>
        <div class="mt-4 grid grid-cols-2 gap-3">
          <button type="button" class="game-call game-call--up" :disabled="sending" @click="call('up')">
            <Icon name="trending" class="h-5 w-5" />
            {{ $t('upDown.up') }}
          </button>
          <button type="button" class="game-call game-call--down" :disabled="sending" @click="call('down')">
            <Icon name="trending" class="h-5 w-5 -scale-y-100" />
            {{ $t('upDown.down') }}
          </button>
        </div>
        <p class="mt-3 hidden text-center text-xs text-ink-muted sm:block">{{ $t('upDown.keys') }}</p>
      </template>

      <!-- The reveal. -->
      <div v-else class="game-reveal mt-5" aria-live="polite">
        <div class="flex flex-wrap items-center gap-2">
          <p
            class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-bold"
            :class="result.correct
              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300'
              : 'bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300'"
          >
            <Icon :name="result.correct ? 'checkCircle' : 'alert'" class="h-4 w-4" />
            {{ result.correct ? $t('upDown.right') : $t('upDown.wrong') }}
          </p>
          <p v-if="result.coins" class="game-coins">
            <Icon name="coin" class="h-4 w-4" />
            {{ $t('upDown.coins', { n: result.coins }) }}
          </p>
          <p class="text-sm text-ink-muted">
            {{ $t('upDown.yourCall', { choice: $t(`upDown.${choice}`) }) }}
          </p>
        </div>

        <p class="mt-3 text-base font-bold text-ink">
          {{ result.direction === 'up' ? $t('upDown.wentUp') : $t('upDown.wentDown') }}:
          <span :class="result.direction === 'up' ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'">{{ move }}</span>
        </p>

        <div class="mt-4 grid gap-3 @2xl:grid-cols-2">
          <div class="rounded-2xl bg-surface-2 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-ink-muted">{{ $t('upDown.why') }}</p>
            <p class="mt-1.5 text-[0.95rem] leading-relaxed text-ink">{{ result.explain }}</p>
          </div>
          <div class="game-lesson rounded-2xl p-4">
            <p class="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-brand-700 dark:text-brand-300">
              <Icon name="book" class="h-3.5 w-3.5" />
              {{ $t('upDown.lesson') }}
            </p>
            <p class="mt-1.5 text-[0.95rem] font-medium leading-relaxed text-ink">{{ result.lesson }}</p>
          </div>
        </div>

        <div class="mt-5 flex flex-wrap items-center gap-2">
          <button type="button" class="game-ask" @click="askWhy">
            <AiAvatar class="h-6 w-6" />
            {{ $t('upDown.askAI') }}
          </button>
          <button
            v-if="left > 0"
            ref="nextButton"
            type="button"
            class="pill ml-auto bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition duration-200 ease-out hover:-translate-y-px hover:bg-brand-700 motion-reduce:hover:translate-y-0"
            @click="load"
          >
            {{ $t('upDown.next') }}
            <Icon name="arrowRight" class="h-4 w-4" />
          </button>
          <RouterLink
            v-else
            ref="nextButton"
            :to="{ name: 'practice' }"
            class="pill ml-auto bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700"
          >
            {{ $t('upDown.toPractice') }}
            <Icon name="arrowRight" class="h-4 w-4" />
          </RouterLink>
        </div>
        <p v-if="left === 0" class="mt-3 text-sm text-ink-muted">{{ $t('upDown.doneToday', { n: perDay }) }}</p>
      </div>

      <p class="mt-5 border-t border-hairline pt-3 text-xs text-ink-muted">{{ $t('upDown.smoothed') }}</p>
    </section>
  </div>
</template>

<style scoped>
.game-stat {
  border-radius: 1rem;
  border: 1px solid var(--color-hairline);
  background: var(--surface);
  padding: 0.6rem 0.8rem;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
.game-stat dt {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-ink-muted);
}
.game-stat dd {
  margin-top: 0.15rem;
  min-height: 1.4rem;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-ink);
}
.game-stat--hot {
  border-color: rgb(249 115 22 / 0.5);
  box-shadow: 0 0 0 3px rgb(249 115 22 / 0.12);
}
.game-pip {
  height: 0.55rem;
  width: 1.25rem;
  border-radius: 999px;
  background: var(--brand-500, #3b82f6);
  transition: background-color 0.3s ease;
}
.game-pip.is-used {
  background: rgb(148 163 184 / 0.3);
}
.game-bump {
  display: inline-block;
  animation: game-pop 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.game-news {
  display: flex;
  gap: 0.5rem;
  border-radius: 0.9rem;
  border: 1px solid var(--color-hairline);
  background: var(--surface-2, #f1f5f9);
  padding: 0.65rem 0.8rem;
  font-size: 0.92rem;
  font-weight: 600;
  line-height: 1.45;
  color: var(--color-ink);
}

.game-call {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border-radius: 1rem;
  padding: 0.95rem 1rem;
  font-size: 1.05rem;
  font-weight: 800;
  color: #fff;
  transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
}
.game-call--up {
  background: linear-gradient(180deg, #22c55e, #16a34a);
  box-shadow: 0 10px 24px -12px rgb(22 163 74 / 0.8);
}
.game-call--down {
  background: linear-gradient(180deg, #f87171, #dc2626);
  box-shadow: 0 10px 24px -12px rgb(220 38 38 / 0.8);
}
.game-call:not(:disabled):hover {
  transform: translateY(-2px);
  filter: brightness(1.05);
}
.game-call:not(:disabled):active {
  transform: translateY(0) scale(0.98);
}
.game-call:disabled {
  opacity: 0.6;
}
.game-call:focus-visible,
.game-ask:focus-visible {
  outline: 2px solid var(--brand-500, #3b82f6);
  outline-offset: 3px;
}

.game-reveal {
  animation: game-rise 0.4s ease-out 0.5s both;
}
.game-coins {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  border-radius: 999px;
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
  padding: 0.25rem 0.75rem;
  font-size: 0.85rem;
  font-weight: 800;
  color: #fff;
  animation: game-coin 0.9s cubic-bezier(0.34, 1.56, 0.64, 1) 0.9s both;
}
.game-lesson {
  border: 1px solid color-mix(in oklab, var(--brand-500, #3b82f6) 30%, transparent);
  background: color-mix(in oklab, var(--brand-500, #3b82f6) 7%, transparent);
}
.game-ask {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border-radius: 999px;
  border: 1px solid var(--color-hairline);
  background: var(--surface);
  padding: 0.35rem 0.95rem 0.35rem 0.35rem;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-ink);
  transition: border-color 0.2s ease, transform 0.2s ease;
}
.game-ask:hover {
  transform: translateY(-1px);
  border-color: var(--brand-400, #7aa7ff);
}

@keyframes game-pop {
  0% { transform: scale(0.8); }
  60% { transform: scale(1.12); }
  100% { transform: scale(1); }
}
@keyframes game-rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes game-coin {
  0% { opacity: 0; transform: translateY(10px) scale(0.6); }
  60% { opacity: 1; transform: translateY(-4px) scale(1.1); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}
@media (prefers-reduced-motion: reduce) {
  .game-bump,
  .game-reveal,
  .game-coins {
    animation: none;
  }
}
</style>
