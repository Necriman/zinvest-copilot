/**
 * The bear's voice. One narrator for the whole app, so two bears never talk
 * over each other.
 *
 *   const voice = useNarrator()
 *   await voice.speak(text)        // 'ended' | 'stopped' | 'failed' | 'muted'
 *   voice.level()                  // 0..1 loudness right now, drives the mouth
 *
 * Where the sound comes from, best first:
 *   1. a recorded clip from the voice pack (public/voice/manifest.json), found
 *      by the exact text, so a line edited in i18n never plays stale audio;
 *   2. the server voice (POST /api/ai/tts), when the backend has a TTS key;
 *   3. the browser's own speech engine.
 * The mouth follows the real loudness of 1 and 2 (decoded once per clip) and a
 * simple talking rhythm for 3.
 */
import { computed, reactive, ref } from 'vue'

import http from '@/api/http'
import { detectLang, normalizeSpeech, speechKey } from './text'

const ENABLED_KEY = 'zinvest.voice.enabled'
const RATE_KEY = 'zinvest.voice.rate'
export const RATES = [0.85, 1, 1.15]

function readStorage(key) {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}
function writeStorage(key, value) {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* private mode: the choice lasts for this visit */
  }
}

const enabled = ref(readStorage(ENABLED_KEY) !== 'off')
const rate = ref(RATES.includes(Number(readStorage(RATE_KEY))) ? Number(readStorage(RATE_KEY)) : 1)
const state = reactive({ speaking: false, owner: null, source: '' })

// --- voice pack
let manifest = null
let manifestRequest = null
function loadManifest() {
  if (!manifestRequest) {
    manifestRequest = fetch('/voice/manifest.json', { cache: 'no-cache' })
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null)
      .then((m) => (manifest = m && m.clips ? m : { clips: {} }))
  }
  return manifestRequest
}

// --- audio bytes, cached by text (a handful of recent clips)
const CACHE_SIZE = 16
const clips = new Map() // key -> Promise<{ url, envelope: Promise<Float32Array|null> } | null>

// Asked once per visit: does the server have a voice (a TTS key)?
let serverVoice = null
function serverHasVoice() {
  if (!serverVoice) serverVoice = http.get('/ai/tts').then((r) => !!r.data?.available).catch(() => false)
  return serverVoice
}

function remember(key, promise) {
  clips.set(key, promise)
  while (clips.size > CACHE_SIZE) {
    const [oldKey, old] = clips.entries().next().value
    clips.delete(oldKey)
    old.then((c) => c && URL.revokeObjectURL(c.url)).catch(() => {})
  }
  return promise
}

async function fetchBytes(text, lang) {
  await loadManifest()
  const key = speechKey(text)
  const entry = manifest.clips[key]
  if (entry) {
    const res = await fetch(entry.src)
    if (res.ok) return { bytes: await res.arrayBuffer(), type: res.headers.get('content-type') || 'audio/mpeg', source: 'pack' }
  }
  if (!(await serverHasVoice())) return null
  try {
    const res = await http.post('/ai/tts', { text: normalizeSpeech(text), lang }, { responseType: 'arraybuffer' })
    return { bytes: res.data, type: res.headers['content-type'] || 'audio/mpeg', source: 'server' }
  } catch (e) {
    if (e?.response?.status === 503) serverVoice = Promise.resolve(false)
    return null // too long, over the daily limit, or the service failed: the browser voice takes over
  }
}

/** Loudness per 20 ms, 0..1, so the mouth opens with the actual syllables. */
async function envelopeOf(bytes) {
  const Offline = window.OfflineAudioContext || window.webkitOfflineAudioContext
  if (!Offline) return null
  try {
    const decoder = new Offline(1, 1, 22050)
    const audio = await decoder.decodeAudioData(bytes.slice(0))
    const data = audio.getChannelData(0)
    const step = Math.max(1, Math.round(audio.sampleRate * 0.02))
    const out = new Float32Array(Math.ceil(data.length / step))
    let peak = 1e-4
    for (let f = 0; f < out.length; f++) {
      let sum = 0
      const end = Math.min(data.length, (f + 1) * step)
      for (let i = f * step; i < end; i++) sum += data[i] * data[i]
      out[f] = Math.sqrt(sum / Math.max(1, end - f * step))
      if (out[f] > peak) peak = out[f]
    }
    for (let f = 0; f < out.length; f++) out[f] = Math.min(1, Math.pow(out[f] / (peak * 0.7), 0.8))
    return out
  } catch {
    return null
  }
}

function prepareClip(text, lang) {
  const key = speechKey(text)
  if (clips.has(key)) return clips.get(key)
  const promise = fetchBytes(text, lang).then((got) => {
    if (!got) return null
    const url = URL.createObjectURL(new Blob([got.bytes], { type: got.type }))
    return { url, source: got.source, envelope: envelopeOf(got.bytes) }
  })
  promise.catch(() => clips.delete(key))
  return remember(key, promise)
}

// --- playback
let audio = null
let envelope = null
let finish = null // resolves the current speak() promise
let token = 0

function element() {
  if (!audio && typeof Audio !== 'undefined') {
    audio = new Audio()
    audio.preload = 'auto'
  }
  return audio
}

function settle(result) {
  const done = finish
  finish = null
  state.speaking = false
  state.owner = null
  state.source = ''
  envelope = null
  done?.(result)
}

function stop() {
  token++
  if (audio) {
    audio.onended = audio.onerror = null
    audio.pause()
  }
  if (typeof window !== 'undefined' && window.speechSynthesis) window.speechSynthesis.cancel()
  settle('stopped')
}

function playClip(clip, my) {
  return new Promise((resolve) => {
    const el = element()
    if (!el) return resolve('failed')
    finish = resolve
    el.onended = () => my === token && settle('ended')
    el.onerror = () => my === token && settle('failed')
    el.src = clip.url
    el.playbackRate = rate.value
    envelope = null
    clip.envelope.then((env) => { if (my === token) envelope = env })
    state.speaking = true
    state.source = clip.source
    el.play().catch(() => my === token && settle('failed'))
  })
}

// Chrome fills the voice list asynchronously; ask early so it is ready on first use.
if (typeof window !== 'undefined' && window.speechSynthesis?.getVoices) {
  window.speechSynthesis.getVoices()
  window.speechSynthesis.addEventListener?.('voiceschanged', () => window.speechSynthesis.getVoices())
}

function browserVoice(lang) {
  const synth = window.speechSynthesis
  const voices = synth?.getVoices?.() || []
  const prefix = { en: 'en', ru: 'ru', uz: 'uz' }[lang] || 'en'
  const scored = voices
    .filter((v) => v.lang.toLowerCase().replace('_', '-').startsWith(prefix))
    .map((v) => {
      let score = 0
      if (/natural|neural|online|premium|enhanced|google/i.test(v.name)) score += 3
      if (lang === 'en' && /en-us/i.test(v.lang.replace('_', '-'))) score += 2
      if (v.localService === false) score += 1
      return { v, score }
    })
    .sort((a, b) => b.score - a.score)
  return scored[0]?.v || null
}

function playBrowser(text, lang, my) {
  return new Promise((resolve) => {
    const synth = typeof window !== 'undefined' ? window.speechSynthesis : null
    if (!synth || typeof SpeechSynthesisUtterance === 'undefined') return resolve('failed')
    const voice = browserVoice(lang)
    if (!voice && lang === 'uz') return resolve('failed') // no Uzbek voice: reading it with another language sounds wrong
    const u = new SpeechSynthesisUtterance(normalizeSpeech(text))
    if (voice) u.voice = voice
    u.lang = voice?.lang || { en: 'en-US', ru: 'ru-RU', uz: 'uz-UZ' }[lang]
    u.rate = rate.value
    finish = resolve
    u.onend = () => my === token && settle('ended')
    u.onerror = () => my === token && settle('failed')
    state.speaking = true
    state.source = 'browser'
    synth.speak(u)
  })
}

/**
 * Say `text`. Stops whatever is being said. `owner` marks who is talking, so a
 * bear can open its mouth only for its own lines.
 */
async function speak(text, { lang, owner = null } = {}) {
  const clean = normalizeSpeech(text)
  if (!clean) return 'failed'
  if (!enabled.value) return 'muted'
  stop()
  const my = ++token
  const language = lang || detectLang(clean)
  state.owner = owner
  state.speaking = true // the bear starts to move while the clip loads
  const clip = await prepareClip(clean, language).catch(() => null)
  if (my !== token) return 'stopped'
  const result = clip ? await playClip(clip, my) : await playBrowser(clean, language, my)
  if (my === token && state.speaking) settle(result) // paths that gave up before playing
  return result
}

/** Fetch a line ahead of time (the next lesson part) so it starts instantly. */
function prepare(text, { lang } = {}) {
  const clean = normalizeSpeech(text)
  if (!clean || !enabled.value) return
  prepareClip(clean, lang || detectLang(clean)).catch(() => {})
}

/** 0..1, how open the mouth should be right now. */
function level() {
  if (!state.speaking) return 0
  if (state.source === 'pack' || state.source === 'server') {
    if (!audio || audio.paused) return 0
    if (envelope) return envelope[Math.min(envelope.length - 1, Math.floor(audio.currentTime / 0.02))] || 0
  }
  // Loading, or the browser voice: a plain talking rhythm.
  if (!state.source) return 0
  const t = performance.now() / 1000
  return 0.25 + 0.55 * Math.abs(Math.sin(t * 10.5)) * (0.6 + 0.4 * Math.sin(t * 3.1))
}

function setEnabled(value) {
  enabled.value = !!value
  writeStorage(ENABLED_KEY, value ? 'on' : 'off')
  if (!value) stop()
}
function setRate(value) {
  if (!RATES.includes(value)) return
  rate.value = value
  writeStorage(RATE_KEY, String(value))
  if (audio) audio.playbackRate = value
}

const speaking = computed(() => state.speaking)

export function useNarrator() {
  return { enabled, rate, speaking, state, speak, prepare, stop, level, setEnabled, setRate }
}
