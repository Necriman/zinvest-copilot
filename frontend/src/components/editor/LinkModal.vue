<script setup>
// Compact link editor. Opened from the toolbar, the text bubble menu, or the
// right-click menu; prefilled with the current link's href when editing. Emits
// `apply` with the typed URL (the editor normalizes + sanitizes it) and `remove`
// to strip the link. Centered modal (not a popover) so it works identically from
// every entry point, including the context menu.
import { nextTick, ref, watch } from 'vue'

import Icon from '@/components/ui/Icon.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  initialUrl: { type: String, default: '' },
  editing: { type: Boolean, default: false }, // a link exists → offer Remove
})
const emit = defineEmits(['apply', 'remove', 'update:modelValue'])

const url = ref('')
const inputEl = ref(null)

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    url.value = props.initialUrl || ''
    nextTick(() => {
      inputEl.value?.focus()
      inputEl.value?.select()
    })
  },
)

function close() {
  emit('update:modelValue', false)
}
function apply() {
  const v = url.value.trim()
  if (!v) return
  emit('apply', v)
  close()
}
function remove() {
  emit('remove')
  close()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="pop">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[110] flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        :aria-label="editing ? $t('editor.linkModal.edit') : $t('editor.linkModal.add')"
        @keydown.esc.prevent="close"
      >
        <div class="absolute -inset-[20vmax] bg-slate-900/50" @click="close" />

        <div
          class="relative z-10 w-full max-w-md rounded-3xl border border-slate-200 bg-white p-5 shadow-float dark:border-hairline dark:bg-surface"
        >
          <h2 class="mb-3 flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
            <Icon name="link" class="h-4 w-4 text-brand-600" />
            {{ editing ? $t('editor.linkModal.edit') : $t('editor.linkModal.add') }}
          </h2>

          <input
            ref="inputEl"
            v-model="url"
            type="text"
            inputmode="url"
            placeholder="https://example.com"
            class="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-hairline dark:bg-surface-2 dark:text-slate-100"
            @keydown.enter.prevent="apply"
          />

          <div class="mt-4 flex items-center justify-between gap-2">
            <button
              v-if="editing"
              type="button"
              class="inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-sm font-semibold text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10"
              @click="remove"
            >
              <Icon name="unlink" class="h-4 w-4" />
              {{ $t('editor.linkModal.remove') }}
            </button>
            <span v-else />

            <div class="flex gap-2">
              <button
                type="button"
                class="rounded-full px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2"
                @click="close"
              >
                {{ $t('editor.linkModal.cancel') }}
              </button>
              <button
                type="button"
                class="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-700 disabled:opacity-50"
                :disabled="!url.trim()"
                @click="apply"
              >
                {{ $t('editor.linkModal.apply') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
