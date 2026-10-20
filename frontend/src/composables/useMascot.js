// Mascot preferences, shared by every bear on the page.
//
// `animated` switches the live 3D bear off for people who find it distracting
// or run on a weak device: every bear then shows its still sticker instead.
// Reduced-motion users get the stills automatically.
import { computed, ref } from 'vue'

const KEY = 'zinvest.mascot.animated'

function read() {
  try {
    return localStorage.getItem(KEY) !== 'off'
  } catch {
    return true
  }
}

const animated = ref(read())
const reduceQuery = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null
const reducedMotion = ref(!!reduceQuery?.matches)
reduceQuery?.addEventListener?.('change', (e) => { reducedMotion.value = e.matches })

let webgl
function supportsWebGL() {
  if (webgl === undefined) {
    try {
      const c = document.createElement('canvas')
      webgl = !!(c.getContext('webgl2') || c.getContext('webgl'))
    } catch {
      webgl = false
    }
  }
  return webgl
}

export function useMascot() {
  const live = computed(() => animated.value && !reducedMotion.value && supportsWebGL())
  function setAnimated(value) {
    animated.value = !!value
    try {
      localStorage.setItem(KEY, value ? 'on' : 'off')
    } catch {
      /* private mode: the choice lasts for this visit */
    }
  }
  return { animated, reducedMotion, live, setAnimated }
}

// Sticker art rendered from the same 3D model (see scripts/mascot/).
export const STICKERS = [
  'idle', 'wave', 'think', 'happy', 'celebrate', 'clap', 'cheer', 'confused', 'sleep', 'coin', 'book', 'tablet', 'phone',
  // one per place (src/mascot/places.js)
  'present', 'weigh', 'introduce', 'invite', 'welcome', 'ready', 'handshake', 'warmup', 'point', 'proud', 'eager',
  // the sign-in screen's attentive bear
  'reading', 'shy', 'peek',
]

const MOOD_STICKER = { talk: 'wave', listen: 'idle' }
export function stickerFor(mood) {
  const name = String(mood || 'idle').toLowerCase()
  return STICKERS.includes(name) ? name : MOOD_STICKER[name] || 'idle'
}

export const stickerUrl = (name) => `/mascot/${stickerFor(name)}.webp`
