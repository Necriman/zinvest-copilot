<script setup>
/**
 * The ten questions after sign-up.
 *
 * Five about you (no right answers), then a five-question knowledge check,
 * one at a time. Picking an answer moves on by itself; any question can be
 * skipped, and so can the whole thing. The answers go to the server, which
 * grades the quiz and has Gemini order the lessons into a personal study
 * plan; a skipped question is simply left out, and skipping everything lands
 * on the default plan.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import BearMascot from '@/components/mascot/BearMascot.vue'
import BearThinking from '@/components/ui/BearThinking.vue'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import { getOnboarding, submitOnboarding } from '@/api/onboarding'

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const questions = ref([]) // flattened: profile questions then quiz questions
const answers = ref({}) // question id -> choice index
const step = ref(0)
const result = ref(null)
const cheer = ref(false)
let advanceTimer = null

const current = computed(() => questions.value[step.value] || null)
const total = computed(() => questions.value.length)
const isLast = computed(() => step.value === total.value - 1)
const progress = computed(() => (total.value ? (step.value / total.value) * 100 : 0))
const LETTERS = ['A', 'B', 'C', 'D', 'E']

// The bear thinks along with the quiz, and is glad for every answer.
const bearMood = computed(() => {
  if (result.value) return 'celebrate'
  if (cheer.value) return 'happy'
  return current.value?.kind === 'quiz' ? 'think' : 'reading'
})

async function loadQuestions() {
  const data = await getOnboarding()
  questions.value = [
    ...data.profile.map((q) => ({ ...q, kind: 'profile' })),
    ...data.quiz.map((q) => ({ ...q, kind: 'quiz' })),
  ]
}

onMounted(async () => {
  try {
    await loadQuestions()
  } catch {
    error.value = 'generic'
  } finally {
    loading.value = false
  }
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  clearTimeout(advanceTimer)
  window.removeEventListener('keydown', onKey)
})

// The same questions in the newly picked language; answers are indexes, so
// the ones already given still mean the same.
const { locale } = useI18n()
watch(locale, () => loadQuestions().catch(() => {}))

function forward() {
  if (isLast.value) submit()
  else step.value++
}

function pick(index) {
  if (!current.value || submitting.value) return
  answers.value = { ...answers.value, [current.value.id]: index }
  cheer.value = true
  clearTimeout(advanceTimer)
  advanceTimer = setTimeout(() => {
    cheer.value = false
    forward()
  }, 380)
}

function skipQuestion() {
  if (!current.value || submitting.value) return
  const { [current.value.id]: _dropped, ...rest } = answers.value
  answers.value = rest
  forward()
}

function back() {
  clearTimeout(advanceTimer)
  cheer.value = false
  if (step.value > 0) step.value--
}

// 1–5 or A–E picks an answer; Enter moves on when this one is answered.
function onKey(e) {
  if (!current.value || result.value || e.target?.closest?.('input, textarea')) return
  const n = Number(e.key)
  const letter = LETTERS.indexOf(String(e.key).toUpperCase())
  const index = n >= 1 && n <= 5 ? n - 1 : letter
  if (index >= 0 && index < current.value.choices.length) pick(index)
  else if (e.key === 'Enter' && answers.value[current.value.id] !== undefined) forward()
}

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    const profile = {}
    const quiz = []
    for (const q of questions.value) {
      const choice = answers.value[q.id]
      if (choice === undefined) continue
      if (q.kind === 'profile') profile[q.id] = choice
      else quiz.push({ question_id: q.id, choice_index: choice })
    }
    result.value = await submitOnboarding(profile, quiz)
  } catch {
    error.value = 'generic'
  } finally {
    submitting.value = false
  }
}

function skipAll() {
  router.push({ name: 'studyPlan' })
}
</script>

<template>
  <div class="ob">
    <div class="ob__wrap">
      <!-- Result -->
      <div v-if="result" class="ob__result">
        <div class="ob__bear ob__bear--result"><BearMascot :mood="bearMood" /></div>
        <h1 class="ob__title">{{ $t('onboarding.readyTitle') }}</h1>
        <p class="ob__muted">
          {{ $t('onboarding.readyBody', { level: $t(`onboarding.level.${result.level}`), score: result.quiz_score }) }}
        </p>
        <div class="ob__plan">
          <p class="ob__plan-title">{{ $t('onboarding.planSummary', { n: result.plan.lesson_count }) }}</p>
          <p class="ob__muted mt-2">{{ result.plan.rationale || $t('onboarding.planDefault') }}</p>
        </div>
        <button type="button" class="ob__primary" @click="router.push({ name: 'studyPlan' })">
          {{ $t('onboarding.startLearning') }}
          <Icon name="arrowRight" class="h-4 w-4" />
        </button>
      </div>

      <!-- Building the plan: a real wait (the AI orders the lessons), shown as one -->
      <BearThinking
        v-else-if="submitting"
        class="my-auto"
        :title="$t('onboarding.buildingTitle')"
        :steps="[$t('onboarding.steps.s1'), $t('onboarding.steps.s2'), $t('onboarding.steps.s3'), $t('onboarding.steps.s4')]"
        :note="$t('onboarding.buildingNote')"
        :step-ms="2200"
      />

      <!-- Questionnaire -->
      <template v-else>
        <header class="ob__top">
          <button type="button" class="ob__icon-btn" :disabled="step === 0" :aria-label="$t('common.back')" @click="back">
            <Icon name="arrowLeft" class="h-4 w-4" />
          </button>
          <div class="ob__bar" role="progressbar" :aria-valuenow="step" aria-valuemin="0" :aria-valuemax="total">
            <span :style="{ transform: `scaleX(${progress / 100})` }" />
          </div>
          <span class="ob__count">{{ Math.min(step + 1, total) }}/{{ total }}</span>
          <button type="button" class="ob__skip-all" @click="skipAll">{{ $t('onboarding.skipAll') }}</button>
        </header>

        <p v-if="step === 0 && !loading" class="ob__intro">
          {{ route.query.welcome === 'google' ? $t('onboarding.introGoogle') : $t('onboarding.intro') }}
        </p>

        <div v-if="loading" class="mt-10 space-y-3">
          <LoadingSkeleton height="h-8" rounded="rounded-xl" />
          <LoadingSkeleton v-for="n in 4" :key="n" height="h-16" rounded="rounded-2xl" />
        </div>

        <div v-else-if="current" class="ob__body">
          <div class="ob__bear" aria-hidden="true"><BearMascot :mood="bearMood" :decorations="false" /></div>

          <Transition name="ob-q" mode="out-in">
            <section :key="current.id" class="ob__q">
              <p class="ob__kicker" :data-kind="current.kind">
                {{ $t(current.kind === 'quiz' ? 'onboarding.knowledgeCheck' : 'onboarding.aboutYou') }}
              </p>
              <h1 class="ob__title">{{ current.prompt }}</h1>

              <div class="ob__choices" role="radiogroup" :aria-label="current.prompt">
                <button
                  v-for="(choice, i) in current.choices"
                  :key="i"
                  type="button"
                  role="radio"
                  class="ob__choice"
                  :aria-checked="answers[current.id] === i"
                  @click="pick(i)"
                >
                  <span class="ob__letter">{{ LETTERS[i] }}</span>
                  <span class="ob__text">{{ choice }}</span>
                  <Icon v-if="answers[current.id] === i" name="check" class="ob__tick" />
                </button>
              </div>
            </section>
          </Transition>
        </div>

        <p v-if="error" class="ob__error">{{ $t('errors.generic') }}</p>

        <footer class="ob__foot">
          <button type="button" class="ob__ghost" :disabled="submitting || loading" @click="skipQuestion">
            {{ isLast ? $t('onboarding.skipAndFinish') : $t('onboarding.skipQuestion') }}
          </button>
          <button
            v-if="current && answers[current.id] !== undefined"
            type="button"
            class="ob__primary ob__primary--small"
            :disabled="submitting"
            @click="forward"
          >
            {{ submitting ? $t('onboarding.building') : isLast ? $t('onboarding.finish') : $t('onboarding.next') }}
            <Icon v-if="!submitting" name="arrowRight" class="h-4 w-4" />
          </button>
        </footer>
      </template>
    </div>
  </div>
</template>

<style scoped>
.ob {
  min-height: 100vh;
  background:
    radial-gradient(60% 40% at 50% 0%, color-mix(in oklab, var(--brand-500) 10%, transparent), transparent 70%),
    var(--bg);
}
.ob__wrap {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 44rem;
  min-height: 100vh;
  margin: 0 auto;
  padding: 1.75rem 1.25rem 2rem;
}
.ob__top {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}
.ob__icon-btn {
  display: grid;
  place-items: center;
  width: 2.5rem;
  height: 2.5rem;
  flex-shrink: 0;
  border-radius: 0.8rem;
  color: var(--text-muted);
  transition: background-color 0.2s ease, color 0.2s ease;
}
.ob__icon-btn:hover:not(:disabled) {
  background: var(--surface-2);
  color: var(--text);
}
.ob__icon-btn:disabled {
  opacity: 0.3;
}
.ob__bar {
  flex: 1;
  height: 0.7rem;
  border-radius: 99px;
  background: var(--surface-2);
  overflow: hidden;
}
.ob__bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--brand-500), var(--brand-400));
  transform-origin: 0 50%;
  transition: transform 0.45s cubic-bezier(0.22, 1, 0.36, 1);
}
.ob__count {
  flex-shrink: 0;
  font-size: 0.8rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
}
.ob__skip-all {
  flex-shrink: 0;
  min-height: 2.5rem;
  padding: 0 0.4rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted);
}
.ob__skip-all:hover {
  color: var(--text);
}
.ob__intro {
  margin-top: 1.4rem;
  padding: 0.8rem 1rem;
  border-radius: 1rem;
  background: color-mix(in oklab, var(--brand-500) 9%, var(--surface));
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text);
}
.ob__body {
  flex: 1;
  display: grid;
  align-items: center;
  gap: 1.5rem;
  margin-top: 1.75rem;
}
@media (min-width: 768px) {
  .ob__body {
    grid-template-columns: 11rem minmax(0, 1fr);
    gap: 2.5rem;
  }
}
.ob__bear {
  width: 7.5rem;
  height: 9rem;
  margin: 0 auto;
}
@media (min-width: 768px) {
  .ob__bear {
    width: 11rem;
    height: 14rem;
  }
}
.ob__bear--result {
  width: 11rem;
  height: 14rem;
}
.ob__kicker {
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--brand-600);
}
.ob__kicker[data-kind='quiz'] {
  color: #b7791f;
}
.ob__title {
  margin-top: 0.55rem;
  font-size: clamp(1.35rem, 1.1rem + 1vw, 1.75rem);
  font-weight: 800;
  line-height: 1.25;
  letter-spacing: -0.02em;
  color: var(--text);
}
.ob__choices {
  margin-top: 1.4rem;
  display: grid;
  gap: 0.65rem;
}
.ob__choice {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  width: 100%;
  min-height: 3.6rem;
  padding: 0.7rem 1rem;
  border-radius: 1.1rem;
  border: 1.5px solid var(--border);
  background: var(--surface);
  text-align: left;
  transition:
    border-color 0.2s ease,
    background-color 0.2s ease,
    transform 0.15s ease;
}
.ob__choice:hover {
  border-color: color-mix(in oklab, var(--brand-500) 45%, var(--border));
}
.ob__choice:active {
  transform: scale(0.99);
}
.ob__choice:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
}
.ob__choice[aria-checked='true'] {
  border-color: var(--brand-500);
  background: color-mix(in oklab, var(--brand-500) 10%, var(--surface));
}
.ob__letter {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;
  border-radius: 0.65rem;
  border: 1.5px solid var(--border);
  font-size: 0.8rem;
  font-weight: 800;
  color: var(--text-muted);
}
.ob__choice[aria-checked='true'] .ob__letter {
  border-color: var(--brand-500);
  background: var(--brand-600);
  color: #fff;
}
.ob__text {
  flex: 1;
  font-size: 0.97rem;
  font-weight: 500;
  line-height: 1.4;
  color: var(--text);
}
.ob__tick {
  width: 1.1rem;
  height: 1.1rem;
  color: var(--brand-600);
}
.ob__error {
  margin-top: 1rem;
  padding: 0.6rem 1rem;
  border-radius: 0.8rem;
  background: rgba(229, 72, 77, 0.1);
  font-size: 0.875rem;
  color: #c4282d;
}
.ob__foot {
  margin-top: 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.ob__ghost {
  min-height: 2.9rem;
  padding: 0 1rem;
  border-radius: 0.9rem;
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--text-muted);
  transition: background-color 0.2s ease, color 0.2s ease;
}
.ob__ghost:hover:not(:disabled) {
  background: var(--surface-2);
  color: var(--text);
}
.ob__primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  min-height: 3.3rem;
  margin-top: 1.5rem;
  padding: 0 1.5rem;
  border-radius: 1rem;
  background: var(--brand-600);
  color: #fff;
  font-weight: 700;
  transition: background-color 0.2s ease, opacity 0.2s ease;
}
.ob__primary:hover:not(:disabled) {
  background: var(--brand-700);
}
.ob__primary:disabled {
  opacity: 0.55;
}
.ob__primary--small {
  width: auto;
  margin-top: 0;
  min-height: 2.9rem;
}
.ob__result {
  margin: auto 0;
  text-align: center;
}
.ob__muted {
  font-size: 0.93rem;
  line-height: 1.55;
  color: var(--text-muted);
}
.ob__plan {
  margin-top: 1.5rem;
  padding: 1.25rem;
  border-radius: 1.25rem;
  border: 1px solid var(--border);
  background: var(--surface);
  text-align: left;
}
.ob__plan-title {
  font-weight: 700;
  color: var(--text);
}
.ob-q-enter-active,
.ob-q-leave-active {
  transition:
    opacity 0.22s ease,
    transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.ob-q-enter-from {
  opacity: 0;
  transform: translateX(18px);
}
.ob-q-leave-to {
  opacity: 0;
  transform: translateX(-18px);
}
@media (prefers-reduced-motion: reduce) {
  .ob-q-enter-active,
  .ob-q-leave-active,
  .ob__bar span {
    transition: none;
  }
}
</style>
