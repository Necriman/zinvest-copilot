<script setup>
/**
 * One practice question the bear asks in the middle of the reading, between
 * parts. Grading happens on the server (the answer key never reaches the
 * browser); the reader continues after checking, right or wrong, or skips.
 */
import { ref, watch } from 'vue'

import MascotFeedback from './MascotFeedback.vue'
import http from '@/api/http'

const props = defineProps({ lessonId: String, question: Object })
const emit = defineEmits(['answered', 'continue'])

const selection = ref(null), feedback = ref(null), busy = ref(false), error = ref('')
watch(() => props.question?.id, () => { selection.value = null; feedback.value = null; error.value = ''; busy.value = false })

async function check() {
  if (selection.value === null || busy.value) return
  const asked = props.question.id
  busy.value = true
  error.value = ''
  try {
    const { data } = await http.post(`/learning/lessons/${props.lessonId}/practice`, { question_id: asked, choice_index: selection.value })
    if (asked !== props.question?.id) return
    feedback.value = data
    emit('answered', data.correct)
  } catch (e) {
    error.value = e?.response?.data?.detail || e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="rounded-2xl border-2 border-brand-200 bg-white p-4 text-sm dark:border-brand-500/30 dark:bg-surface">
    <p class="text-xs font-semibold text-brand-600">{{ $t('checkpoint.label') }}</p>
    <p class="mt-2 font-semibold">{{ question.prompt }}</p>
    <fieldset class="mt-3 space-y-2">
      <legend class="sr-only">{{ question.prompt }}</legend>
      <label
        v-for="(choice, i) in question.choices"
        :key="i"
        class="flex min-h-11 cursor-pointer items-center gap-3 rounded-xl border p-3 transition"
        :class="feedback && i === feedback.answer_index ? 'border-emerald-400 bg-emerald-50/60 dark:bg-emerald-500/10' : feedback && i === selection ? 'border-amber-400' : selection === i ? 'border-brand-400 bg-brand-50/50 dark:bg-brand-500/10' : 'border-hairline'"
      >
        <input v-model="selection" type="radio" :value="i" :disabled="!!feedback || busy" :name="`checkpoint-${lessonId}-${question.id}`" />{{ choice }}
      </label>
    </fieldset>
    <MascotFeedback
      v-if="feedback"
      class="mt-3"
      :correct="feedback.correct"
      :answer="feedback.correct ? '' : question.choices[feedback.answer_index]"
      :explanation="feedback.explanation"
      :seed="question.id"
    />
    <div class="mt-3 flex flex-wrap gap-2">
      <button v-if="!feedback" type="button" :disabled="selection === null || busy" class="min-h-11 rounded-xl bg-brand-600 px-4 font-semibold text-white disabled:opacity-40" @click="check">{{ $t('practice.check') }}</button>
      <button v-else type="button" class="min-h-11 rounded-xl bg-brand-600 px-4 font-semibold text-white" @click="emit('continue')">{{ $t('checkpoint.continue') }}</button>
      <button v-if="!feedback" type="button" class="min-h-11 px-3 text-slate-500" @click="emit('continue')">{{ $t('checkpoint.skip') }}</button>
    </div>
    <p v-if="error" role="alert" class="mt-2 text-red-600">{{ error }}</p>
  </div>
</template>
