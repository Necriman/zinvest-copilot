<script setup>
/**
 * Zinvest AI — a tutor that knows where the learner is, not a chat box.
 *
 * It opens on what the learner is studying and the last question they got
 * wrong (read from their own tests and Daily, no model call), with the four
 * things a tutor is for. Coming from a lesson's "Ask Zinvest about this", the
 * lesson is the context. Every answer is still a question the learner sent:
 * the actions write it out in their name, visibly, and attach the lesson or
 * the mistake so the answer is about them.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AiActions from '@/components/ai/AiActions.vue'
import AiStart from '@/components/ai/AiStart.vue'
import AiText from '@/components/ai/AiText.vue'
import { buildAsk } from '@/components/ai/actions'
import Icon from '@/components/ui/Icon.vue'
import AiAvatar from '@/components/ai/AiAvatar.vue'
import { askAdvisor, getAIContext } from '@/api/ai'
import { useAskAI } from '@/composables/useAskAI'
import { osScrollElement } from '@/plugins/overlayScrollbars'

const { t } = useI18n()
const route = useRoute()

const prompt = ref('')
const loading = ref(false)
const messages = ref([])
const quota = ref(null)
const thread = ref(null)
const input = ref(null)

const ctx = ref(null)
const ctxLoading = ref(true)

// Gemini usually answers in seconds, but a long explanation — or a retry after
// a timeout — can take well over a minute. Past this point the thinking
// bubble says so, so a slow answer does not read as a frozen screen.
const SLOW_AFTER_MS = 12000
const slow = ref(false)
let slowTimer = null

const quotaLeft = computed(() => (quota.value?.limit ? Math.max(0, Math.round((quota.value.remaining / quota.value.limit) * 100)) : null))

// What the learner is on: sent with every free-typed question too, so "what
// does this mean?" is answered about the right lesson.
const baseContext = computed(() => {
  const learning = ctx.value?.learning
  if (!learning) return {}
  // The id lets the server read that lesson's text to the tutor.
  return { lesson: learning.title, unit: learning.unit_title, ...(learning.kind === 'lesson' ? { lesson_id: learning.id } : {}) }
})

// "Continue in Zinvest AI" from the select-to-ask card: the question and its
// answer arrive already asked, so the conversation carries on from them.
const askAI = useAskAI()
function adoptHandoff() {
  const carried = askAI.takeHandoff()
  if (!carried) return
  messages.value.push({ role: 'user', text: carried.question }, { role: 'ai', text: carried.answer })
  scrollDown()
}
window.addEventListener('zinvest-ai-handoff', adoptHandoff)
onBeforeUnmount(() => window.removeEventListener('zinvest-ai-handoff', adoptHandoff))

onMounted(async () => {
  adoptHandoff()
  try {
    ctx.value = await getAIContext(route.query.lesson)
  } catch {
    // The screen works without it: the actions fall back to general questions.
    ctx.value = null
  } finally {
    ctxLoading.value = false
  }
})

async function scrollDown() {
  await nextTick()
  // With v-os the host is no longer the scroller — scroll the OS viewport instead.
  const el = osScrollElement(thread.value)
  el?.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
}

async function send(text, context = null) {
  const q = (text ?? prompt.value).trim()
  if (!q || loading.value) return
  messages.value.push({ role: 'user', text: q })
  prompt.value = ''
  loading.value = true
  slow.value = false
  clearTimeout(slowTimer)
  slowTimer = setTimeout(() => (slow.value = true), SLOW_AFTER_MS)
  scrollDown()
  try {
    const res = await askAdvisor(q, { ...baseContext.value, ...(context || {}) })
    messages.value.push({ role: 'ai', text: res.is_stub ? t('business.aiUnavailable') : res.answer, unavailable: res.is_stub })
    quota.value = res.quota
  } catch (e) {
    messages.value.push({ role: 'ai', text: e.response?.data?.detail || t('errors.generic'), error: true })
  } finally {
    clearTimeout(slowTimer)
    slow.value = false
    loading.value = false
    scrollDown()
  }
}

onBeforeUnmount(() => clearTimeout(slowTimer))

async function onAction(key) {
  const ask = buildAsk(key, ctx.value, t)
  if (!ask) return
  if (ask.draft) {
    // Needs the learner's own words: start the sentence and hand them the box.
    prompt.value = ask.draft
    await nextTick()
    input.value?.focus()
    return
  }
  send(ask.text, ask.context)
}
</script>

<template>
  <div class="mx-auto flex h-[calc(100vh-8rem)] max-w-3xl flex-col">
    <div class="mb-4 flex items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <AiAvatar class="h-11 w-11" />
        <div>
          <h1 class="text-xl font-extrabold tracking-tight text-slate-900 dark:text-white">{{ $t('ai.title') }}</h1>
          <p class="text-sm text-slate-500">{{ $t('ai.subtitle') }}</p>
        </div>
      </div>
      <span v-if="quotaLeft !== null" class="shrink-0 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-surface-2 dark:text-slate-300">
        {{ $t('aiChat.quota', { p: quotaLeft }) }}
      </span>
    </div>

    <div ref="thread" v-os class="card flex-1 space-y-4 overflow-y-auto p-5">
      <AiStart v-if="!messages.length" :ctx="ctx" :loading="ctxLoading" :busy="loading" @pick="onAction" />

      <div v-for="(m, i) in messages" :key="i" class="flex items-end gap-2" :class="m.role === 'user' ? 'justify-end' : 'justify-start'">
        <AiAvatar v-if="m.role === 'ai'" class="mb-0.5 h-8 w-8" :class="m.error || m.unavailable ? 'opacity-60 grayscale' : ''" />
        <div
          class="max-w-[80%] rounded-2xl px-4 py-2.5 text-sm"
          :class="m.role === 'user'
            ? 'bg-brand-600 text-white'
            : m.error || m.unavailable
              ? 'bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-200'
              : 'bg-slate-100 text-slate-800 dark:bg-surface-2 dark:text-ink'"
        >
          <!-- Answers are formatted (headings, lists, the formula) without
               ever becoming HTML; the learner's own words stay as typed. -->
          <AiText v-if="m.role === 'ai' && !m.error && !m.unavailable" :text="m.text" />
          <p v-else class="whitespace-pre-wrap">{{ m.text }}</p>
        </div>
      </div>
      <div v-if="loading" class="flex items-end gap-2" role="status">
        <AiAvatar thinking class="mb-0.5 h-8 w-8" />
        <p class="rounded-2xl bg-slate-100 px-4 py-2.5 text-sm text-slate-500 dark:bg-surface-2">{{ slow ? $t('aiHome.slow') : $t('ai.thinking') }}</p>
      </div>
    </div>

    <!-- Mid-conversation, the same four actions stay one tap away. -->
    <AiActions v-if="messages.length" class="mt-3" compact :ctx="ctx" :disabled="loading" @pick="onAction" />

    <form class="mt-3 flex items-center gap-2" @submit.prevent="send()">
      <input
        ref="input"
        v-model="prompt"
        :placeholder="$t('aiHome.placeholder')"
        :aria-label="$t('aiHome.placeholder')"
        class="flex-1 rounded-full border border-slate-200 bg-white px-5 py-3 text-sm focus:border-brand-500 focus:outline-none dark:border-hairline dark:bg-surface"
      />
      <button
        type="submit"
        :disabled="loading || !prompt.trim()"
        :aria-label="$t('ai.ask')"
        class="flex h-11 w-11 items-center justify-center rounded-full bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50"
      >
        <Icon name="send" class="h-5 w-5" />
      </button>
    </form>
  </div>
</template>
