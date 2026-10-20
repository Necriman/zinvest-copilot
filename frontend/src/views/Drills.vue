<script setup>
import { computed, ref } from 'vue'

import BearMascot from '@/components/mascot/BearMascot.vue'
import InlineLoader from '@/components/ui/InlineLoader.vue'
import MascotFeedback from '@/components/mascot/MascotFeedback.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import http from '@/api/http'

const { data, loading, error } = useAsyncData(() => http.get('/learning/challenges').then((r) => r.data))
const answers = ref({}), feedback = ref({}), busy = ref(''), failure = ref('')

// The bear reacts to the latest answer for a few seconds, then waits.
const reaction = ref('')
let timer
const mood = computed(() => reaction.value || 'think')

async function check(c) {
  if (busy.value || answers.value[c.id] === undefined) return
  busy.value = c.id
  failure.value = ''
  try {
    const result = (await http.post('/learning/challenges', { id: c.id, choice_index: answers.value[c.id] })).data
    feedback.value = { ...feedback.value, [c.id]: result }
    reaction.value = result.correct ? 'happy' : 'confused'
    clearTimeout(timer)
    timer = setTimeout(() => (reaction.value = ''), 2800)
  } catch (e) {
    failure.value = e?.response?.data?.detail || e.message
  } finally {
    busy.value = ''
  }
}
</script>

<template>
  <div class="@container">
    <div class="mb-6 flex items-center justify-between gap-4">
      <div>
        <h1 class="text-3xl font-extrabold">{{ $t('challenge.title') }}</h1>
        <p class="mt-3 text-slate-500">{{ $t('challenge.intro') }}</p>
      </div>
      <div class="hidden h-40 w-32 shrink-0 sm:block"><BearMascot :mood="mood" interactive :label="$t('mascot.tap')" /></div>
    </div>
    <InlineLoader v-if="loading" />
    <p v-if="error || failure" role="alert" class="mb-4 text-red-600">{{ error || failure }}</p>
    <div class="grid grid-cols-1 gap-5 @3xl:grid-cols-2">
      <article v-for="c in data?.challenges || []" :key="c.id" class="card min-w-0 p-5">
        <p class="text-xs font-bold uppercase text-brand-600">{{ c.unit_title }}</p>
        <h2 class="mt-3 font-semibold leading-relaxed">{{ c.prompt }}</h2>
        <fieldset class="mt-4 space-y-2">
          <legend class="sr-only">{{ c.prompt }}</legend>
          <label
            v-for="(choice, i) in c.choices"
            :key="i"
            class="flex min-h-11 cursor-pointer items-center gap-3 rounded-xl border p-3 transition"
            :class="feedback[c.id] && i === feedback[c.id].answer_index ? 'border-emerald-400 bg-emerald-50/60 dark:bg-emerald-500/10' : feedback[c.id] && i === answers[c.id] ? 'border-amber-400' : answers[c.id] === i ? 'border-brand-400 bg-brand-50/50 dark:bg-brand-500/10' : 'border-hairline'"
          >
            <input v-model="answers[c.id]" type="radio" :value="i" :name="c.id" :disabled="!!feedback[c.id]" />{{ choice }}
          </label>
        </fieldset>
        <button v-if="!feedback[c.id]" type="button" :disabled="!!busy || answers[c.id] === undefined" class="mt-4 min-h-11 rounded-xl bg-brand-600 px-5 font-semibold text-white disabled:opacity-50" @click="check(c)">{{ $t('practice.check') }}</button>
        <MascotFeedback
          v-else
          class="mt-4"
          :correct="feedback[c.id].correct"
          :answer="feedback[c.id].correct ? '' : c.choices[feedback[c.id].answer_index]"
          :explanation="feedback[c.id].explanation"
          :seed="c.id"
        />
      </article>
    </div>
    <p v-if="!loading && !data?.challenges?.length && !error" class="card p-6">{{ $t('practice.empty') }}</p>
  </div>
</template>
