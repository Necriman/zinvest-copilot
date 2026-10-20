<script setup>
/**
 * Answer feedback with the bear: happy on a right answer, puzzled on a wrong
 * one, with a short line that varies by question so it never feels canned.
 * The bear says the line out loud (recorded voice, see src/voice).
 */
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

import BearSticker from './BearSticker.vue'
import { useNarrator } from '@/voice/narrator'

const props = defineProps({
  correct: { type: Boolean, default: false },
  answer: { type: String, default: '' }, // the right answer, shown when wrong
  explanation: { type: String, default: '' },
  seed: { type: String, default: '' }, // e.g. the question id
})

function hash(text) {
  let h = 0
  for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) >>> 0
  return h
}
const line = computed(() => (props.correct ? `mascot.praise${(hash(props.seed) % 5) + 1}` : `mascot.encourage${(hash(props.seed) % 4) + 1}`))

const { t, locale } = useI18n()
const narrator = useNarrator()
onMounted(() => narrator.speak(t(line.value), { owner: 'feedback', lang: locale.value }))
</script>

<template>
  <div
    class="flex items-start gap-3 rounded-2xl p-3"
    :class="correct ? 'bg-emerald-50 text-emerald-900 dark:bg-emerald-500/10 dark:text-emerald-200' : 'bg-amber-50 text-amber-900 dark:bg-amber-500/10 dark:text-amber-200'"
    role="status"
  >
    <BearSticker :name="correct ? 'happy' : 'confused'" pop class="-my-1 h-16 w-16 shrink-0" />
    <div class="min-w-0 pt-1">
      <p class="font-bold">{{ $t(line) }}</p>
      <p v-if="!correct && answer" class="mt-1 text-sm">{{ $t('mascot.rightAnswer', { answer }) }}</p>
      <p v-if="explanation" class="mt-1 text-sm opacity-90">{{ explanation }}</p>
    </div>
  </div>
</template>
