<script setup>
/**
 * The practice trainer: the question bank, one question at a time, for as
 * long as the learner likes. The same bank and the same grading as the bot's
 * /quiz, so a question answered in one is not asked straight back in the other.
 *
 * No coins — the Daily is the habit and pays for it; this is the gym. What it
 * does keep is a run of right answers in a row, because a streak you can feel
 * is the cheapest motivation there is, and losing it costs nothing.
 *
 * Every question ends in its explanation. "Ask the AI" is there after
 * answering (why is this the answer?) and instead of answering (just tell
 * me) — the second shows the answer too, and the question then counts as not
 * solved, so it comes back another day.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import AiAvatar from '@/components/ai/AiAvatar.vue'
import BearMascot from '@/components/mascot/BearMascot.vue'
import Icon from '@/components/ui/Icon.vue'
import { answerPractice, nextPractice } from '@/api/games'
import { useAskAI } from '@/composables/useAskAI'

const { t } = useI18n()
const { askAbout } = useAskAI()

const topic = ref('') // '' is every topic
const question = ref(null)
const topics = ref([])
const stats = ref(null)
const result = ref(null) // the graded answer, kept on screen until "next"
const loading = ref(true)
const sending = ref(false)
const failed = ref('')
const combo = ref(0)
const nextButton = ref(null)
const whyButton = ref(null)

const letters = ['A', 'B', 'C', 'D', 'E', 'F']
const total = computed(() => topics.value.reduce((sum, item) => sum + item.count, 0))
const accuracy = computed(() =>
  stats.value?.total ? Math.round((100 * stats.value.correct) / stats.value.total) : null,
)
const mood = computed(() => {
  if (!result.value) return 'think'
  if (result.value.revealed) return 'idle'
  if (result.value.correct) return combo.value >= 3 ? 'celebrate' : 'happy'
  return 'confused'
})
const verdict = computed(() => {
  if (!result.value) return ''
  if (result.value.revealed) return t('trainer.revealed')
  return result.value.correct ? t('trainer.right') : t('trainer.wrong')
})

async function load(after = '') {
  loading.value = true
  failed.value = ''
  try {
    const data = await nextPractice({ topic: topic.value, after })
    question.value = data.question
    topics.value = data.topics || []
    stats.value = data.stats
    result.value = null
  } catch (e) {
    failed.value = e?.response?.data?.detail || t('errors.generic')
  } finally {
    loading.value = false
  }
}

async function grade(how) {
  if (!question.value || result.value || sending.value) return null
  sending.value = true
  failed.value = ''
  try {
    const graded = await answerPractice(question.value.id, how)
    result.value = graded
    stats.value = graded.stats
    combo.value = graded.correct ? combo.value + 1 : 0
    await nextTick()
    nextButton.value?.focus({ preventScroll: true })
    return graded
  } catch (e) {
    failed.value = e?.response?.data?.detail || t('errors.generic')
    return null
  } finally {
    sending.value = false
  }
}

function choose(index) {
  grade({ choice: index })
}

// The question in words the AI can answer well: every option, and the right
// one named, so the explanation can never argue for a different answer.
function prompt(kind, graded) {
  const options = graded.options.map((option, i) => `${letters[i]}) ${option}`).join('; ')
  const wrong = !graded.correct && graded.chosen !== null && graded.chosen !== undefined
  return t(`trainer.ask.${kind}`, {
    question: graded.question,
    options,
    correct: graded.options[graded.answer],
    chosen: wrong ? t('trainer.ask.chosen', { chosen: graded.options[graded.chosen] }) : '',
  })
}

function anchor(event) {
  return event?.currentTarget?.getBoundingClientRect?.() || null
}

async function askForAnswer() {
  const graded = await grade({ reveal: true })
  if (!graded) return
  // The button that was pressed is gone with the reveal: the answer card
  // opens by the explanation instead, where the next question is asked.
  await nextTick()
  whyButton.value?.scrollIntoView({ block: 'center' })
  askAbout(prompt('reveal', graded), graded.question, whyButton.value?.getBoundingClientRect() || null)
}

function askWhy(event) {
  if (result.value) askAbout(prompt('explain', result.value), result.value.question, anchor(event))
}

function next() {
  load(question.value?.id || '')
}

function pickTopic(key) {
  if (topic.value === key || sending.value) return
  topic.value = key
  load()
}

function optionState(index) {
  const r = result.value
  if (!r) return ''
  if (index === r.answer) return 'is-right'
  if (index === r.chosen) return 'is-wrong'
  return 'is-dim'
}

// 1–4 (or A–D) answers. Enter needs no handler: the Next button has focus.
function onKey(event) {
  if (result.value || !question.value || event.metaKey || event.ctrlKey || event.altKey) return
  if (event.target?.closest?.('input, textarea, select, [contenteditable="true"]')) return
  const key = event.key.toLowerCase()
  const index = '1234'.includes(key) ? Number(key) - 1 : 'abcd'.indexOf(key)
  if (index >= 0 && index < question.value.options.length) {
    event.preventDefault()
    choose(index)
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
        <h1 class="text-3xl font-extrabold text-ink">{{ $t('trainer.title') }}</h1>
        <p class="mt-2 max-w-2xl text-ink-muted">{{ $t('trainer.lead') }}</p>
      </div>
      <div class="hidden h-28 w-24 shrink-0 sm:block">
        <BearMascot :mood="mood" :decorations="false" />
      </div>
    </header>

    <!-- The tally: today, overall, and the run in a row. -->
    <dl class="mb-5 grid grid-cols-3 gap-2 sm:max-w-xl">
      <div class="trainer-stat">
        <dt>{{ $t('trainer.today') }}</dt>
        <dd>{{ stats ? $t('trainer.todayValue', { correct: stats.today_correct, total: stats.today }) : '—' }}</dd>
      </div>
      <div class="trainer-stat">
        <dt>{{ $t('trainer.accuracy') }}</dt>
        <dd>{{ accuracy === null ? '—' : `${accuracy}%` }}</dd>
      </div>
      <div class="trainer-stat" :class="{ 'trainer-stat--hot': combo >= 3 }">
        <dt>{{ $t('trainer.combo') }}</dt>
        <dd class="flex items-center gap-1">
          <Icon name="flame" class="h-4 w-4" :class="combo ? 'text-orange-500' : 'text-slate-400'" />
          <span :key="combo" class="trainer-combo">{{ combo }}</span>
        </dd>
      </div>
    </dl>

    <!-- Topics -->
    <div class="-mx-1 mb-5 flex gap-2 overflow-x-auto px-1 pb-1 sm:flex-wrap sm:overflow-visible" role="group" :aria-label="$t('trainer.allTopics')">
      <button type="button" class="trainer-chip" :class="{ 'is-on': topic === '' }" :aria-pressed="topic === ''" @click="pickTopic('')">
        {{ $t('trainer.allTopics') }}
        <span class="trainer-chip__count">{{ total }}</span>
      </button>
      <button
        v-for="item in topics"
        :key="item.key"
        type="button"
        class="trainer-chip"
        :class="{ 'is-on': topic === item.key }"
        :aria-pressed="topic === item.key"
        @click="pickTopic(item.key)"
      >
        {{ $t(`trainer.topics.${item.key}`) }}
        <span class="trainer-chip__count">{{ item.count }}</span>
      </button>
    </div>

    <p v-if="failed" role="alert" class="mb-4 text-sm text-red-600 dark:text-red-400">{{ failed }}</p>

    <section class="card p-5 sm:p-6" aria-live="polite">
      <div v-if="loading && !question" class="space-y-3" aria-hidden="true">
        <div class="h-4 w-24 animate-pulse rounded bg-surface-2" />
        <div class="h-6 w-4/5 animate-pulse rounded bg-surface-2" />
        <div v-for="i in 4" :key="i" class="h-12 animate-pulse rounded-xl bg-surface-2" />
      </div>

      <p v-else-if="!question" class="py-8 text-center text-ink-muted">{{ $t('trainer.empty') }}</p>

      <div v-else :class="{ 'opacity-60 transition-opacity': loading }">
        <p class="text-xs font-bold uppercase tracking-wide text-brand-600 dark:text-brand-400">
          {{ $t(`trainer.topics.${question.topic}`) }}
        </p>
        <h2 class="mt-2 text-lg font-semibold leading-snug text-ink sm:text-xl">{{ question.question }}</h2>

        <div class="mt-5 grid gap-2">
          <button
            v-for="(option, index) in question.options"
            :key="index"
            type="button"
            class="trainer-option"
            :class="optionState(index)"
            :disabled="sending || !!result"
            @click="choose(index)"
          >
            <span class="trainer-option__letter">
              <Icon v-if="optionState(index) === 'is-right'" name="check" class="h-3.5 w-3.5" />
              <Icon v-else-if="optionState(index) === 'is-wrong'" name="x" class="h-3.5 w-3.5" />
              <template v-else>{{ letters[index] }}</template>
            </span>
            <span class="min-w-0 flex-1">{{ option }}</span>
          </button>
        </div>

        <!-- Before answering: the way out that still teaches. -->
        <div v-if="!result" class="mt-4 flex flex-wrap items-center justify-between gap-3">
          <button type="button" class="trainer-ask" :disabled="sending" @click="askForAnswer">
            <AiAvatar class="h-6 w-6" />
            {{ $t('trainer.askAnswer') }}
          </button>
          <span class="hidden text-xs text-ink-muted sm:inline">{{ $t('trainer.keys') }}</span>
        </div>
        <p v-if="!result" class="mt-2 text-xs text-ink-muted">{{ $t('trainer.revealHint') }}</p>

        <!-- After: the verdict, the explanation, and the way on. -->
        <div v-if="result" class="trainer-result mt-5">
          <div class="flex flex-wrap items-center gap-2">
            <p
              class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-bold"
              :class="
                result.revealed
                  ? 'bg-surface-2 text-ink'
                  : result.correct
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300'
                    : 'bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300'
              "
            >
              <Icon :name="result.revealed ? 'eye' : result.correct ? 'checkCircle' : 'alert'" class="h-4 w-4" />
              {{ verdict }}
            </p>
            <p v-if="result.correct && combo >= 3" :key="combo" class="trainer-toast">
              <Icon name="flame" class="h-4 w-4" />
              {{ $t('trainer.comboToast', { n: combo }) }}
            </p>
          </div>

          <div class="mt-3 flex items-start gap-3">
            <div class="h-14 w-14 shrink-0 sm:hidden"><BearMascot :mood="mood" :decorations="false" /></div>
            <p class="min-w-0 text-[0.95rem] leading-relaxed text-ink">{{ result.explain }}</p>
          </div>

          <div class="mt-5 flex flex-wrap gap-2">
            <button ref="whyButton" type="button" class="trainer-ask" @click="askWhy">
              <AiAvatar class="h-6 w-6" />
              {{ $t('trainer.askWhy') }}
            </button>
            <button
              ref="nextButton"
              type="button"
              class="pill ml-auto bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition duration-200 ease-out hover:-translate-y-px hover:bg-brand-700 motion-reduce:hover:translate-y-0"
              :disabled="loading"
              @click="next"
            >
              {{ $t('trainer.next') }}
              <Icon name="arrowRight" class="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.trainer-stat {
  border-radius: 1rem;
  border: 1px solid var(--color-hairline);
  background: var(--surface);
  padding: 0.6rem 0.8rem;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
.trainer-stat dt {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-ink-muted);
}
.trainer-stat dd {
  margin-top: 0.15rem;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-ink);
}
.trainer-stat--hot {
  border-color: rgb(249 115 22 / 0.5);
  box-shadow: 0 0 0 3px rgb(249 115 22 / 0.12);
}
.trainer-combo {
  display: inline-block;
  animation: trainer-pop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.trainer-chip {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 0.4rem;
  border-radius: 999px;
  border: 1px solid var(--color-hairline);
  background: var(--surface);
  padding: 0.4rem 0.85rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-ink);
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}
.trainer-chip:hover {
  border-color: var(--brand-400, #7aa7ff);
}
.trainer-chip.is-on {
  border-color: var(--brand-600, #2563eb);
  background: var(--brand-600, #2563eb);
  color: #fff;
}
.trainer-chip__count {
  border-radius: 999px;
  background: rgb(148 163 184 / 0.18);
  padding: 0 0.4rem;
  font-size: 0.7rem;
  font-weight: 700;
}
.trainer-chip.is-on .trainer-chip__count {
  background: rgb(255 255 255 / 0.22);
}
.trainer-chip:focus-visible,
.trainer-option:focus-visible,
.trainer-ask:focus-visible {
  outline: 2px solid var(--brand-500, #3b82f6);
  outline-offset: 2px;
}

.trainer-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border-radius: 0.9rem;
  border: 1px solid var(--color-hairline);
  background: var(--surface);
  padding: 0.8rem 1rem;
  text-align: left;
  font-size: 0.95rem;
  color: var(--color-ink);
  transition: transform 0.2s ease, border-color 0.2s ease, background-color 0.2s ease, opacity 0.2s ease;
}
.trainer-option:not(:disabled):hover {
  transform: translateY(-1px);
  border-color: var(--brand-400, #7aa7ff);
  background: var(--surface-2, #f1f5f9);
}
.trainer-option__letter {
  display: grid;
  height: 1.6rem;
  width: 1.6rem;
  flex-shrink: 0;
  place-items: center;
  border-radius: 0.5rem;
  background: var(--surface-2, #f1f5f9);
  font-size: 0.72rem;
  font-weight: 800;
  color: var(--color-ink-muted);
  transition: background-color 0.2s ease, color 0.2s ease;
}
.trainer-option:not(:disabled):hover .trainer-option__letter {
  background: var(--brand-500, #3b82f6);
  color: #fff;
}
.trainer-option.is-right {
  border-color: #22c55e;
  background: rgb(34 197 94 / 0.1);
  animation: trainer-pop 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.trainer-option.is-right .trainer-option__letter {
  background: #22c55e;
  color: #fff;
}
.trainer-option.is-wrong {
  border-color: #ef4444;
  background: rgb(239 68 68 / 0.08);
  animation: trainer-shake 0.4s ease;
}
.trainer-option.is-wrong .trainer-option__letter {
  background: #ef4444;
  color: #fff;
}
.trainer-option.is-dim {
  opacity: 0.55;
}

.trainer-ask {
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
.trainer-ask:not(:disabled):hover {
  transform: translateY(-1px);
  border-color: var(--brand-400, #7aa7ff);
}
.trainer-ask:disabled {
  opacity: 0.6;
}

.trainer-result {
  animation: trainer-rise 0.35s ease-out;
}
.trainer-toast {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border-radius: 999px;
  background: linear-gradient(90deg, #f97316, #f59e0b);
  padding: 0.25rem 0.75rem;
  font-size: 0.85rem;
  font-weight: 800;
  color: #fff;
  animation: trainer-pop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes trainer-pop {
  0% { transform: scale(0.85); }
  60% { transform: scale(1.06); }
  100% { transform: scale(1); }
}
@keyframes trainer-shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}
@keyframes trainer-rise {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
@media (prefers-reduced-motion: reduce) {
  .trainer-combo,
  .trainer-option.is-right,
  .trainer-option.is-wrong,
  .trainer-result,
  .trainer-toast {
    animation: none;
  }
}
</style>
