<script setup>
// A single stop on the study map. Coloured by its unit's accent, and sized by
// state — the current node is the biggest thing on screen, flagged "You are
// here", so where to go next is obvious at a glance.
//
// The unit test is the unit's checkpoint and is drawn as one: a diamond, the
// same mark the landing page uses for it, so the map and the page that sold
// it speak the same visual language.
//
// The startup roadmap reuses the map: its milestones are checkpoints with their
// own `label` and `icon`, and its locked steps can be opened to read (`peek`).
import { computed } from 'vue'

import Icon from '@/components/ui/Icon.vue'
import { accentOf } from './accents'

const props = defineProps({
  node: { type: Object, required: true },
  accent: { type: String, default: 'brand' },
  index: { type: Number, default: 0 },
  // Just unlocked by a lesson finished since the last visit: it arrives with a
  // small pop, after the track has filled up to it.
  fresh: { type: Boolean, default: false },
})
const emit = defineEmits(['select'])

const palette = computed(() => accentOf(props.accent))
const isTest = computed(() => props.node.kind === 'test')
const isCurrent = computed(() => props.node.state === 'current')
const isLocked = computed(() => props.node.state === 'locked')
const isDone = computed(() => props.node.state === 'completed')

const icon = computed(() => {
  if (isTest.value) return isDone.value ? 'check' : props.node.icon || 'shield'
  if (isDone.value) return 'check'
  if (isLocked.value) return 'lock'
  return 'play'
})

// The current stop sits largest; a checkpoint is a touch larger than a lesson.
const size = computed(() => {
  if (isCurrent.value) return 'h-20 w-20'
  if (isTest.value) return 'h-[66px] w-[66px]'
  return 'h-16 w-16'
})

const tip = computed(() => props.node.reason || null)
</script>

<template>
  <button
    type="button"
    :disabled="isLocked && !node.peek"
    class="group flex flex-col items-center gap-2"
    :class="isLocked && !node.peek ? 'cursor-not-allowed' : ''"
    :title="tip"
    @click="(!isLocked || node.peek) && emit('select', node)"
  >
    <span class="relative flex flex-col items-center" :class="fresh ? 'spn-fresh' : ''">
      <!-- Where the learner is -->
      <span
        v-if="isCurrent"
        class="pill absolute -top-7 z-10 whitespace-nowrap px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wide shadow-sm"
        :class="palette.soft"
      >
        {{ $t('studyV2.here') }}
      </span>

      <span
        class="relative flex items-center justify-center transition-transform duration-150"
        :class="[
          size,
          isTest ? 'spn-diamond' : 'rounded-full',
          isLocked ? '' : 'group-hover:scale-105',
          isDone ? `${palette.fill} text-white shadow-lg` : '',
          isCurrent ? `bg-white shadow-lg ring-4 dark:bg-surface ${palette.ring} ${palette.ink}` : '',
          isLocked && isTest ? `bg-white text-slate-400 ring-2 ring-slate-200 dark:bg-surface dark:ring-hairline` : '',
          isLocked && !isTest ? 'bg-slate-200 text-slate-400 dark:bg-surface-2' : '',
        ]"
      >
        <!-- Inside the turned diamond the pulse is already turned with it; it
             only needs the diamond's corners. -->
        <span
          v-if="isCurrent"
          class="absolute inset-0 animate-ping"
          :class="[palette.pulse, isTest ? 'rounded-[0.9rem]' : 'rounded-full']"
        />
        <span class="relative flex items-center justify-center" :class="isTest ? 'spn-upright' : ''">
          <Icon :name="icon" :class="isCurrent || isTest ? 'h-7 w-7' : 'h-6 w-6'" />
        </span>

        <!-- Step number, so a run of identical circles still reads as a sequence -->
        <span
          v-if="!isTest && !isLocked"
          class="absolute -bottom-0.5 -right-0.5 flex h-5 w-5 items-center justify-center rounded-full border-2 border-white text-[10px] font-extrabold dark:border-slate-900"
          :class="palette.soft"
        >
          {{ index + 1 }}
        </span>
      </span>
    </span>

    <span
      class="max-w-[130px] rounded-md bg-white/90 px-1.5 text-center text-xs font-semibold dark:bg-surface/90"
      :class="[
        isLocked ? 'text-slate-500 dark:text-slate-400' : 'text-slate-700 dark:text-slate-200',
        isTest && !node.label ? 'mt-1 uppercase tracking-[0.12em] text-[10.5px]' : '',
        isTest && node.label ? 'mt-1 line-clamp-3 font-bold' : '',
      ]"
    >
      {{ isTest ? node.label || $t('studyV2.checkpoint') : node.title }}
    </span>
  </button>
</template>

<style scoped>
/* A checkpoint is a diamond: the node turned 45°, rounded just enough to sit
   with the circles, and its icon turned back upright. */
.spn-diamond {
  border-radius: 0.9rem;
  transform: rotate(45deg) scale(0.86);
}
.spn-upright {
  transform: rotate(-45deg);
}

/* Unlocked since the last visit: arrives after the track has reached it. */
.spn-fresh {
  animation: spn-pop 520ms cubic-bezier(0.34, 1.56, 0.64, 1) 820ms both;
}
@keyframes spn-pop {
  0% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .spn-fresh {
    animation: none;
  }
}
</style>
