<script setup>
/**
 * Unit test: the last node of every unit on the study map. One question at a
 * time, graded on submit (the answer key stays on the server until then), then
 * a result screen where the bear celebrates a pass or cheers the learner on,
 * with a review of every answer.
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import BearMascot from '@/components/mascot/BearMascot.vue'
import BearSticker from '@/components/mascot/BearSticker.vue'
import Icon from '@/components/ui/Icon.vue'
import { startUnitTest, submitUnitTest } from '@/api/units'
import { useSharedStats } from '@/composables/useSharedStats'
import { useNarrator } from '@/voice/narrator'

const route = useRoute()
const router = useRouter()
const { reload: reloadStats } = useSharedStats()

const phase = ref('loading') // loading | error | locked | empty | intro | question | submitting | result
const test = ref(null)
const index = ref(0)
const answers = ref({})
const result = ref(null)

const questions = computed(() => test.value?.questions || [])
const question = computed(() => questions.value[index.value])
const passPercent = computed(() => Math.round((test.value?.pass_threshold || 0) * 100))
const progress = computed(() => (phase.value === 'result' ? 100 : Math.round((index.value / Math.max(1, questions.value.length)) * 100)))
const isLast = computed(() => index.value === questions.value.length - 1)
const selected = computed({
  get: () => answers.value[question.value?.id] ?? null,
  set: (v) => { answers.value = { ...answers.value, [question.value.id]: v } },
})

let generation = 0
async function load() {
  const id = ++generation
  phase.value = 'loading'
  result.value = null
  answers.value = {}
  index.value = 0
  try {
    const data = await startUnitTest(route.params.unitId)
    if (id !== generation) return
    test.value = data
    phase.value = data.questions?.length ? 'intro' : 'empty'
  } catch (e) {
    if (id !== generation) return
    phase.value = e?.response?.status === 403 ? 'locked' : 'error'
  }
}
watch(() => route.params.unitId, (unitId) => unitId && load(), { immediate: true })

// A new language mid-test: fetch the same questions in it and keep the answers
// given so far — ids and options do not change between languages.
async function relabel() {
  if (!test.value || !['intro', 'question'].includes(phase.value)) return
  try {
    const data = await startUnitTest(route.params.unitId)
    test.value = { ...test.value, unit_title: data.unit_title, questions: data.questions }
  } catch {
    /* keep the words already on screen */
  }
}

function begin() {
  index.value = 0
  phase.value = 'question'
}
function next() {
  if (selected.value === null) return
  if (isLast.value) submit()
  else index.value++
}
function prev() {
  if (index.value > 0) index.value--
}

async function submit() {
  phase.value = 'submitting'
  try {
    const payload = questions.value.map((q) => ({ question_id: q.id, choice_index: answers.value[q.id] ?? null }))
    result.value = await submitUnitTest(route.params.unitId, payload)
    phase.value = 'result'
    reloadStats()
  } catch {
    phase.value = 'error'
  }
}

function retry() {
  answers.value = {}
  result.value = null
  begin()
}
function exit() {
  router.push({ name: 'studyPlan', query: { unit: route.params.unitId } })
}

// The bear says how it went.
const { t, locale } = useI18n()
watch(locale, relabel)
const narrator = useNarrator()
const bearTalking = computed(() => narrator.state.speaking && narrator.state.owner === 'test')
watch(phase, (now) => {
  if (now === 'result' && result.value) narrator.speak(t(result.value.passed ? 'voice.testPassed' : 'voice.testFailed'), { owner: 'test', lang: locale.value })
})
onBeforeUnmount(() => { if (narrator.state.owner === 'test') narrator.stop() })

const reviewRows = computed(() => (result.value?.review || []).map((r) => {
  const q = questions.value.find((x) => x.id === r.question_id) || { prompt: '', choices: [] }
  return { ...r, prompt: q.prompt, chosen: q.choices[r.chosen_index], answer: q.choices[r.answer_index] }
}))
</script>

<template>
  <div class="flex min-h-screen flex-col bg-canvas">
    <header class="sticky top-0 z-10 border-b border-hairline bg-white/95 backdrop-blur dark:bg-surface/95">
      <div class="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
        <button type="button" class="flex h-10 items-center gap-2 rounded-full px-3 text-sm font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2" @click="exit">
          <Icon name="x" class="h-4 w-4" /> {{ $t('unitTest.exit') }}
        </button>
        <div class="h-3 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-surface-2" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100" :aria-label="$t('unitTest.label')">
          <div class="h-full rounded-full bg-brand-600 transition-[width] duration-500 ease-out" :style="{ width: progress + '%' }" />
        </div>
        <span v-if="phase === 'question'" class="w-14 shrink-0 text-right text-sm font-semibold tabular-nums text-slate-500">{{ index + 1 }}/{{ questions.length }}</span>
      </div>
    </header>

    <main class="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-6 sm:py-10">
      <!-- Loading -->
      <div v-if="phase === 'loading'" class="m-auto h-40 w-40" role="status" :aria-label="$t('common.loading')">
        <BearSticker name="think" float class="h-full w-full" />
      </div>

      <!-- Problems -->
      <div v-else-if="['error', 'locked', 'empty'].includes(phase)" class="m-auto max-w-md text-center">
        <BearSticker :name="phase === 'locked' ? 'sleep' : 'confused'" pop class="mx-auto h-44 w-44" />
        <p class="mt-2 text-lg font-bold text-slate-900 dark:text-white">
          {{ phase === 'locked' ? $t('unitTest.locked') : phase === 'empty' ? $t('unitTest.empty') : $t('unitTest.loadError') }}
        </p>
        <div class="mt-6 flex flex-wrap justify-center gap-2">
          <button v-if="phase === 'error'" type="button" class="min-h-11 rounded-2xl bg-brand-600 px-5 font-semibold text-white" @click="load">{{ $t('unitTest.retry') }}</button>
          <button type="button" class="min-h-11 rounded-2xl border border-hairline px-5 font-semibold" @click="exit">{{ $t('celebration.toPlan') }}</button>
        </div>
      </div>

      <!-- Intro -->
      <section v-else-if="phase === 'intro'" class="m-auto w-full max-w-md text-center">
        <div class="mx-auto h-56 w-56"><BearMascot mood="warmup" interactive :label="$t('mascot.tap')" /></div>
        <p class="mt-2 text-sm font-semibold uppercase tracking-wider text-brand-600">{{ $t('unitTest.label') }}</p>
        <h1 class="mt-1 text-3xl font-extrabold text-slate-900 dark:text-white">{{ test.unit_title }}</h1>
        <p class="mt-3 text-slate-600 dark:text-slate-300">{{ $t('unitTest.intro', { n: questions.length, pass: passPercent }) }}</p>
        <p class="mt-2 text-sm text-slate-500">{{ test.coin_reward ? $t('unitTest.reward', { n: test.coin_reward }) : $t('unitTest.noReward') }}</p>
        <button type="button" class="mt-7 min-h-12 w-full rounded-2xl bg-brand-600 px-6 text-lg font-bold text-white shadow-sm transition hover:bg-brand-700" @click="begin">{{ $t('unitTest.start') }}</button>
      </section>

      <!-- Question -->
      <section v-else-if="phase === 'question' && question" :key="question.id" class="zt-question flex flex-1 flex-col">
        <div class="flex items-start gap-3">
          <BearSticker name="think" class="hidden h-20 w-20 shrink-0 sm:block" />
          <div class="min-w-0">
            <p class="text-sm font-semibold text-brand-600">{{ $t('unitTest.question', { i: index + 1, n: questions.length }) }}</p>
            <h1 class="mt-1 text-xl font-bold leading-snug text-slate-900 sm:text-2xl dark:text-white">{{ question.prompt }}</h1>
          </div>
        </div>
        <fieldset class="mt-6 space-y-3">
          <legend class="sr-only">{{ question.prompt }}</legend>
          <label
            v-for="(choice, i) in question.choices"
            :key="i"
            class="flex min-h-14 cursor-pointer items-center gap-3 rounded-2xl border-2 bg-white px-4 py-3 text-base transition has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-500 dark:bg-surface"
            :class="selected === i ? 'border-brand-500 bg-brand-50/60 dark:bg-brand-500/10' : 'border-hairline hover:border-slate-300 dark:hover:border-slate-500'"
          >
            <input v-model="selected" type="radio" class="sr-only" :value="i" :name="`test-${question.id}`" />
            <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border text-sm font-bold" :class="selected === i ? 'border-brand-500 bg-brand-600 text-white' : 'border-slate-300 text-slate-500 dark:border-slate-600'">{{ i + 1 }}</span>
            <span>{{ choice }}</span>
          </label>
        </fieldset>
        <div class="mt-auto flex items-center justify-between gap-3 pt-8 sm:mt-10 sm:pt-0">
          <button type="button" :disabled="index === 0" class="min-h-12 rounded-2xl px-5 font-semibold text-slate-600 hover:bg-slate-100 disabled:invisible dark:text-slate-300 dark:hover:bg-surface-2" @click="prev">{{ $t('unitTest.prev') }}</button>
          <button type="button" :disabled="selected === null" class="min-h-12 rounded-2xl bg-brand-600 px-7 font-bold text-white shadow-sm transition hover:bg-brand-700 disabled:opacity-40" @click="next">{{ isLast ? $t('unitTest.finish') : $t('unitTest.next') }}</button>
        </div>
      </section>

      <!-- Grading -->
      <div v-else-if="phase === 'submitting'" class="m-auto text-center" role="status">
        <BearSticker name="think" float class="mx-auto h-40 w-40" />
        <p class="mt-2 font-semibold text-slate-600 dark:text-slate-300">{{ $t('unitTest.checking') }}</p>
      </div>

      <!-- Result -->
      <section v-else-if="phase === 'result' && result" class="w-full">
        <div class="mx-auto max-w-md text-center">
          <div class="mx-auto h-60 w-60"><BearMascot :mood="result.passed ? 'celebrate' : 'cheer'" interactive :label="$t('mascot.tap')" :voice="bearTalking ? narrator.level : null" /></div>
          <h1 class="text-3xl font-extrabold text-slate-900 dark:text-white">{{ result.passed ? $t('unitTest.passedTitle') : $t('unitTest.failedTitle') }}</h1>
          <p class="mt-2 text-lg font-semibold" :class="result.passed ? 'text-emerald-600' : 'text-amber-600'">{{ $t('unitTest.score', { score: result.score }) }} · {{ $t('unitTest.correctCount', { c: result.correct_count, n: result.total_count }) }}</p>
          <p class="mt-2 text-slate-600 dark:text-slate-300">{{ result.passed ? $t('unitTest.passedText') : $t('unitTest.needed', { pass: passPercent }) }}</p>
          <div v-if="result.coins_awarded || result.day_streak" class="mt-4 flex flex-wrap justify-center gap-2">
            <span v-if="result.coins_awarded" class="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1.5 text-sm font-bold text-amber-700 dark:bg-amber-500/15 dark:text-amber-300"><Icon name="coin" class="h-4 w-4" /> {{ $t('celebration.coins', { n: result.coins_awarded }) }}</span>
            <span v-if="result.day_streak" class="inline-flex items-center gap-1.5 rounded-full bg-orange-50 px-3 py-1.5 text-sm font-bold text-orange-700 dark:bg-orange-500/15 dark:text-orange-300"><Icon name="flame" filled class="h-4 w-4" /> {{ $t('celebration.streak', { n: result.day_streak }) }}</span>
          </div>
          <div class="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
            <button type="button" class="min-h-12 rounded-2xl bg-brand-600 px-6 font-bold text-white shadow-sm hover:bg-brand-700" @click="result.passed ? exit() : retry()">{{ result.passed ? $t('celebration.toPlan') : $t('unitTest.retry') }}</button>
            <button type="button" class="min-h-12 rounded-2xl border border-hairline px-6 font-semibold hover:bg-slate-50 dark:hover:bg-surface-2" @click="result.passed ? retry() : exit()">{{ result.passed ? $t('unitTest.retry') : $t('unitTest.lessons') }}</button>
          </div>
        </div>

        <h2 class="mt-10 text-lg font-bold text-slate-900 dark:text-white">{{ $t('unitTest.review') }}</h2>
        <ol class="mt-3 space-y-3">
          <li v-for="(row, i) in reviewRows" :key="row.question_id" class="rounded-2xl border border-hairline bg-white p-4 dark:bg-surface">
            <div class="flex items-start gap-3">
              <span class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-white" :class="row.correct ? 'bg-emerald-500' : 'bg-amber-500'">
                <Icon :name="row.correct ? 'check' : 'x'" class="h-3.5 w-3.5" />
              </span>
              <div class="min-w-0">
                <p class="font-semibold text-slate-900 dark:text-white">{{ i + 1 }}. {{ row.prompt }}</p>
                <p class="mt-1 text-sm" :class="row.correct ? 'text-emerald-700 dark:text-emerald-300' : 'text-amber-700 dark:text-amber-300'">{{ $t('unitTest.yourAnswer', { answer: row.chosen ?? $t('unitTest.noAnswer') }) }}</p>
                <p v-if="!row.correct" class="mt-1 text-sm text-slate-700 dark:text-slate-200">{{ $t('mascot.rightAnswer', { answer: row.answer }) }}</p>
                <p v-if="row.explanation" class="mt-1 text-sm text-slate-500">{{ row.explanation }}</p>
              </div>
            </div>
          </li>
        </ol>
      </section>
    </main>
  </div>
</template>

<style scoped>
.zt-question { animation: zt-in 0.3s ease both; }
@keyframes zt-in { from { opacity: 0; transform: translateX(16px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .zt-question { animation: none; } }
</style>
