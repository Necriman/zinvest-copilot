<script setup>
// WYSIWYG equation editor. The input area is MathLive's <math-field> web
// component (MS-Word-style: click into fractions/exponents, arrow around,
// type naturally). The colored keypad maps to MathLive `insert()` commands
// with placeholder tokens: #0 = current selection, #? = a fill-in placeholder.
// "Insert" emits the resulting LaTeX so the editor calls insertBlockMath({ latex }).
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import katex from 'katex'
import 'katex/dist/katex.min.css'
// Importing MathLive registers the <math-field> custom element as a side effect.
// The fonts CSS is bundled by Vite (sets --ML__static-fonts so MathLive skips
// its own dynamic font loader); sounds are disabled to avoid 404s + keypress beeps.
import { MathfieldElement } from 'mathlive'
import 'mathlive/fonts.css'

import Icon from '@/components/ui/Icon.vue'

MathfieldElement.soundsDirectory = null

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // When editing an existing equation, its LaTeX is passed in to prefill the field.
  initialLatex: { type: String, default: '' },
})
const emit = defineEmits(['insert', 'cancel', 'update:modelValue'])

const mf = ref(null) // the <math-field> element
const latex = ref('') // mirror of the field value (drives the Insert disabled state)
const dialogEl = ref(null)
let restoreEl = null

// Render a small KaTeX face for a keypad button (never throws).
function face(tex) {
  try {
    return katex.renderToString(tex, { throwOnError: false, output: 'html' })
  } catch {
    return tex
  }
}

// [display face (KaTeX), MathLive insert command]
// Every structural template inserts *empty* placeholders (`#?` → a MathLive
// \placeholder{} box) for each slot — including the base — so the user always
// sees square boxes to fill, exactly like MS Word (never a hardcoded "x").
const GROUPS = [
  {
    title: 'Common Operations',
    color: 'blue',
    cols: 'grid-cols-4',
    items: [
      ['\\frac{a}{b}', '\\frac{#?}{#?}'],
      ['x^2', '{#?}^{2}'],
      ['x^y', '{#?}^{#?}'],
      ['x_y', '{#?}_{#?}'],
    ],
  },
  {
    title: 'Roots & Radicals',
    color: 'green',
    cols: 'grid-cols-3',
    items: [
      ['\\sqrt{x}', '\\sqrt{#?}'],
      ['\\sqrt[3]{x}', '\\sqrt[3]{#?}'],
      ['\\sqrt[n]{x}', '\\sqrt[#?]{#?}'],
    ],
  },
  {
    title: 'Greek Letters & Constants',
    color: 'purple',
    cols: 'grid-cols-9',
    items: [
      ['\\pi', '\\pi'],
      ['\\theta', '\\theta'],
      ['\\alpha', '\\alpha'],
      ['\\beta', '\\beta'],
      ['\\gamma', '\\gamma'],
      ['\\lambda', '\\lambda'],
      ['\\mu', '\\mu'],
      ['\\sigma', '\\sigma'],
      ['\\infty', '\\infty'],
    ],
  },
  {
    title: 'Trigonometry',
    color: 'indigo',
    cols: 'grid-cols-6',
    items: [
      ['\\sin', '\\sin'],
      ['\\cos', '\\cos'],
      ['\\tan', '\\tan'],
      ['\\sec', '\\sec'],
      ['\\csc', '\\csc'],
      ['\\cot', '\\cot'],
    ],
  },
  {
    title: 'Functions',
    color: 'teal',
    cols: 'grid-cols-3',
    items: [
      ['\\log', '\\log'],
      ['\\ln', '\\ln'],
      ['\\exp', '\\exp'],
    ],
  },
  {
    title: 'Calculus',
    color: 'red',
    cols: 'grid-cols-6',
    items: [
      ['\\lim', '\\lim_{#?}'],
      ['\\sum', '\\sum_{#?}^{#?}'],
      ['\\prod', '\\prod_{#?}^{#?}'],
      ['\\int', '\\int_{#?}^{#?}'],
      ['\\partial', '\\partial'],
      ['\\nabla', '\\nabla'],
    ],
  },
]

// Pre-render every button face once.
const RENDERED = GROUPS.map((g) => ({
  ...g,
  items: g.items.map(([f, cmd]) => ({ html: face(f), cmd, aria: f })),
}))

// Desktop two-column split: keypad + Common Operations on the left, the advanced
// groups (Roots, Greek, Trig, Functions, Calculus) on the right. Mobile stacks
// everything in one column.
// Group titles are ids; the heading shown is GROUP_KEYS' translation.
const GROUP_KEYS = {
  'Common Operations': 'editor.math.groups.common',
  'Roots & Radicals': 'editor.math.groups.roots',
  'Greek Letters & Constants': 'editor.math.groups.greek',
  'Trigonometry': 'editor.math.groups.trig',
  'Functions': 'editor.math.groups.functions',
  'Calculus': 'editor.math.groups.calculus',
}
const COMMON = RENDERED.filter((g) => g.title === 'Common Operations')
const ADVANCED = RENDERED.filter((g) => g.title !== 'Common Operations')

// Calculator-style keypad rendered directly in the modal (replaces MathLive's
// floating virtual keyboard). Each key inserts LaTeX; `del` backspaces. The '0'
// key spans two columns. Auto-flows in a 5-column grid.
const KEYPAD = [
  { t: '7', v: '7' }, { t: '8', v: '8' }, { t: '9', v: '9' }, { t: '÷', v: '\\div', op: true, aria: 'divide' }, { t: '×', v: '\\times', op: true, aria: 'multiply' },
  { t: '4', v: '4' }, { t: '5', v: '5' }, { t: '6', v: '6' }, { t: '+', v: '+', op: true, aria: 'plus' }, { t: '−', v: '-', op: true, aria: 'minus' },
  { t: '1', v: '1' }, { t: '2', v: '2' }, { t: '3', v: '3' }, { t: '=', v: '=', op: true, aria: 'equals' }, { t: '⌫', del: true, aria: 'backspace' },
  { t: '0', v: '0', span: 2 }, { t: '.', v: '.' }, { t: 'x', v: 'x' }, { t: 'y', v: 'y' },
]

// Cursor-navigation arrows (useful on touch, where precise cursor placement is
// hard). Bound to MathLive move commands.
const ARROWS = [
  { t: '←', cmd: 'moveToPreviousChar', aria: 'move cursor left' },
  { t: '→', cmd: 'moveToNextChar', aria: 'move cursor right' },
]

const COLOR = {
  blue: 'border-blue-100 bg-blue-50 text-blue-700 hover:bg-blue-100 dark:border-blue-500/20 dark:bg-blue-500/10 dark:text-blue-300 dark:hover:bg-blue-500/20',
  green: 'border-green-100 bg-green-50 text-green-700 hover:bg-green-100 dark:border-green-500/20 dark:bg-green-500/10 dark:text-green-300 dark:hover:bg-green-500/20',
  purple: 'border-purple-100 bg-purple-50 text-purple-700 hover:bg-purple-100 dark:border-purple-500/20 dark:bg-purple-500/10 dark:text-purple-300 dark:hover:bg-purple-500/20',
  indigo: 'border-indigo-100 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:border-indigo-500/20 dark:bg-indigo-500/10 dark:text-indigo-300 dark:hover:bg-indigo-500/20',
  teal: 'border-teal-100 bg-teal-50 text-teal-700 hover:bg-teal-100 dark:border-teal-500/20 dark:bg-teal-500/10 dark:text-teal-300 dark:hover:bg-teal-500/20',
  red: 'border-red-100 bg-red-50 text-red-700 hover:bg-red-100 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300 dark:hover:bg-red-500/20',
}

// Insert a MathLive command at the cursor, then keep focus in the field.
function insertCmd(cmd) {
  const field = mf.value
  if (!field) return
  field.insert(cmd, { focus: true, mode: 'math' })
  latex.value = field.value
}

// Keypad key: insert its LaTeX, backspace, or run a MathLive command (arrows).
function onKey(k) {
  const field = mf.value
  if (!field) return
  if (k.del) {
    field.focus()
    field.executeCommand('deleteBackward')
  } else if (k.cmd) {
    field.focus()
    field.executeCommand(k.cmd)
  } else {
    field.insert(k.v, { focus: true, mode: 'math' })
  }
  latex.value = field.value
}

// Guard against re-entrancy when we rewrite the field value below.
let enforcing = false
function onFieldInput() {
  const field = mf.value
  if (!field || enforcing) return
  const raw = field.value ?? ''
  latex.value = raw
  // Strict placeholder persistence: after deleting a value MathLive can leave a
  // structural slot empty and invisible. Re-inflate so the square box always
  // stays:
  //  1) an empty group {} (fraction slot / radicand) → {\placeholder{}}
  //  2) a script (^ or _) with no base (start or after an operator) → prepend
  //     a \placeholder{} base, so `^{…}` becomes `\placeholder{}^{…}`.
  // The negative lookbehind skips \placeholder{}'s own braces (avoids a loop).
  const fixed = raw
    .replace(/(?<!\\placeholder)\{\}/g, '{\\placeholder{}}')
    .replace(/(^|[+\-=(,])([\^_])/g, '$1\\placeholder{}$2')
  if (fixed !== raw) {
    enforcing = true
    const caret = field.position
    field.value = fixed
    field.position = caret
    latex.value = fixed
    enforcing = false
  }
}

function clearField() {
  if (mf.value) mf.value.value = ''
  latex.value = ''
}

// MathLive marks empty slots as \placeholder{} (and filled ones as
// \placeholder{x}) — a MathLive macro KaTeX can't parse, which would make the
// editor fall back to showing raw LaTeX. Unwrap every placeholder to its
// contents (empty for blanks), looping to handle nested slots.
function toKatex(input) {
  let out = input
  let prev
  do {
    prev = out
    out = out.replace(/\\placeholder(?:\[[^\]]*\])?\{([^{}]*)\}/g, '$1')
  } while (out !== prev)
  return out.trim()
}

function close() {
  emit('update:modelValue', false)
}
function onCancel() {
  emit('cancel')
  clearField()
  close()
}
function onInsert() {
  const value = toKatex(mf.value?.value ?? '')
  if (!value) return
  emit('insert', value)
  clearField()
  close()
}

// Focus trap — keep Tab cycling inside the modal. The <math-field> is treated as
// a single stop (its own internal arrow-key navigation handles the equation).
function focusables() {
  if (!dialogEl.value) return []
  return Array.from(
    dialogEl.value.querySelectorAll('button, math-field, [href], input, [tabindex]:not([tabindex="-1"])'),
  ).filter((el) => !el.disabled && el.offsetParent !== null)
}
function onTab(e) {
  const els = focusables()
  if (!els.length) return
  const first = els[0]
  const last = els[els.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

// The <math-field> lives behind v-if, so it does NOT exist at onMounted — it is
// (re)created every time the modal opens. Configure it then.
function configureField(field) {
  // Disable MathLive's floating virtual keyboard entirely — the in-modal keypad
  // handles touch entry, and the native device keyboard may still focus cleanly.
  // 'manual' stops the grey overlay from auto-showing; hide() dismisses any
  // instance left over from a previous field.
  field.mathVirtualKeyboardPolicy = 'manual'
  window.mathVirtualKeyboard?.hide?.()
  // Keep emptied scripts as a visible placeholder box instead of auto-collapsing
  // the script (MS-Word behaviour). MathLive's default is true.
  field.smartSuperscript = false
  // Render a clear square box for every empty structural slot (num/denom, root,
  // script) so backspacing a value never leaves invisible null space.
  field.placeholderSymbol = '▢'
  field.removeEventListener('input', onFieldInput)
  field.addEventListener('input', onFieldInput)
}

// Focus the <math-field> on open (and on any click inside the modal) so hardware-
// keyboard keystrokes flow straight into the equation without tapping the box.
// We focus in nextTick and again on the next frame, since the custom element may
// not be ready to accept focus on the very first tick (Teleport + transition).
function focusField() {
  mf.value?.focus()
  requestAnimationFrame(() => mf.value?.focus())
}

// Aggressive focus trap: while the modal is open, any keystroke that lands
// somewhere other than the field (e.g. after clicking the backdrop) pulls focus
// back to the field so typing is never lost. Tab (focus cycling), Escape
// (cancel), and keys aimed at a focused button are left alone.
function onWindowKeydown(e) {
  if (e.key === 'Tab' || e.key === 'Escape') return
  const field = mf.value
  if (!field || document.activeElement === field) return
  const ae = document.activeElement
  if (ae && ae !== document.body && dialogEl.value?.contains(ae) && ae.tagName === 'BUTTON') return
  field.focus()
}

// On open: prefill with initialLatex (edit mode) or empty (new), configure, focus.
// Restore focus to the opener on close.
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      restoreEl = document.activeElement
      latex.value = props.initialLatex || ''
      window.addEventListener('keydown', onWindowKeydown)
      nextTick(() => {
        const field = mf.value
        if (!field) return
        field.value = props.initialLatex || ''
        configureField(field)
        focusField()
      })
    } else {
      window.removeEventListener('keydown', onWindowKeydown)
      if (restoreEl) {
        restoreEl.focus?.()
        restoreEl = null
      }
    }
  },
)

onBeforeUnmount(() => window.removeEventListener('keydown', onWindowKeydown))
</script>

<template>
  <Teleport to="body">
    <!-- ONE transition on the outermost wrapper. The backdrop and the card are its
         children, so a single opacity fade brings them in/out together — they can
         never fall out of sync. (No backdrop-filter: Chrome disables it while an
         ancestor's opacity animates, which made the blur snap in a beat late.) -->
    <Transition name="ml-modal">
      <div
        v-if="modelValue"
        ref="dialogEl"
        class="fixed inset-0 z-[100] flex items-center justify-center p-0 md:p-4"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('editor.math.editor')"
        @keydown.esc.prevent="onCancel"
        @keydown.tab="onTab"
        @click.prevent="focusField"
      >
        <!-- Backdrop: intentionally NOT click-to-dismiss (avoids losing a half-typed
             equation to a stray click — the user must choose Cancel or Insert). -->
        <div class="absolute -inset-[20vmax] bg-slate-900/50" />

        <!-- Full-screen + scrollable on mobile; on desktop a wide, two-column
             card (max-w-4xl) that grows to fit its content (h-auto, capped at
             95vh) so the taller layout no longer forces a vertical scrollbar. -->
        <div
          class="relative z-10 flex h-full max-h-full w-full flex-col overflow-hidden rounded-none border-0 bg-white shadow-float dark:bg-surface md:h-auto md:max-h-[95vh] md:max-w-4xl md:rounded-3xl md:border md:border-slate-200 md:dark:border-hairline"
        >
          <!-- Header -->
          <div class="relative shrink-0 px-6 pt-5 pb-3 text-center">
            <h2 class="text-lg font-bold text-slate-900 dark:text-white">{{ $t('editor.math.editor') }}</h2>
            <button
              type="button"
              class="absolute right-4 top-4 rounded-full p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-surface-2"
              :aria-label="$t('editor.math.close')"
              @click="onCancel"
            >
              <Icon name="x" class="h-5 w-5" />
            </button>
          </div>

          <!-- Body (scrolls on short viewports) -->
          <div class="min-h-0 flex-1 overflow-y-auto px-6 pb-2" v-os>
            <!-- WYSIWYG field -->
            <math-field
              ref="mf"
              class="ml-field w-full rounded-2xl border border-slate-200 bg-slate-50/60 px-4 py-3 text-2xl text-slate-900 focus-within:border-brand-400 dark:border-hairline dark:bg-surface-2 dark:text-slate-100"
            />

            <!-- Two columns on desktop; single stacked column on mobile. -->
            <div class="md:grid md:grid-cols-2 md:gap-x-6">
              <!-- LEFT column: keypad + arrows + Common Operations -->
              <div>
                <!-- In-modal keypad: numbers · variables · operators · backspace.
                     mousedown.prevent keeps the field focused so keys insert at
                     the caret. Replaces MathLive's floating virtual keyboard. -->
                <div class="mt-3 grid grid-cols-5 gap-1.5">
                  <button
                    v-for="(k, i) in KEYPAD"
                    :key="i"
                    type="button"
                    :aria-label="k.aria || k.t"
                    :class="[
                      'flex items-center justify-center rounded-xl border py-2.5 text-lg font-semibold transition-colors',
                      k.span === 2 ? 'col-span-2' : '',
                      k.del
                        ? 'border-red-100 bg-red-50 text-red-500 hover:bg-red-100 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300'
                        : k.op
                          ? 'border-brand-100 bg-brand-50 text-brand-700 hover:bg-brand-100 dark:border-brand-500/20 dark:bg-brand-500/10 dark:text-brand-300 dark:hover:bg-brand-500/20'
                          : 'border-slate-200 bg-white text-slate-800 hover:bg-slate-50 dark:border-hairline dark:bg-surface dark:text-slate-100 dark:hover:bg-surface-2',
                    ]"
                    @mousedown.prevent
                    @click="onKey(k)"
                  >
                    {{ k.t }}
                  </button>
                </div>

                <!-- Cursor-navigation arrows -->
                <div class="mt-1.5 grid grid-cols-2 gap-1.5">
                  <button
                    v-for="(a, i) in ARROWS"
                    :key="i"
                    type="button"
                    :aria-label="a.aria"
                    class="flex items-center justify-center rounded-xl border border-slate-200 bg-white py-2.5 text-lg font-semibold text-slate-700 transition-colors hover:bg-slate-50 dark:border-hairline dark:bg-surface dark:text-slate-100 dark:hover:bg-surface-2"
                    @mousedown.prevent
                    @click="onKey(a)"
                  >
                    {{ a.t }}
                  </button>
                </div>

                <!-- Common Operations -->
                <div v-for="g in COMMON" :key="g.title" class="mt-4">
                  <p class="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{{ $t(GROUP_KEYS[g.title]) }}</p>
                  <div class="grid gap-2" :class="g.cols">
                    <button
                      v-for="(it, i) in g.items"
                      :key="i"
                      type="button"
                      class="flex items-center justify-center rounded-xl border py-2 transition-colors duration-150"
                      :class="COLOR[g.color]"
                      :aria-label="it.aria"
                      :title="it.aria"
                      @mousedown.prevent
                      @click="insertCmd(it.cmd)"
                      v-html="it.html"
                    />
                  </div>
                </div>
              </div>

              <!-- RIGHT column: advanced groups (Roots, Greek, Trig, Functions, Calculus) -->
              <div>
                <div v-for="g in ADVANCED" :key="g.title" class="mt-4">
                  <p class="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{{ $t(GROUP_KEYS[g.title]) }}</p>
                  <div class="grid gap-2" :class="g.cols">
                    <button
                      v-for="(it, i) in g.items"
                      :key="i"
                      type="button"
                      class="flex items-center justify-center rounded-xl border py-2 transition-colors duration-150"
                      :class="COLOR[g.color]"
                      :aria-label="it.aria"
                      :title="it.aria"
                      @mousedown.prevent
                      @click="insertCmd(it.cmd)"
                      v-html="it.html"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex shrink-0 gap-3 border-t border-slate-100 p-4 dark:border-hairline">
            <button
              type="button"
              class="flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-50 dark:border-hairline dark:text-slate-300 dark:hover:bg-surface-2"
              @click="onCancel"
            >
              <Icon name="x" class="h-4 w-4" /> {{ $t('editor.math.cancel') }}
            </button>
            <button
              type="button"
              :disabled="!latex.trim()"
              class="flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50"
              :class="
                latex.trim()
                  ? 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-500/20 dark:text-green-300 dark:hover:bg-green-500/30'
                  : 'bg-green-50 text-green-400 dark:bg-green-500/10'
              "
              @click="onInsert"
            >
              <Icon name="check" class="h-4 w-4" /> {{ $t('editor.math.insert') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* MathLive field: give it comfortable height + hide the built-in menu toggle. */
.ml-field {
  min-height: 4.25rem;
  display: flex;
  align-items: center;
  --caret-color: var(--brand-500);
  --selection-background-color: color-mix(in srgb, var(--brand-500), transparent 78%);
}
.ml-field::part(menu-toggle) {
  display: none;
}
.ml-field::part(virtual-keyboard-toggle) {
  display: none;
}
</style>
