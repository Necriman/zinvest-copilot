<script setup>
// Reusable, accessible confirm/cancel modal. Controlled via v-model (`modelValue`).
// Emits `confirm` / `cancel`; also useful with a promise-based route guard.
import { nextTick, ref, useId, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  confirmText: { type: String, default: 'Confirm' },
  cancelText: { type: String, default: 'Cancel' },
  tone: { type: String, default: 'default' }, // default | danger
})
const emit = defineEmits(['confirm', 'cancel', 'update:modelValue'])

const titleId = useId()
const descId = useId()
const dialogEl = ref(null)
const confirmBtn = ref(null)
let restoreEl = null

function close() {
  emit('update:modelValue', false)
}
function onConfirm() {
  emit('confirm')
  close()
}
function onCancel() {
  emit('cancel')
  close()
}

// Keep Tab focus cycling within the dialog (focus trap).
function focusables() {
  if (!dialogEl.value) return []
  return Array.from(
    dialogEl.value.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'),
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

// Focus the primary action on open; restore focus to the opener on close.
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      restoreEl = document.activeElement
      nextTick(() => confirmBtn.value?.focus())
    } else if (restoreEl) {
      restoreEl.focus?.()
      restoreEl = null
    }
  },
)
</script>

<template>
  <Teleport to="body">
    <Transition name="pop">
      <div
        v-if="modelValue"
        ref="dialogEl"
        class="fixed inset-0 z-[100] flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        :aria-describedby="descId"
        tabindex="-1"
        @keydown.esc.prevent="onCancel"
        @keydown.tab="onTab"
      >
        <!-- Backdrop (over-sized so the pop scale never reveals page edges) -->
        <div class="absolute -inset-[20vmax] bg-slate-900/50" @click="onCancel" />

        <!-- Card -->
        <div
          class="relative z-10 w-full max-w-sm rounded-3xl border border-slate-200 bg-white p-6 shadow-float dark:border-hairline dark:bg-surface"
        >
          <h2 :id="titleId" class="text-lg font-bold text-slate-900 dark:text-white">
            {{ title }}
          </h2>
          <p :id="descId" class="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
            {{ message }}
          </p>

          <div class="mt-6 flex justify-end gap-2">
            <button
              type="button"
              class="rounded-full px-4 py-2 text-sm font-semibold text-slate-600 transition-colors duration-200 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2"
              @click="onCancel"
            >
              {{ cancelText }}
            </button>
            <button
              ref="confirmBtn"
              type="button"
              class="rounded-full px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors duration-200"
              :class="
                tone === 'danger'
                  ? 'bg-red-600 hover:bg-red-700'
                  : 'bg-brand-600 hover:bg-brand-700'
              "
              @click="onConfirm"
            >
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
