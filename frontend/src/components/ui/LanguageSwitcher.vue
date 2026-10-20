<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import Icon from './Icon.vue'
import { AVAILABLE_LOCALES, setLocale } from '@/i18n'

const { locale } = useI18n()
const root = ref(null)
const open = ref(false)
const current = computed(
  () => AVAILABLE_LOCALES.find((l) => l.code === locale.value) || AVAILABLE_LOCALES[0],
)

function choose(code) {
  setLocale(code)
  open.value = false
}

// Dismiss on outside-click / Escape. A document listener is used instead of a
// `fixed inset-0` overlay because the navbar's backdrop-filter would confine a
// fixed overlay to the navbar box (it becomes the containing block).
function onDoc(e) {
  if (open.value && root.value && !root.value.contains(e.target)) open.value = false
}
function onKey(e) {
  if (e.key === 'Escape') open.value = false
}
onMounted(() => {
  document.addEventListener('mousedown', onDoc)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDoc)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div ref="root" class="relative">
    <button
      type="button"
      class="pill px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2"
      :title="$t('common.changeLanguage')"
      @click="open = !open"
    >
      <Icon name="globe" class="h-4 w-4" />
      {{ current.label }}
      <Icon name="chevronDown" class="h-3.5 w-3.5" />
    </button>

    <Transition name="pop">
      <div
        v-if="open"
        class="absolute right-0 z-20 mt-2 w-40 origin-top-right overflow-hidden rounded-2xl border border-slate-200 bg-white py-1 shadow-float dark:border-hairline dark:bg-surface"
      >
        <button
          v-for="l in AVAILABLE_LOCALES"
          :key="l.code"
          type="button"
          class="flex w-full items-center justify-between px-4 py-2 text-sm text-slate-700 transition-colors duration-200 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-surface-2"
          :class="{ 'font-semibold text-brand-600 dark:text-brand-400': l.code === locale }"
          @click="choose(l.code)"
        >
          <span>{{ l.name }}</span>
          <span class="text-xs text-slate-400">{{ l.label }}</span>
        </button>
      </div>
    </Transition>
  </div>
</template>
