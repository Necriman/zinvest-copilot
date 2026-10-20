<script setup>
/**
 * My Startup intake: nine questions, one at a time, then a market check.
 *
 * The questions are the ones an investor would ask first: what it is, where
 * it launches, whose problem, who pays, how it works, what people use today,
 * how it earns, how far along, who builds it. The answers go to POST
 * /api/startup/onboarding, where Gemini searches Google for the market in
 * that country and city: is there demand, who already serves it, what gap is
 * left, the risks, the next steps, and the pages it found. The result screen
 * shows all of it; `done` then hands control back to the workspace.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { submitStartupOnboarding } from '@/api/startup'
import MarketResearch from './MarketResearch.vue'
import BearMascot from '@/components/mascot/BearMascot.vue'
import BearSticker from '@/components/mascot/BearSticker.vue'
import BearThinking from '@/components/ui/BearThinking.vue'
import CheckBox from '@/components/ui/CheckBox.vue'
import Icon from '@/components/ui/Icon.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'

const { locale, t } = useI18n()
const emit = defineEmits(['done'])

// key → the field sent to the backend; type drives the input; optional ones can be skipped.
const QUESTIONS = [
  { key: 'name', type: 'text' },
  { key: 'location', type: 'text' },
  { key: 'problem', type: 'textarea' },
  { key: 'market', type: 'choice', choices: ['b2c', 'b2b', 'both'] },
  { key: 'description', type: 'textarea', big: true },
  { key: 'alternatives', type: 'textarea', optional: true },
  { key: 'revenue_model', type: 'textarea' },
  { key: 'stage', type: 'choice', choices: ['idea', 'mvp', 'operational'] },
  { key: 'team', type: 'choice', choices: ['solo', 'small', 'medium', 'large'] },
]

const step = ref(0)
const answers = ref({})
const submitting = ref(false)
const error = ref('')
const result = ref(null) // the workspace blocks: { analysis, research?, enabled }

const current = computed(() => QUESTIONS[step.value])
const total = QUESTIONS.length
const isLast = computed(() => step.value === total - 1)
const answered = computed(() => {
  const v = answers.value[current.value.key]
  return current.value.type === 'choice' ? !!v : String(v || '').trim().length > 0
})
const canGo = computed(() => answered.value || current.value.optional)
const research = computed(() => result.value?.research || null)
const place = computed(() => String(answers.value.location || '').trim())

function set(value) {
  answers.value = { ...answers.value, [current.value.key]: value }
}

function pick(value) {
  set(value)
  // A choice needs no extra click: on to the next question.
  if (!isLast.value) setTimeout(() => step.value++, 220)
}

async function next() {
  if (!canGo.value || submitting.value) return
  if (!isLast.value) {
    step.value++
    return
  }
  submitting.value = true
  error.value = ''
  try {
    const res = await submitStartupOnboarding(answers.value, locale.value)
    result.value = res.blocks
  } catch (e) {
    error.value = e?.response?.data?.detail || t('errors.generic')
  } finally {
    submitting.value = false
  }
}

function onEnter(e) {
  if (current.value.type === 'text' && e.key === 'Enter') next()
}
</script>

<template>
  <div class="mx-auto w-full max-w-2xl">
    <!-- The market check -->
    <div v-if="result" class="card p-6 sm:p-8">
      <div class="flex flex-col items-center text-center">
        <BearSticker name="tablet" pop class="h-28 w-28" />
        <p class="mt-3 text-xs font-bold uppercase tracking-wider text-brand-600">{{ $t('startup.research.eyebrow') }}</p>
        <h2 class="mt-1 text-xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {{ answers.name || $t('startup.onboarding.assessmentTitle') }}
        </h2>
      </div>

      <MarketResearch v-if="research" class="mt-5" :research="research" :place="place" />

      <!-- No market check could be had: the plain assessment -->
      <p v-else class="mt-4 whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300">{{ result.analysis }}</p>

      <button
        type="button"
        class="mt-6 w-full rounded-2xl bg-brand-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
        @click="emit('done')"
      >
        {{ $t('startup.onboarding.enterWorkspace') }}
      </button>
    </div>

    <!-- The search takes a while: say what is happening -->
    <div v-else-if="submitting" class="card p-6">
      <BearThinking
        :title="$t('startup.research.loadingTitle')"
        :steps="[
          $t('startup.research.step1', { place: place || '…' }),
          $t('startup.research.step2'),
          $t('startup.research.step3'),
          $t('startup.research.step4'),
        ]"
        :note="$t('startup.research.loadingNote')"
        :step-ms="6000"
      />
    </div>

    <!-- Questionnaire -->
    <div v-else class="card p-6">
      <div class="mx-auto mb-3 h-44 w-36"><BearMascot mood="handshake" interactive :label="$t('mascot.tap')" /></div>
      <div class="mb-6 flex items-center gap-4">
        <button
          type="button"
          class="shrink-0 rounded-xl p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 disabled:opacity-30 dark:hover:bg-surface-2 dark:hover:text-slate-100"
          :disabled="step === 0"
          :title="$t('common.back')"
          @click="step--"
        >
          <Icon name="arrowLeft" class="h-4 w-4" />
        </button>
        <ProgressBar :value="((step + (answered ? 1 : 0)) / total) * 100" class="flex-1" />
        <span class="shrink-0 text-xs font-semibold tabular-nums text-slate-400">{{ step + 1 }}/{{ total }}</span>
      </div>

      <p class="text-xs font-bold uppercase tracking-wider text-brand-600">{{ $t('startup.onboarding.eyebrow') }}</p>
      <h2 class="mt-2 text-lg font-extrabold leading-snug tracking-tight text-slate-900 dark:text-white">
        {{ $t(`startup.intake.${current.key}.q`) }}
      </h2>
      <p class="mt-1.5 text-sm text-slate-500">{{ $t(`startup.intake.${current.key}.hint`) }}</p>

      <div class="mt-5">
        <input
          v-if="current.type === 'text'"
          :value="answers[current.key] || ''"
          :placeholder="$t(`startup.intake.${current.key}.placeholder`)"
          maxlength="200"
          class="zx-input w-full"
          @input="set($event.target.value)"
          @keydown="onEnter"
        />
        <textarea
          v-else-if="current.type === 'textarea'"
          :value="answers[current.key] || ''"
          :rows="current.big ? 6 : 4"
          :placeholder="$t(`startup.intake.${current.key}.placeholder`)"
          maxlength="2000"
          class="zx-input w-full resize-y py-2.5"
          @input="set($event.target.value)"
        />
        <div v-else class="space-y-2.5" role="radiogroup">
          <button
            v-for="choice in current.choices"
            :key="choice"
            type="button"
            role="radio"
            :aria-checked="answers[current.key] === choice"
            class="flex w-full items-center gap-3 rounded-2xl border-2 px-4 py-3 text-left transition"
            :class="
              answers[current.key] === choice
                ? 'border-brand-500 bg-brand-50 dark:bg-brand-500/10'
                : 'border-slate-200 bg-white hover:border-brand-300 dark:border-hairline dark:bg-surface'
            "
            @click="pick(choice)"
          >
            <CheckBox type="radio" :model-value="answers[current.key]" :value="choice" class="pointer-events-none" />
            <span class="text-sm text-slate-700 dark:text-slate-200">{{ $t(`startup.intake.${current.key}.${choice}`) }}</span>
          </button>
        </div>
      </div>

      <p v-if="error" class="mt-4 rounded-xl bg-red-50 px-4 py-2 text-sm text-red-600 dark:bg-red-500/10">{{ error }}</p>

      <div class="mt-6 flex items-center justify-between gap-3">
        <button
          v-if="current.optional && !answered"
          type="button"
          class="text-sm font-semibold text-slate-400 transition hover:text-slate-600"
          @click="next"
        >
          {{ $t('startup.intake.skip') }}
        </button>
        <span v-else />
        <button
          type="button"
          :disabled="!canGo"
          class="rounded-2xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700 disabled:opacity-40"
          @click="next"
        >
          {{ isLast ? $t('startup.research.run') : $t('startup.onboarding.next') }}
        </button>
      </div>
    </div>
  </div>
</template>
