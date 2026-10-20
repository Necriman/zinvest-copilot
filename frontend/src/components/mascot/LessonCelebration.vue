<script setup>
/**
 * The end-of-lesson moment: the bear celebrates, coins and the streak are
 * shown, and one clear button leads to what comes next.
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import BearMascot from './BearMascot.vue'
import Icon from '@/components/ui/Icon.vue'
import { useNarrator } from '@/voice/narrator'

const props = defineProps({
  open: { type: Boolean, default: false },
  coins: { type: Number, default: 0 },
  streak: { type: Number, default: 0 },
  hasNextLesson: { type: Boolean, default: false },
  testAvailable: { type: Boolean, default: false },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
})
const emit = defineEmits(['next', 'test', 'plan', 'close'])

const { t, locale } = useI18n()
const narrator = useNarrator()
const bearTalking = computed(() => narrator.state.speaking && narrator.state.owner === 'celebration')
const hush = () => { if (narrator.state.owner === 'celebration') narrator.stop() }

const primary = ref(null)
watch(() => props.open, async (open) => {
  if (!open) return hush()
  narrator.speak(t('bear.congratulations'), { owner: 'celebration', lang: locale.value })
  await nextTick()
  primary.value?.focus()
})
onBeforeUnmount(hush)

const COLORS = ['#2e6cf6', '#d4a72c', '#22c55e', '#f97316', '#1e2a44', '#93b4fb']
const confetti = computed(() => Array.from({ length: 34 }, (_, i) => {
  const r = (n) => ((i * 9301 + n * 49297) % 233280) / 233280
  return {
    left: `${r(1) * 100}%`,
    background: COLORS[i % COLORS.length],
    animationDelay: `${r(2) * 0.6}s`,
    animationDuration: `${1.6 + r(3) * 1.2}s`,
    '--drift': `${(r(4) - 0.5) * 120}px`,
    '--spin': `${360 + r(5) * 540}deg`,
    width: `${6 + r(6) * 6}px`,
    height: `${8 + r(7) * 8}px`,
  }
}))

function primaryAction() {
  if (props.hasNextLesson) emit('next')
  else if (props.testAvailable) emit('test')
  else emit('plan')
}
</script>

<template>
  <Teleport to="body">
    <Transition name="zc">
      <div v-if="open" class="fixed inset-0 z-[80] flex items-end justify-center bg-slate-900/45 p-3 backdrop-blur-[2px] sm:items-center sm:p-6" @keydown.esc="emit('close')" @click.self="emit('close')">
        <div role="dialog" aria-modal="true" aria-labelledby="zc-title" class="zc-card relative w-full max-w-md overflow-hidden rounded-3xl bg-white px-6 pb-6 pt-2 text-center shadow-2xl dark:bg-surface">
          <div class="zc-confetti" aria-hidden="true">
            <i v-for="(style, i) in confetti" :key="i" :style="style" />
          </div>
          <div class="relative mx-auto h-56 w-56 sm:h-64 sm:w-64">
            <BearMascot mood="celebrate" interactive :label="$t('mascot.tap')" :voice="bearTalking ? narrator.level : null" />
          </div>
          <h2 id="zc-title" class="relative text-2xl font-extrabold text-slate-900 dark:text-white">{{ title || $t('celebration.title') }}</h2>
          <p class="relative mt-1 text-slate-500">{{ subtitle || (coins > 0 ? $t('celebration.subtitle') : $t('celebration.review')) }}</p>
          <div v-if="coins > 0 || streak > 0" class="relative mt-4 flex flex-wrap justify-center gap-2">
            <span v-if="coins > 0" class="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1.5 text-sm font-bold text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
              <Icon name="coin" class="h-4 w-4" /> {{ $t('celebration.coins', { n: coins }) }}
            </span>
            <span v-if="streak > 0" class="inline-flex items-center gap-1.5 rounded-full bg-orange-50 px-3 py-1.5 text-sm font-bold text-orange-700 dark:bg-orange-500/15 dark:text-orange-300">
              <Icon name="flame" filled class="h-4 w-4" /> {{ $t('celebration.streak', { n: streak }) }}
            </span>
          </div>
          <div class="relative mt-6 flex flex-col gap-2">
            <button ref="primary" type="button" class="min-h-12 rounded-2xl bg-brand-600 px-5 font-bold text-white shadow-sm transition hover:bg-brand-700" @click="primaryAction">
              {{ hasNextLesson ? $t('celebration.next') : testAvailable ? $t('celebration.test') : $t('celebration.toPlan') }}
            </button>
            <button v-if="hasNextLesson || testAvailable" type="button" class="min-h-11 rounded-2xl px-5 font-semibold text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2" @click="emit('plan')">
              {{ $t('celebration.toPlan') }}
            </button>
            <button type="button" class="min-h-11 px-5 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-200" @click="emit('close')">
              {{ $t('celebration.stay') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.zc-confetti { position: absolute; inset: 0 0 auto 0; height: 100%; pointer-events: none; overflow: hidden; }
.zc-confetti i {
  position: absolute;
  top: -20px;
  border-radius: 2px;
  opacity: 0;
  animation-name: zc-fall;
  animation-timing-function: cubic-bezier(0.25, 0.6, 0.4, 1);
  animation-fill-mode: forwards;
}
@keyframes zc-fall {
  0% { transform: translate(0, 0) rotate(0); opacity: 1; }
  85% { opacity: 1; }
  100% { transform: translate(var(--drift), 520px) rotate(var(--spin)); opacity: 0; }
}
.zc-enter-active, .zc-leave-active { transition: opacity 0.25s ease; }
.zc-enter-active .zc-card { transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1); }
.zc-enter-from, .zc-leave-to { opacity: 0; }
.zc-enter-from .zc-card { transform: translateY(40px) scale(0.96); }
@media (prefers-reduced-motion: reduce) {
  .zc-confetti { display: none; }
  .zc-enter-active .zc-card { transition: none; }
}
</style>
