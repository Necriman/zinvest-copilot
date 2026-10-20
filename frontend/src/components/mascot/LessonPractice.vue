<script setup>
/**
 * Optional practice for the whole unit, under the lesson. Never awards coins or
 * unlocks anything; the bear just reacts to each answer.
 */
import { computed, ref, watch } from 'vue'

import MascotFeedback from './MascotFeedback.vue'
import http from '@/api/http'

const props = defineProps({ lessonId: String })
const emit = defineEmits(['answered'])

const questions = ref([]), index = ref(0), selection = ref(null), feedback = ref(null), busy = ref(false), error = ref(''), opened = ref(false)
const question = computed(() => questions.value[index.value])
let generation = 0

watch(() => props.lessonId, () => {
  generation++
  questions.value = []
  index.value = 0
  selection.value = null
  feedback.value = null
  opened.value = false
  busy.value = false
  error.value = ''
})

async function load() {
  if (!props.lessonId || busy.value) return
  busy.value = true
  error.value = ''
  const current = ++generation
  try {
    const { data } = await http.get(`/learning/lessons/${props.lessonId}/practice`)
    if (current !== generation) return
    questions.value = data.questions
    opened.value = true
  } catch (e) {
    if (current === generation) error.value = e?.response?.data?.detail || e.message
  } finally {
    if (current === generation) busy.value = false
  }
}

async function check() {
  if (selection.value === null || busy.value) return
  busy.value = true
  error.value = ''
  const current = generation
  try {
    const { data } = await http.post(`/learning/lessons/${props.lessonId}/practice`, { question_id: question.value.id, choice_index: selection.value })
    if (current !== generation) return
    feedback.value = data
    emit('answered', data.correct)
  } catch (e) {
    if (current === generation) error.value = e?.response?.data?.detail || e.message
  } finally {
    if (current === generation) busy.value = false
  }
}

function next() {
  index.value = (index.value + 1) % questions.value.length
  selection.value = null
  feedback.value = null
}
</script>

<template>
  <section class="mt-4 rounded-2xl border border-hairline bg-white p-4 text-sm dark:bg-surface">
    <button v-if="!opened" type="button" :disabled="busy" class="min-h-11 w-full font-semibold text-brand-600" @click="load">{{ $t('practice.title') }}</button>
    <template v-else-if="question">
      <p class="text-xs font-semibold text-brand-600">{{ $t('practice.title') }} · {{ index + 1 }}/{{ questions.length }}</p>
      <p class="mt-3 font-semibold">{{ question.prompt }}</p>
      <fieldset class="mt-3 space-y-2">
        <legend class="sr-only">{{ question.prompt }}</legend>
        <label
          v-for="(choice, i) in question.choices"
          :key="i"
          class="flex min-h-11 cursor-pointer items-center gap-3 rounded-xl border p-3 transition"
          :class="feedback && i === feedback.answer_index ? 'border-emerald-400 bg-emerald-50/60 dark:bg-emerald-500/10' : feedback && i === selection ? 'border-amber-400' : selection === i ? 'border-brand-400 bg-brand-50/50 dark:bg-brand-500/10' : 'border-hairline'"
        >
          <input v-model="selection" type="radio" :value="i" :disabled="!!feedback || busy" :name="`practice-${lessonId}-${question.id}`" />{{ choice }}
        </label>
      </fieldset>
      <MascotFeedback
        v-if="feedback"
        class="mt-3"
        :correct="feedback.correct"
        :answer="feedback.correct ? '' : question.choices[feedback.answer_index]"
        :explanation="feedback.explanation"
        :seed="question.id + index"
      />
      <button v-if="!feedback" type="button" :disabled="selection === null || busy" class="mt-3 min-h-11 rounded-xl bg-brand-600 px-4 font-semibold text-white disabled:opacity-40" @click="check">{{ $t('practice.check') }}</button>
      <button v-else type="button" class="mt-3 min-h-11 px-3 font-semibold text-brand-600" @click="next">{{ $t('practice.next') }}</button>
    </template>
    <p v-else class="text-slate-500">{{ $t('practice.empty') }}</p>
    <p v-if="error" role="alert" class="mt-3 text-red-600">{{ error }}</p>
  </section>
</template>
