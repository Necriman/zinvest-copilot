<script setup>
/**
 * The bear beside a lesson. It reads the lesson part by part out loud, asks
 * whether everything is clear after each part and waits, stops between parts
 * to ask a question from the unit, reacts to the answers, and answers free
 * questions about the lesson through the AI advisor. Its mouth follows the
 * voice (src/voice/narrator.js).
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import BearMascot from './BearMascot.vue'
import LessonPractice from './LessonPractice.vue'
import LessonCheckpoint from './LessonCheckpoint.vue'
import Icon from '@/components/ui/Icon.vue'
import { askAdvisor } from '@/api/ai'
import http from '@/api/http'
import { payloadToHtml } from '@/utils/payloadToHtml'
import { useNarrator } from '@/voice/narrator'

const props = defineProps({
  lesson: Object,
  completed: Boolean,
  paused: Boolean, // the celebration overlay is open
})
const { t, locale } = useI18n()

const input = ref(''), answer = ref(''), busy = ref(false), error = ref(''), isStub = ref(false)
const segment = ref(0), readDone = ref(false)

// --- the voice: one narrator for the app; this bear talks for 'lesson' and 'feedback' lines
const narrator = useNarrator()
const speaking = computed(() => narrator.state.speaking && ['lesson', 'feedback'].includes(narrator.state.owner))
const listening = ref(false) // the learner pressed "Read aloud": keep reading part after part
const say = (key) => narrator.speak(t(key), { owner: 'lesson', lang: locale.value })

const sections = computed(() => {
  const html = props.lesson?.edited_content || props.lesson?.content_html || payloadToHtml(props.lesson?.canvas_payload)
  if (html) {
    const doc = new DOMParser().parseFromString(html, 'text/html')
    return [...doc.querySelectorAll('h1,h2,h3,p,li')].map((e) => e.textContent.trim()).filter(Boolean)
  }
  const texts = []
  const walk = (v) => {
    if (!v) return
    if (typeof v === 'string') { if (v.length > 25) texts.push(v) }
    else if (Array.isArray(v)) v.forEach(walk)
    else if (typeof v === 'object') for (const [k, item] of Object.entries(v)) if (['text', 'content', 'blocks', 'children', 'title', 'body', 'sections'].includes(k)) walk(item)
  }
  walk(props.lesson?.canvas_payload)
  return texts
})

// Checkpoints: the unit's practice questions are spread evenly through the
// reading, so the bear stops between parts and asks one. At most one question
// per two parts, and never after the final part.
const questions = ref([]), answered = ref(new Set()), quiz = ref(null)
const checkpoints = computed(() => {
  const n = sections.value.length, count = Math.min(questions.value.length, Math.floor(n / 2)), map = new Map()
  for (let i = 0; i < count; i++) map.set(Math.floor(((i + 1) * n) / (count + 1)) - 1, questions.value[i])
  return map
})
let questionsRequest = 0
let doneAtOpen = false // the lesson was already finished when it was opened
async function loadQuestions() {
  const id = ++questionsRequest
  questions.value = []
  if (!props.lesson?.id) return
  try {
    const { data } = await http.get(`/learning/lessons/${props.lesson.id}/practice`)
    if (id === questionsRequest) questions.value = data.questions || []
  } catch {
    /* checkpoints are optional; the reading still works */
  }
}

// --- the bear's mood and what it says
const reaction = ref(null) // { mood, say } for a couple of seconds after an event
let reactionTimer
function flash(mood, say, ms = 2600) {
  reaction.value = { mood, say }
  clearTimeout(reactionTimer)
  reactionTimer = setTimeout(() => (reaction.value = null), ms)
}
const greeting = ref(true)
let greetingTimer
onMounted(() => { greetingTimer = setTimeout(() => (greeting.value = false), 2200) })

const mood = computed(() => {
  if (props.paused) return 'idle'
  if (reaction.value) return reaction.value.mood
  if (speaking.value) return 'talk'
  if (busy.value) return 'think'
  if (quiz.value) return 'listen'
  if (greeting.value) return 'eager' // rubs his paws: let's begin
  return 'idle'
})
const bubble = computed(() => {
  if (reaction.value?.say) return reaction.value.say
  if (busy.value) return t('mascot.thinking')
  if (quiz.value) return t('checkpoint.label')
  if (readDone.value) return t('checkpoint.clear')
  if (props.completed) return t('bear.congratulations')
  return t('bear.lessonIntro')
})

function onAnswered(correct) {
  flash(correct ? 'happy' : 'confused', correct ? t('mascot.praise1') : t('mascot.encourage4'))
}

// --- reading aloud, part by part. The part is read in its own language (the
// lessons are in English); the bear's own lines follow the interface language.
function silence() {
  if (speaking.value) narrator.stop()
}
function stop() {
  listening.value = false
  silence()
}
async function read() {
  listening.value = true
  readDone.value = false
  error.value = ''
  const text = sections.value[segment.value]
  if (!text) return
  const upcoming = sections.value[segment.value + 1]
  if (upcoming) narrator.prepare(upcoming)
  const at = segment.value
  const result = await narrator.speak(text, { owner: 'lesson' })
  if (at !== segment.value) return
  if (result === 'ended') {
    readDone.value = true
    say('voice.clear')
  } else if (result === 'failed') {
    listening.value = false
    error.value = t('bear.voiceUnavailable')
  } else if (result === 'muted') {
    listening.value = false
  }
}
function next() {
  silence()
  readDone.value = false
  const q = checkpoints.value.get(segment.value)
  if (q && !answered.value.has(q.id)) {
    quiz.value = q
    if (listening.value) say('checkpoint.label')
    return
  }
  if (segment.value < sections.value.length - 1) {
    segment.value++
    if (listening.value) read()
  }
}
function toggleVoice() {
  narrator.setEnabled(!narrator.enabled.value)
  if (!narrator.enabled.value) listening.value = false
}
function finishCheckpoint() {
  answered.value = new Set([...answered.value, quiz.value.id])
  quiz.value = null
  next()
}

// --- free questions to the AI
let requestId = 0
async function ask() {
  if (!input.value.trim() || busy.value) return
  const id = ++requestId
  busy.value = true
  error.value = ''
  try {
    const res = await askAdvisor(input.value, { lesson_id: props.lesson?.id, lesson_title: props.lesson?.title, lesson_text: sections.value.join('\n').slice(0, 24000), current_section: sections.value[segment.value], language: locale.value })
    if (id !== requestId) return
    answer.value = res.answer
    isStub.value = res.is_stub
    input.value = ''
    if (!res.is_stub) flash('talk', '', 1800)
  } catch (e) {
    if (id === requestId) error.value = e?.response?.data?.detail || e.message
  } finally {
    if (id === requestId) busy.value = false
  }
}

watch(() => props.lesson?.id, () => {
  requestId++
  doneAtOpen = !!props.completed
  stop()
  segment.value = 0
  answer.value = ''
  error.value = ''
  busy.value = false
  readDone.value = false
  quiz.value = null
  answered.value = new Set()
  loadQuestions()
}, { immediate: true })
// Finished during this visit (the celebration overlay says the line out loud).
watch(() => props.completed, (done, before) => {
  if (!done || before !== false || doneAtOpen) return
  flash('celebrate', t('bear.congratulations'), 3200)
  listening.value = false
})

onBeforeUnmount(() => {
  requestId++
  questionsRequest++
  clearTimeout(reactionTimer)
  clearTimeout(greetingTimer)
  stop()
})
</script>

<template>
  <aside class="flex h-full min-h-0 flex-col overflow-y-auto bg-slate-50 p-4 sm:p-5 dark:bg-surface-2">
    <div class="flex items-end gap-2">
      <div class="h-40 w-32 shrink-0 sm:h-44 sm:w-36">
        <BearMascot :mood="mood" interactive :label="$t('mascot.tap')" :voice="speaking ? narrator.level : null" />
      </div>
      <p class="zl-bubble relative mb-10 rounded-2xl border border-hairline bg-white px-4 py-3 text-sm font-medium leading-snug text-slate-700 shadow-sm dark:bg-surface dark:text-slate-200" aria-live="polite">
        {{ bubble }}
      </p>
    </div>

    <LessonCheckpoint v-if="quiz" class="mt-4" :lesson-id="lesson.id" :question="quiz" @answered="onAnswered" @continue="finishCheckpoint" />
    <div v-else-if="sections.length" class="mt-4 rounded-2xl border border-hairline bg-white p-4 dark:bg-surface">
      <div class="flex items-center justify-between gap-2">
        <p class="text-xs font-semibold text-brand-600">{{ $t('bear.section') }} {{ segment + 1 }} / {{ sections.length }}</p>
        <button
          type="button"
          class="-my-2 -mr-2 inline-flex h-10 w-10 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 dark:hover:bg-surface-2"
          :aria-label="$t(narrator.enabled.value ? 'voice.mute' : 'voice.unmute')"
          :title="$t(narrator.enabled.value ? 'voice.mute' : 'voice.unmute')"
          :aria-pressed="!narrator.enabled.value"
          @click="toggleVoice"
        >
          <Icon :name="narrator.enabled.value ? 'volume' : 'volumeOff'" class="h-5 w-5" />
        </button>
      </div>
      <p class="mt-2 max-h-40 overflow-auto text-sm leading-relaxed">{{ sections[segment] }}</p>
      <div class="mt-3 flex flex-wrap gap-2">
        <button v-if="narrator.enabled.value" type="button" class="inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand-600 px-4 text-sm font-semibold text-white" @click="speaking || listening ? stop() : read()">
          <Icon :name="speaking || listening ? 'pause' : 'play'" class="h-4 w-4" /> {{ $t(speaking || listening ? 'bear.pause' : 'bear.listen') }}
        </button>
        <button type="button" :disabled="segment >= sections.length - 1" class="min-h-11 rounded-xl border border-hairline px-4 text-sm font-semibold disabled:opacity-40" @click="next">{{ $t('bear.understood') }}</button>
      </div>
      <p v-if="checkpoints.size" class="mt-3 text-xs text-slate-500">{{ $t('checkpoint.progress', { done: answered.size, total: checkpoints.size }) }}</p>
    </div>

    <div v-if="answer" class="mt-4 rounded-2xl bg-white p-4 text-sm shadow-sm dark:bg-surface">
      <p v-if="isStub" class="mb-2 font-semibold text-amber-700">{{ $t('business.aiUnavailable') }}</p>
      <p class="whitespace-pre-wrap">{{ answer }}</p>
    </div>
    <LessonPractice v-if="lesson?.id" :lesson-id="lesson.id" @answered="onAnswered" />
    <p v-if="error" role="alert" class="mt-3 text-sm text-red-600">{{ error }}</p>
    <form class="mt-4 flex gap-2" @submit.prevent="ask">
      <label class="min-w-0 flex-1"><span class="sr-only">{{ $t('bear.question') }}</span><input v-model="input" :placeholder="$t('bear.question')" class="zx-input w-full" /></label>
      <button :disabled="busy || !input.trim()" class="min-h-11 rounded-xl bg-brand-600 px-4 text-white disabled:opacity-40">{{ busy ? '…' : $t('bear.ask') }}</button>
    </form>
  </aside>
</template>

<style scoped>
/* A speech bubble whose tail points at the bear on its left. */
.zl-bubble::before {
  content: '';
  position: absolute;
  left: -7px;
  bottom: 14px;
  width: 12px;
  height: 12px;
  background: inherit;
  border-left: 1px solid var(--color-hairline, rgba(148, 163, 184, 0.35));
  border-bottom: 1px solid var(--color-hairline, rgba(148, 163, 184, 0.35));
  transform: rotate(45deg);
}
</style>
