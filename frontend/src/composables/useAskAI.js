// Select anything, ask Zinvest about it.
//
// One shared state for the whole app, because the question can start in two
// places — the floating button over an ordinary selection, and the lesson
// editor's own selection menu — and must land in one answer card. Pages that
// know what the learner is reading (a lesson) register it as the scope, so the
// answer is about this lesson and not about the word in general.
import { reactive } from 'vue'

import { askAdvisor } from '@/api/ai'
import i18n from '@/i18n'

const t = (key, params) => i18n.global.t(key, params)

// Longer than this and it is a passage, not a question; the model gets the
// start of it and the card says so by quoting only that much.
const MAX_CHARS = 400
// Up to this many words reads as a term ("what does X mean?"), beyond it as a
// passage to explain.
const TERM_WORDS = 4

const state = reactive({
  open: false,
  text: '',
  question: '',
  rect: null, // where the selection was, in viewport coordinates
  loading: false,
  answer: '',
  error: false,
  scope: {},
})

let seq = 0
// A finished exchange waiting to be carried into the full chat, so opening it
// there shows the same answer instead of asking — and paying — twice.
let handoff = null

function clean(text) {
  return String(text || '').replace(/\s+/g, ' ').trim().slice(0, MAX_CHARS)
}

async function ask(text, rect = null) {
  const selected = clean(text)
  if (selected.length < 2) return
  const words = selected.split(' ').length
  return send(t(words <= TERM_WORDS ? 'askAI.whatIs' : 'askAI.explain', { text: selected }), selected, rect)
}

// A question a page has already worded (the trainer's "why is this the
// answer?"), quoting `quote` in the card the way a selection would be.
function askAbout(question, quote, rect = null) {
  return send(question, clean(quote), rect)
}

async function send(question, quote, rect) {
  const mine = ++seq
  Object.assign(state, {
    open: true,
    text: quote,
    question,
    rect,
    loading: true,
    answer: '',
    error: false,
  })
  try {
    const res = await askAdvisor(state.question, { mode: 'selection', ...state.scope })
    if (mine !== seq) return // a newer question replaced this one
    state.answer = res.is_stub ? t('business.aiUnavailable') : res.answer
    state.error = !!res.is_stub
  } catch (e) {
    if (mine !== seq) return
    state.answer = e?.response?.data?.detail || t('errors.generic')
    state.error = true
  } finally {
    if (mine === seq) state.loading = false
  }
}

function close() {
  seq++ // an answer still on its way is no longer wanted
  state.open = false
  state.loading = false
}

// Called by pages that know what is being read.
function setScope(scope) {
  state.scope = { ...(scope || {}) }
}
function clearScope() {
  state.scope = {}
}

// "Continue in Zinvest AI": park the exchange for the chat to pick up.
function handOff() {
  if (!state.answer || state.error) return
  handoff = { question: state.question, answer: state.answer }
  close()
}
function takeHandoff() {
  const out = handoff
  handoff = null
  return out
}

export function useAskAI() {
  return { state, ask, askAbout, close, setScope, clearScope, handOff, takeHandoff }
}
