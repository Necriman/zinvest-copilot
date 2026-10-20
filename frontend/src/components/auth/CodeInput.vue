<script setup>
/**
 * Six boxes for the emailed code. Typing moves on by itself, Backspace moves
 * back, a pasted or autofilled code fills every box at once, and `complete`
 * fires as soon as the sixth digit lands. The bear looks along the boxes as
 * they fill.
 */
import { nextTick, onMounted, ref, watch } from 'vue'

import { authBear } from '@/composables/useAuthBear'

const props = defineProps({
  modelValue: { type: String, default: '' },
  length: { type: Number, default: 6 },
  disabled: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
  label: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'complete'])

const boxes = ref([])
const digits = ref(Array.from({ length: props.length }, (_, i) => props.modelValue[i] || ''))

watch(
  () => props.modelValue,
  (v) => {
    if (v === digits.value.join('')) return
    digits.value = Array.from({ length: props.length }, (_, i) => v[i] || '')
  },
)

function publish() {
  const code = digits.value.join('')
  emit('update:modelValue', code)
  if (code.length === props.length && /^\d+$/.test(code)) emit('complete', code)
}

// Along the row of boxes, the way the monkey follows the text.
function look(i) {
  authBear.settle('code')
  authBear.gazeAlong(i / (props.length - 1))
}

function focusBox(i) {
  const el = boxes.value[Math.max(0, Math.min(props.length - 1, i))]
  el?.focus()
  el?.select()
}

function fill(from, text) {
  const clean = text.replace(/\D/g, '').slice(0, props.length - from)
  if (!clean) return false
  for (let k = 0; k < clean.length; k++) digits.value[from + k] = clean[k]
  publish()
  nextTick(() => focusBox(Math.min(props.length - 1, from + clean.length)))
  return true
}

function onInput(i, e) {
  const value = e.target.value
  if (value.length > 1) {
    // Autofill ("one-time-code") or fast typing drops several digits in one box.
    e.target.value = digits.value[i]
    fill(i, value)
    return
  }
  const d = value.replace(/\D/g, '')
  digits.value[i] = d
  e.target.value = d
  publish()
  if (d && i < props.length - 1) focusBox(i + 1)
  look(i)
}

function onKeydown(i, e) {
  if (e.key === 'Backspace' && !digits.value[i] && i > 0) {
    e.preventDefault()
    digits.value[i - 1] = ''
    publish()
    focusBox(i - 1)
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault()
    focusBox(i - 1)
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    focusBox(i + 1)
  }
}

function onPaste(i, e) {
  const text = e.clipboardData?.getData('text') || ''
  if (fill(i, text)) e.preventDefault()
}

function clear() {
  digits.value = Array.from({ length: props.length }, () => '')
  publish()
  nextTick(() => focusBox(0))
}

onMounted(() => focusBox(digits.value.findIndex((d) => !d)))

defineExpose({ clear, focus: () => focusBox(digits.value.findIndex((d) => !d)) })
</script>

<template>
  <div class="ci" :class="{ 'ci--invalid': invalid }" role="group" :aria-label="label">
    <input
      v-for="(d, i) in digits"
      :key="i"
      :ref="(el) => (boxes[i] = el)"
      class="ci__box"
      :class="{ 'ci__box--filled': d }"
      :value="d"
      :disabled="disabled"
      :aria-label="`${label} ${i + 1}`"
      :autocomplete="i === 0 ? 'one-time-code' : 'off'"
      inputmode="numeric"
      pattern="[0-9]*"
      maxlength="6"
      @input="onInput(i, $event)"
      @keydown="onKeydown(i, $event)"
      @paste="onPaste(i, $event)"
      @focus="look(i)"
      @blur="authBear.settle('code')"
    />
  </div>
</template>

<style scoped>
.ci {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: clamp(0.4rem, 2vw, 0.7rem);
}
.ci__box {
  width: 100%;
  aspect-ratio: 0.86;
  max-height: 4.4rem;
  border-radius: 1rem;
  border: 1.5px solid var(--border);
  background: var(--surface);
  color: var(--text);
  text-align: center;
  font: 700 clamp(1.4rem, 1rem + 2vw, 1.9rem) / 1 ui-monospace, 'SFMono-Regular', Menlo, monospace;
  outline: none;
  caret-color: var(--brand-500);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.15s ease;
}
.ci__box:focus {
  border-color: var(--brand-500);
  box-shadow: 0 0 0 4px color-mix(in oklab, var(--brand-500) 18%, transparent);
}
.ci__box--filled {
  border-color: color-mix(in oklab, var(--brand-500) 55%, var(--border));
  animation: ci-pop 0.18s ease-out;
}
.ci--invalid .ci__box {
  border-color: #e5484d;
  animation: ci-shake 0.4s ease-in-out;
}
.ci__box:disabled {
  opacity: 0.6;
}
@keyframes ci-pop {
  50% {
    transform: scale(1.06);
  }
}
@keyframes ci-shake {
  20%,
  60% {
    transform: translateX(-4px);
  }
  40%,
  80% {
    transform: translateX(4px);
  }
}
@media (prefers-reduced-motion: reduce) {
  .ci__box {
    animation: none !important;
    transition: none;
  }
}
</style>
