<script setup>
/**
 * Zinvest AI before the first question.
 *
 * Not an empty chat with three sample prompts: the bear, one question — what
 * are we figuring out today? — the four things a tutor is for, and underneath,
 * what Zinvest already knows about this learner. That context is real: the
 * lesson they are on (or came from) and the last question they got wrong, as
 * the server read it from their tests and Daily runs. With nothing to show,
 * the panel simply is not there.
 */
import { computed } from 'vue'

import AiActions from './AiActions.vue'
import AiAvatar from './AiAvatar.vue'
import Icon from '@/components/ui/Icon.vue'

const props = defineProps({
  ctx: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
})
defineEmits(['pick'])

const learning = computed(() => props.ctx?.learning || null)
const mistake = computed(() => props.ctx?.mistake || null)
const hasContext = computed(() => !!(learning.value || mistake.value))

// The bear's offer. Arriving from a lesson, it is about that lesson — the
// learner came with a question about it, not about an old Daily. Otherwise the
// last mistake first (the most useful thing to go over), then an example.
const offer = computed(() => {
  const example = learning.value
    ? { key: 'example', line: 'aiHome.suggestExample', params: { topic: learning.value.title } }
    : null
  if (props.ctx?.from_lesson && example) return example
  if (mistake.value) return { key: 'mistake', line: 'aiHome.suggestMistake', params: {} }
  return example
})
</script>

<template>
  <div class="flex min-h-full flex-col items-center justify-center py-2 text-center">
    <!-- The AI's own face, larger here than anywhere else: this is its room. -->
    <AiAvatar large :thinking="busy" class="h-24 w-24 sm:h-28 sm:w-28" />
    <p class="mt-4 text-[11px] font-bold uppercase tracking-[0.2em] text-brand-600 dark:text-brand-300">
      {{ $t('ai.title') }}
    </p>
    <h2 class="mt-1.5 text-2xl font-bold tracking-tight text-ink sm:text-[1.75rem]">
      {{ learning && ctx?.from_lesson ? $t('aiHome.questionLesson', { topic: learning.title }) : $t('aiHome.question') }}
    </h2>
    <p class="mt-2 max-w-md text-sm leading-relaxed text-ink-muted">{{ $t('aiHome.lead') }}</p>

    <AiActions class="mt-5 w-full max-w-2xl" :ctx="ctx" :disabled="busy" @pick="$emit('pick', $event)" />

    <!-- What Zinvest already knows. -->
    <section v-if="loading || hasContext" class="mt-8 w-full max-w-xl text-left">
      <p class="flex items-center gap-3 text-[11px] font-bold uppercase tracking-[0.18em] text-ink-faint">
        <span class="h-px flex-1 bg-hairline" aria-hidden="true" />
        {{ $t('aiHome.contextTitle') }}
        <span class="h-px flex-1 bg-hairline" aria-hidden="true" />
      </p>

      <div v-if="loading" class="mt-4 space-y-2.5" aria-hidden="true">
        <div class="h-12 animate-pulse rounded-2xl bg-surface-2" />
        <div class="h-12 animate-pulse rounded-2xl bg-surface-2" />
      </div>

      <dl v-else class="mt-4 space-y-3">
        <div v-if="learning" class="flex items-start gap-3">
          <dt class="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
            <Icon name="trending" class="h-4 w-4" />
            <span class="sr-only">{{ ctx?.from_lesson ? $t('aiHome.askingAbout') : $t('aiHome.learningNow') }}</span>
          </dt>
          <dd class="min-w-0">
            <p class="text-xs font-medium text-ink-muted">
              {{ ctx?.from_lesson ? $t('aiHome.askingAbout') : $t('aiHome.learningNow') }}
            </p>
            <p class="text-sm font-semibold text-ink">
              {{ learning.title }}
              <span v-if="learning.unit_title && learning.unit_title !== learning.title" class="font-normal text-ink-muted">
                · {{ learning.unit_code }} {{ learning.unit_title }}
              </span>
            </p>
          </dd>
        </div>

        <div v-if="mistake" class="flex items-start gap-3">
          <dt class="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300">
            <Icon name="alert" class="h-4 w-4" />
            <span class="sr-only">{{ $t('aiHome.recentMistake') }}</span>
          </dt>
          <dd class="min-w-0">
            <p class="text-xs font-medium text-ink-muted">{{ $t('aiHome.recentMistake') }} · {{ mistake.where }}</p>
            <p class="text-sm font-semibold leading-snug text-ink">«{{ mistake.question }}»</p>
            <p class="mt-0.5 text-xs text-ink-muted">
              {{ $t('aiHome.yourAnswer', { a: mistake.chosen }) }} ·
              <span class="text-mint-ink">{{ $t('aiHome.rightAnswer', { a: mistake.correct }) }}</span>
            </p>
          </dd>
        </div>

        <!-- The bear's one offer, made from the above. -->
        <div v-if="offer" class="flex items-center gap-3 rounded-2xl bg-lavender px-3.5 py-3">
          <AiAvatar class="h-9 w-9" />
          <p class="min-w-0 flex-1 text-sm leading-snug text-ink">{{ $t(offer.line, offer.params) }}</p>
          <button
            type="button"
            class="shrink-0 rounded-xl bg-brand-600 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
            :disabled="busy"
            @click="$emit('pick', offer.key)"
          >
            {{ $t('aiHome.yes') }}
          </button>
        </div>
      </dl>
    </section>
  </div>
</template>
