<script setup>
/**
 * Zinvest Daily — five short situations, about two minutes, once a day.
 *
 * The whole thing happens inside this card: no route change, no modal. That is
 * deliberate. The point of a daily habit is that it costs nothing to start, and
 * a screen the learner has to navigate to is already a decision.
 *
 * The bear only shows up when there is something to say: after an answer, and
 * at the end. He is the one explaining, so the explanation is his line, not a
 * grey box of feedback text.
 */
import { computed, ref } from 'vue'

import BearMascot from '@/components/mascot/BearMascot.vue'
import Icon from '@/components/ui/Icon.vue'
import { answerDaily, getDaily } from '@/api/daily'
import { useAsyncData } from '@/composables/useAsyncData'
import { useSharedStats } from '@/composables/useSharedStats'

const { data, loading, reload } = useAsyncData(getDaily)
const { reload: reloadStats } = useSharedStats()

const sending = ref(false)
// The answer just played, held until the learner moves on, so the explanation
// stays on screen instead of flashing past.
const shown = ref(null)
const done = ref(null)

const size = computed(() => data.value?.size || 0)
const answered = computed(() => data.value?.answered || 0)
const finished = computed(() => !!data.value?.finished)
const current = computed(() => (data.value?.items || [])[answered.value] || null)
const maxCoins = computed(() => data.value?.max_coins || 0)

// One dot per question: filled for played, ringed for the one on screen.
const dots = computed(() =>
  Array.from({ length: size.value }, (_, i) => ({
    i,
    played: i < answered.value,
    now: i === answered.value && !finished.value,
  })),
)

async function choose(index) {
  if (sending.value || shown.value) return
  sending.value = true
  try {
    const result = await answerDaily(index)
    shown.value = result
    if (result.finished) {
      done.value = result
      // Awaited, so the coin and streak counters in the top bar have moved by
      // the time the learner reads the reward line. A reward that only lands
      // after a reload is not felt as a reward.
      await reloadStats()
    }
  } finally {
    sending.value = false
  }
}

async function next() {
  shown.value = null
  await reload()
}

const bearMood = computed(() => {
  if (done.value) return 'celebrate'
  return shown.value?.correct ? 'happy' : 'confused'
})
</script>

<template>
  <section v-if="data?.available" class="card mb-5 overflow-hidden p-5 sm:p-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="flex items-center gap-2 text-base font-bold text-ink">
          <Icon name="zap" class="h-4 w-4 text-brand-600 dark:text-brand-400" />
          {{ $t('daily.title') }}
        </h2>
        <p class="mt-0.5 text-xs text-ink-muted">
          {{ $t('daily.meta', { coins: maxCoins }) }}
        </p>
      </div>

      <ol class="flex items-center gap-1.5" :aria-label="$t('daily.progress', { done: answered, total: size })">
        <li
          v-for="dot in dots"
          :key="dot.i"
          class="h-2 rounded-full transition-all duration-300 ease-out"
          :class="
            dot.played
              ? 'w-5 bg-brand-500'
              : dot.now
                ? 'w-5 bg-brand-500/30 ring-1 ring-brand-500'
                : 'w-2 bg-surface-2'
          "
        />
      </ol>
    </header>

    <!-- The finished state stays all day: a done thing should look done. -->
    <div v-if="finished && !shown" class="mt-5 flex items-center gap-4">
      <div class="h-20 w-20 shrink-0"><BearMascot mood="happy" :decorations="false" /></div>
      <div class="min-w-0">
        <p class="font-semibold text-ink">
          {{ $t('daily.doneTitle', { correct: data.correct, total: size }) }}
        </p>
        <p class="mt-0.5 text-sm text-ink-muted">
          {{ $t('daily.doneBody', { coins: data.coins_awarded }) }}
        </p>
      </div>
    </div>

    <div v-else-if="loading && !current" class="mt-5 h-24 animate-pulse rounded-2xl bg-surface-2" />

    <template v-else>
      <!-- Question -->
      <p v-if="current && !shown" class="mt-5 text-[1.05rem] font-semibold leading-snug text-ink">
        {{ current.question }}
      </p>

      <div v-if="current && !shown" class="mt-4 grid gap-2">
        <button
          v-for="(option, index) in current.options"
          :key="index"
          type="button"
          :disabled="sending"
          class="group flex items-center gap-3 rounded-xl border border-hairline bg-surface px-4 py-3 text-left text-sm text-ink transition duration-200 ease-out hover:-translate-y-px hover:border-brand-400 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 disabled:opacity-60 motion-reduce:hover:translate-y-0"
          @click="choose(index)"
        >
          <span
            class="grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-surface-2 text-[0.7rem] font-bold text-ink-muted transition-colors duration-200 group-hover:bg-brand-500 group-hover:text-white"
          >
            {{ String.fromCharCode(65 + index) }}
          </span>
          {{ option }}
        </button>
      </div>

      <!-- What the bear says about the answer just given. -->
      <div v-if="shown" class="mt-5">
        <p
          class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold"
          :class="shown.correct ? 'bg-mint text-mint-ink' : 'bg-surface-2 text-ink-muted'"
        >
          <Icon :name="shown.correct ? 'checkCircle' : 'alert'" class="h-3.5 w-3.5" />
          {{ shown.correct ? $t('daily.right') : $t('daily.wrong') }}
        </p>

        <div class="mt-3 flex items-start gap-3">
          <div class="h-16 w-16 shrink-0 sm:h-20 sm:w-20">
            <BearMascot :mood="bearMood" :decorations="false" />
          </div>
          <p class="min-w-0 pt-1 text-sm leading-relaxed text-ink">{{ shown.explain }}</p>
        </div>

        <div v-if="done" class="mt-4 rounded-2xl bg-surface-2 px-4 py-3">
          <p class="text-sm font-semibold text-ink">
            {{ $t('daily.doneTitle', { correct: done.correct, total: size }) }}
          </p>
          <p class="mt-0.5 text-sm text-ink-muted">
            {{ $t('daily.reward', { coins: done.coins_awarded, streak: done.streak }) }}
          </p>
        </div>

        <button
          v-if="!done"
          type="button"
          class="pill mt-4 bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition duration-200 ease-out hover:-translate-y-px hover:bg-brand-700 motion-reduce:hover:translate-y-0"
          @click="next"
        >
          {{ $t('daily.next') }}
          <Icon name="arrowRight" class="h-4 w-4" />
        </button>
      </div>
    </template>
  </section>
</template>
