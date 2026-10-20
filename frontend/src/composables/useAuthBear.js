/**
 * What the bear on the sign-in and sign-up screens is doing.
 *
 * The forms say what is happening (typing an address, typing a password,
 * showing it, waiting for the code, a mistake, success) and AuthLayout turns
 * that into a mood, a line in the speech bubble and a gaze: the Telegram
 * monkey's trick, with our bear. One shared state, because the bear lives in
 * the layout and the forms are its children in the router view.
 */
import { reactive } from 'vue'

const state = reactive({
  // idle | reading | shy | peek | code | error | success
  status: 'idle',
  // [nx, ny] for BearMascot's `gaze`, or null to follow the pointer
  gaze: null,
  // bumped to play a one-off reaction (shake, hop...) in the layout
  reaction: { name: '', n: 0 },
  // 'form' or 'code': the layout hides the sign-in/sign-up switch on the code step
  step: 'form',
})

let settleTimer = null
let flashing = false
let canvas = null

function textWidth(input) {
  canvas ||= document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  const style = getComputedStyle(input)
  ctx.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`
  const upToCaret = input.value.slice(0, input.selectionEnd ?? input.value.length)
  return ctx.measureText(upToCaret).width
}

export function useAuthBear() {
  return state
}

export const authBear = {
  set(status) {
    clearTimeout(settleTimer)
    flashing = false
    state.status = status
    if (status !== 'reading' && status !== 'code') state.gaze = null
  },

  /** Like set(), but never cuts short a moment (a mistake, a success) in progress. */
  settle(status) {
    if (!flashing) this.set(status)
  },

  /** Follow the caret of `input` (an <input> element) with the bear's head. */
  read(input) {
    clearTimeout(settleTimer)
    state.status = 'reading'
    if (!input || typeof window === 'undefined') return
    const frac = Math.max(0, Math.min(1, textWidth(input) / Math.max(1, input.clientWidth - 24)))
    // The layout decides which way "toward the form" is (side panel or above);
    // here it is just how far along the field the caret has travelled.
    state.gaze = [frac, 1]
  },

  /** Look `frac` (0..1) of the way along the form's width. */
  gazeAlong(frac) {
    state.gaze = [Math.max(0, Math.min(1, frac)), 1]
  },

  react(name) {
    state.reaction = { name, n: state.reaction.n + 1 }
  },

  /** A short moment (a mistake, a success), then back to `after`. */
  flash(status, ms = 1600, after = 'idle') {
    clearTimeout(settleTimer)
    flashing = true
    state.status = status
    state.gaze = null
    settleTimer = setTimeout(() => {
      flashing = false
      state.status = after
    }, ms)
  },

  setStep(step) {
    state.step = step
  },

  reset() {
    clearTimeout(settleTimer)
    flashing = false
    state.status = 'idle'
    state.gaze = null
    state.step = 'form'
  },
}
