<script setup>
/**
 * The Zinvest bear.
 *
 * Live 3D (see src/mascot/engine.js) when the device and the user's settings
 * allow it, otherwise the matching still sticker. The sticker also shows while
 * the model loads, so there is never an empty box.
 *
 *   <BearMascot mood="wave" interactive />
 *   const bear = ref(); bear.value.react('hop')
 *   <BearMascot mood="talk" :voice="narrator.level" />   // mouth follows real speech
 *
 * Moods: idle, wave, talk, think, listen, happy, celebrate, clap, cheer,
 * confused, sleep, and one gesture per place on the site: present, weigh,
 * introduce, invite, welcome, ready, handshake, warmup, point, proud, eager
 * (src/mascot/places.js). Reactions: hop, spin, nod, wink, flap, shake.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { stickerUrl, useMascot } from '@/composables/useMascot'

const props = defineProps({
  mood: { type: String, default: 'idle' },
  framing: { type: String, default: 'full' }, // 'full' | 'bust'
  interactive: { type: Boolean, default: false },
  follow: { type: Boolean, default: true }, // head follows the pointer
  decorations: { type: Boolean, default: true },
  label: { type: String, default: '' },
  voice: { type: Function, default: null }, // () => loudness 0..1 while the bear speaks
  // [nx, ny] in -1..1: where the head should look, overriding the pointer
  // (the sign-in form steers it along the text being typed). null = follow.
  gaze: { type: Array, default: null },
})
const emit = defineEmits(['poke'])

const { t } = useI18n()
const { live } = useMascot()

const host = ref(null)
const ready = ref(false)
const failed = ref(false)
let bear = null
let alive = true

const moodName = computed(() => String(props.mood || 'idle').toLowerCase())
const poster = computed(() => stickerUrl(moodName.value))
const showLive = computed(() => live.value && !failed.value)
const decoration = computed(() => (props.decorations ? { happy: 'sparkle', celebrate: 'sparkle', clap: 'sparkle', confused: 'question', sleep: 'sleep', think: 'dots' }[moodName.value] || '' : ''))

async function mount() {
  if (!showLive.value || bear || !host.value) return
  try {
    const { createBear } = await import('@/mascot/engine')
    if (!alive || !host.value || bear) return
    bear = await createBear(host.value, {
      mood: moodName.value,
      framing: props.framing,
      onReady: () => { if (alive) ready.value = true },
      onError: () => { failed.value = true; teardown() },
    })
    if (!alive) teardown()
    else if (props.voice) bear.setVoice(props.voice)
  } catch {
    failed.value = true
  }
}

function teardown() {
  bear?.dispose()
  bear = null
  ready.value = false
}

watch(moodName, (m) => bear?.setMood(m))
watch(() => props.voice, (fn) => bear?.setVoice(fn || null))
watch(
  () => props.gaze,
  (g) => bear?.setPointer(g ? [g[0], g[1]] : null),
  { deep: true },
)
watch(showLive, (on) => (on ? mount() : teardown()), { flush: 'post' })

// Pointer follow, only for mice and trackpads.
let pending = false
let lastEvent = null
function onPointerMove(e) {
  lastEvent = e
  if (pending || props.gaze) return
  pending = true
  requestAnimationFrame(() => {
    pending = false
    if (!bear || !host.value || !lastEvent) return
    const r = host.value.getBoundingClientRect()
    const cx = r.left + r.width / 2, cy = r.top + r.height * 0.3
    const nx = Math.max(-1, Math.min(1, (lastEvent.clientX - cx) / Math.max(320, window.innerWidth / 2)))
    const ny = Math.max(-1, Math.min(1, (lastEvent.clientY - cy) / Math.max(320, window.innerHeight / 2)))
    bear.setPointer([nx, ny])
  })
}
function onPointerLeave() {
  bear?.setPointer(null)
}
const finePointer = typeof window !== 'undefined' && window.matchMedia?.('(pointer: fine)').matches

const POKES = ['hop', 'spin', 'flap', 'wink', 'nod']
let lastPoke = ''
function poke() {
  if (!props.interactive) return
  const options = POKES.filter((p) => p !== lastPoke)
  lastPoke = options[Math.floor(Math.random() * options.length)]
  bear?.react(lastPoke)
  emit('poke', lastPoke)
}

onMounted(() => {
  mount()
  if (props.follow && finePointer) {
    window.addEventListener('pointermove', onPointerMove, { passive: true })
    document.documentElement.addEventListener('pointerleave', onPointerLeave)
  }
})
onBeforeUnmount(() => {
  alive = false
  window.removeEventListener('pointermove', onPointerMove)
  document.documentElement.removeEventListener('pointerleave', onPointerLeave)
  teardown()
})

defineExpose({
  react: (name) => bear?.react(name),
})
</script>

<template>
  <component
    :is="interactive ? 'button' : 'div'"
    :type="interactive ? 'button' : undefined"
    class="zb"
    :class="{ 'zb--interactive': interactive, 'zb--ready': ready && showLive }"
    :role="interactive ? undefined : 'img'"
    :aria-label="label || t('bear.name')"
    @click="poke"
  >
    <img :src="poster" alt="" class="zb__poster" draggable="false" decoding="async" />
    <div v-if="showLive" ref="host" class="zb__stage" />
    <span v-if="decoration" class="zb__deco" :class="`zb__deco--${decoration}`" aria-hidden="true">
      <template v-if="decoration === 'sparkle'"><i /><i /><i /></template>
      <template v-else-if="decoration === 'question'">?</template>
      <template v-else-if="decoration === 'sleep'"><b>z</b><b>z</b></template>
      <template v-else-if="decoration === 'dots'"><i /><i /><i /></template>
    </span>
  </component>
</template>

<style scoped>
.zb {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  -webkit-tap-highlight-color: transparent;
}
.zb--interactive { cursor: pointer; border-radius: 1.5rem; }
.zb--interactive:focus-visible { outline: 2px solid var(--brand-500, #2e6cf6); outline-offset: 2px; }
.zb__poster,
.zb__stage,
.zb__stage :deep(canvas) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.zb__poster {
  object-fit: contain;
  transition: opacity 0.35s ease;
  user-select: none;
  pointer-events: none;
}
.zb__stage :deep(canvas) { display: block; touch-action: pan-y; }
.zb__stage { opacity: 0; transition: opacity 0.35s ease; }
.zb--ready .zb__stage { opacity: 1; }
.zb--ready .zb__poster { opacity: 0; }

/* Decorations echo the mascot sheet: sparkles, a question mark, sleepy z's. */
.zb__deco { position: absolute; pointer-events: none; font-weight: 800; }
.zb__deco--sparkle { inset: 0; }
.zb__deco--sparkle i {
  position: absolute;
  width: 12%;
  aspect-ratio: 1;
  background: #d4a72c;
  clip-path: polygon(50% 0, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0 50%, 38% 38%);
  animation: zb-twinkle 1.8s ease-in-out infinite;
}
.zb__deco--sparkle i:nth-child(1) { left: 10%; top: 22%; }
.zb__deco--sparkle i:nth-child(2) { right: 8%; top: 14%; width: 9%; background: var(--brand-500, #2e6cf6); animation-delay: -0.6s; }
.zb__deco--sparkle i:nth-child(3) { right: 16%; top: 48%; width: 7%; animation-delay: -1.2s; }
.zb__deco--question {
  right: 10%;
  top: 4%;
  font-size: clamp(1rem, 16cqw, 3rem);
  color: var(--brand-500, #2e6cf6);
  animation: zb-bob 2.4s ease-in-out infinite;
}
.zb__deco--sleep { right: 12%; top: 8%; color: var(--brand-500, #2e6cf6); font-size: clamp(0.8rem, 10cqw, 2rem); }
.zb__deco--sleep b { display: inline-block; animation: zb-float 2.8s ease-in-out infinite; }
.zb__deco--sleep b:nth-child(2) { font-size: 0.7em; animation-delay: -1.4s; vertical-align: top; }
.zb__deco--dots { right: 8%; top: 10%; display: flex; gap: 6%; width: 26%; }
.zb__deco--dots i {
  flex: 1;
  aspect-ratio: 1;
  border-radius: 50%;
  background: #9fb4d9;
  animation: zb-dot 1.4s ease-in-out infinite;
}
.zb__deco--dots i:nth-child(2) { animation-delay: 0.2s; }
.zb__deco--dots i:nth-child(3) { animation-delay: 0.4s; }
.zb { container-type: inline-size; }

@keyframes zb-twinkle { 0%, 100% { transform: scale(0.55) rotate(0deg); opacity: 0.35; } 50% { transform: scale(1) rotate(20deg); opacity: 1; } }
@keyframes zb-bob { 0%, 100% { transform: translateY(0) rotate(-6deg); } 50% { transform: translateY(-12%) rotate(6deg); } }
@keyframes zb-float { 0% { transform: translate(0, 0); opacity: 0; } 30% { opacity: 1; } 100% { transform: translate(30%, -60%); opacity: 0; } }
@keyframes zb-dot { 0%, 100% { transform: translateY(0); opacity: 0.4; } 50% { transform: translateY(-40%); opacity: 1; } }
@media (prefers-reduced-motion: reduce) {
  .zb__deco *, .zb__deco { animation: none !important; }
  .zb__poster, .zb__stage { transition: none; }
}
</style>
