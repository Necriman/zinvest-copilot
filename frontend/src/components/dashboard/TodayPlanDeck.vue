<script setup>
/**
 * "Your plan for today" as a deck of cards: the next study step, one question
 * for the AI, one entry in the startup's books. Start a card or put it back
 * under the deck for later. Clear every card and the last one turns into a
 * star, with the bear celebrating. Laid out by the width of its column.
 */
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

import BearSticker from '@/components/mascot/BearSticker.vue'
import Icon from '@/components/ui/Icon.vue'
import { CARD_ICON, cardRoute, cardText } from './planCards'

const props = defineProps({
  plan: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  // Today's page shows the study step in its own card above, and titles this
  // deck as the rest of the day.
  titleKey: { type: String, default: 'deck.title' },
})
const { t } = useI18n()

const cards = computed(() => props.plan?.cards || [])
const allDone = computed(() => cards.value.length > 0 && cards.value.every((c) => c.done))

// Deck order: open cards first, in plan order; "Later" moves the front card back.
const order = ref([])
watch(cards, (list) => {
  const open = list.map((c, i) => i).filter((i) => !list[i].done)
  const done = list.map((c, i) => i).filter((i) => list[i].done)
  order.value = [...open, ...done]
}, { immediate: true })

const front = computed(() => cards.value[order.value[0]] || null)
const layers = computed(() => Math.min(2, order.value.length - 1))
function later() {
  if (order.value.length < 2) return
  order.value = [...order.value.slice(1), order.value[0]]
}
function bringToFront(index) {
  order.value = [index, ...order.value.filter((i) => i !== index)]
}

const text = (card) => cardText(card, t)
const meta = (card) => {
  const parts = [t('deck.minutes', { n: card.minutes })]
  if (card.coins && !card.done) parts.push(t('deck.coins', { n: card.coins }))
  return parts.join(' · ')
}
const minutesLeft = computed(() => props.plan?.minutes_left ?? 0)
</script>

<template>
  <section class="card @container mb-5 p-5 @xl:p-6">
    <!-- Header: what this is and how far along -->
    <header class="flex items-center gap-3">
      <BearSticker :name="allDone ? 'celebrate' : 'book'" class="h-12 w-12 shrink-0" />
      <div class="min-w-0 flex-1">
        <h2 class="text-lg font-bold leading-tight tracking-tight text-ink">{{ $t(titleKey) }}</h2>
        <p class="mt-0.5 text-sm text-ink-muted">
          <template v-if="plan">
            {{ $t('deck.progress', { done: plan.done, total: plan.total }) }}<template v-if="minutesLeft"> · {{ $t('deck.minutes', { n: minutesLeft }) }}</template>
          </template>
          <template v-else>&nbsp;</template>
        </p>
      </div>
      <div v-if="cards.length" class="hidden gap-1.5 @sm:flex" aria-hidden="true">
        <span v-for="card in cards" :key="card.key" class="h-1.5 w-6 rounded-full" :class="card.done ? 'bg-mint-ink' : 'bg-surface-2 dark:bg-white/10'" />
      </div>
    </header>

    <div class="mt-5 grid gap-5 @xl:grid-cols-[minmax(0,1fr)_minmax(0,15rem)] @xl:items-start @3xl:grid-cols-[minmax(0,1fr)_18rem]">
      <!-- The deck -->
      <div class="@xl:order-2">
        <div class="relative h-52">
          <template v-if="!allDone && front">
            <span
              v-for="k in layers"
              :key="k"
              class="absolute rounded-3xl border border-hairline bg-surface"
              :style="{ inset: `${k * 6}px ${12 - k * 6}px ${12 - k * 6}px ${k * 6}px`, zIndex: 3 - k }"
              aria-hidden="true"
            />
            <Transition name="zd-swap" mode="out-in">
              <div :key="front.key" class="zd-card absolute inset-0 bottom-3 right-3 z-10 flex flex-col justify-between rounded-3xl p-5 text-white" :class="front.done ? 'zd-card--done' : ''">
                <div class="min-w-0">
                  <p class="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-white/80">
                    <span class="flex h-6 w-6 items-center justify-center rounded-full bg-white/20"><Icon :name="CARD_ICON[front.key]" class="h-3.5 w-3.5" /></span>
                    {{ $t('deck.card', { i: 1, n: order.length }) }} · {{ text(front).kicker }}
                  </p>
                  <h3 class="mt-3 line-clamp-2 text-xl font-bold leading-snug tracking-tight">{{ text(front).title }}</h3>
                  <p class="mt-1 text-sm font-medium text-white/85">{{ front.done ? $t('deck.done') : meta(front) }}</p>
                </div>
                <div class="flex items-center gap-1.5">
                  <RouterLink :to="cardRoute(front)" class="inline-flex min-h-10 items-center gap-2 rounded-xl bg-white px-4 text-sm font-bold text-slate-900 shadow-sm transition hover:-translate-y-0.5">
                    <Icon :name="front.done ? 'arrowRight' : 'play'" class="h-4 w-4" /> {{ front.done ? $t('deck.again') : $t('deck.start') }}
                  </RouterLink>
                  <button v-if="order.length > 1" type="button" class="min-h-10 rounded-xl px-3 text-sm font-semibold text-white/90 transition hover:bg-white/15" @click="later">{{ $t('deck.skip') }}</button>
                </div>
              </div>
            </Transition>
          </template>
          <div v-else-if="allDone" class="zd-star-card absolute inset-0 bottom-3 right-3 flex items-center gap-3 rounded-3xl p-4 text-amber-950">
            <BearSticker name="celebrate" pop class="h-28 w-28 shrink-0" />
            <div class="min-w-0">
              <svg class="zd-star h-8 w-8" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z" /></svg>
              <h3 class="mt-1 text-lg font-bold leading-tight">{{ $t('deck.starTitle') }}</h3>
              <p class="mt-1 text-sm font-medium">{{ $t('deck.starText') }}</p>
            </div>
          </div>
          <div v-else class="absolute inset-0 bottom-3 right-3 animate-pulse rounded-3xl bg-surface-2" aria-hidden="true" />
        </div>
        <p v-if="!allDone" class="mt-2 flex items-start gap-1.5 text-xs leading-relaxed text-ink-muted">
          <svg class="mt-px h-3.5 w-3.5 shrink-0 text-amber-500" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z" /></svg>
          {{ $t('deck.hint') }}
        </p>
      </div>

      <!-- The list -->
      <ol class="space-y-1 @xl:order-1">
        <li v-for="(card, i) in cards" :key="card.key">
          <button
            type="button"
            class="flex w-full items-center gap-3 rounded-2xl px-2.5 py-2 text-left transition hover:bg-surface-2"
            :class="front === card && !allDone ? 'bg-surface-2' : ''"
            :aria-current="front === card && !allDone ? 'true' : undefined"
            @click="bringToFront(i)"
          >
            <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl" :class="card.done ? 'bg-mint text-mint-ink' : 'bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300'">
              <Icon :name="card.done ? 'check' : CARD_ICON[card.key]" class="h-5 w-5" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-semibold" :class="card.done ? 'text-ink-muted line-through decoration-1' : 'text-ink'">{{ text(card).title }}</span>
              <span class="block truncate text-xs text-ink-muted">{{ text(card).kicker }} · {{ card.done ? $t('deck.done') : $t('deck.minutes', { n: card.minutes }) }}</span>
            </span>
          </button>
        </li>
        <li v-if="loading && !cards.length" class="space-y-1" aria-hidden="true">
          <span v-for="n in 3" :key="n" class="block h-14 animate-pulse rounded-2xl bg-surface-2" />
        </li>
      </ol>
    </div>
  </section>
</template>

<style scoped>
.zd-card {
  background: linear-gradient(135deg, var(--brand-600), var(--brand-500));
  box-shadow: 0 16px 32px -22px color-mix(in srgb, var(--brand-700) 80%, transparent);
}
.zd-card--done { background: linear-gradient(135deg, #0f9f7a, #10b981); }
.zd-star-card { background: linear-gradient(135deg, #fde68a, #fbbf24); }
.zd-swap-enter-active, .zd-swap-leave-active { transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.3s ease; }
.zd-swap-enter-from { opacity: 0; transform: translate(10px, 8px) scale(0.97); }
.zd-swap-leave-to { opacity: 0; transform: translateX(-24px) rotate(-3deg); }
.zd-star { color: #b45309; animation: zd-pop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) both; }
@keyframes zd-pop { from { transform: scale(0.2) rotate(-40deg); opacity: 0; } to { transform: none; opacity: 1; } }
@media (prefers-reduced-motion: reduce) {
  .zd-swap-enter-active, .zd-swap-leave-active { transition: none; }
  .zd-star { animation: none; }
}
</style>
