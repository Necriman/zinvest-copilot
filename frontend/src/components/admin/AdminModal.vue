<script setup>
// Dialog shell for the admin panel: a card over a dimmed page with its own
// content slot (forms, confirmations). Same behaviour as ui/AlertModal: Esc and
// the backdrop close it, Tab stays inside, focus returns to the opener.
import { nextTick, ref, useId, watch } from 'vue'

import Icon from '@/components/ui/Icon.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
  text: { type: String, default: '' },
  wide: { type: Boolean, default: false },
  // A dialog that must be answered (the unlock prompt) still closes on Esc,
  // but not on a stray click outside it.
  persistent: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const titleId = useId()
const root = ref(null)
let restoreEl = null

function focusables() {
  if (!root.value) return []
  return Array.from(
    root.value.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'),
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

watch(
  () => props.open,
  (open) => {
    if (open) {
      restoreEl = document.activeElement
      nextTick(() => {
        // First field if there is one, else the first button.
        const field = root.value?.querySelector('input:not([type=hidden]), textarea, select')
        ;(field || focusables()[0])?.focus()
      })
    } else if (restoreEl) {
      restoreEl.focus?.()
      restoreEl = null
    }
  },
  { immediate: true },
)
</script>

<template>
  <Teleport to="body">
    <Transition name="pop">
      <div
        v-if="open"
        ref="root"
        class="fixed inset-0 z-[100] flex items-end justify-center p-3 sm:items-center sm:p-4"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        @keydown.esc.prevent="emit('close')"
        @keydown.tab="onTab"
      >
        <div class="absolute -inset-[20vmax] bg-slate-900/50" @click="persistent || emit('close')" />
        <div
          class="relative z-10 flex max-h-[calc(100vh-1.5rem)] w-full flex-col rounded-3xl border border-slate-200 bg-white shadow-float dark:border-hairline dark:bg-surface"
          :class="wide ? 'max-w-2xl' : 'max-w-md'"
        >
          <div class="flex items-start gap-3 px-5 pt-5 sm:px-6 sm:pt-6">
            <div class="min-w-0 flex-1">
              <h2 :id="titleId" class="text-lg font-bold text-slate-900 dark:text-white">{{ title }}</h2>
              <p v-if="text" class="mt-1.5 text-sm leading-relaxed text-slate-500 dark:text-slate-400">{{ text }}</p>
            </div>
            <button
              type="button"
              class="-mr-1 -mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-surface-2 dark:hover:text-slate-200"
              :aria-label="$t('admin.common.close')"
              @click="emit('close')"
            >
              <Icon name="x" class="h-4 w-4" />
            </button>
          </div>
          <div class="min-h-0 overflow-y-auto px-5 pb-5 pt-4 sm:px-6 sm:pb-6">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
