<script setup>
/**
 * The two games on Home: today's "Up or down?" round as a teaser — its chart
 * up to the question mark — and the trainer next to it.
 */
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import PriceChart from '@/components/games/PriceChart.vue'
import Icon from '@/components/ui/Icon.vue'
import { getPredict } from '@/api/games'
import { useAsyncData } from '@/composables/useAsyncData'

const { data } = useAsyncData(getPredict)
const round = computed(() => data.value?.round || null)
</script>

<template>
  <section class="mb-5">
    <h2 class="mb-3 text-lg font-bold text-ink">{{ $t('games.title') }}</h2>
    <div class="grid gap-3 @xl:grid-cols-2">
      <RouterLink :to="{ name: 'predict' }" class="games-tile group">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="flex items-center gap-2 font-bold text-ink">
              <Icon name="trending" class="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              {{ $t('upDown.title') }}
            </p>
            <p class="mt-1 text-sm text-ink-muted">
              {{
                data && !round
                  ? $t('games.predictDone')
                  : $t('games.predictSub', { n: data?.left_today ?? 3, coins: data?.coins_right ?? 5 })
              }}
            </p>
          </div>
          <span class="games-go">{{ $t('games.play') }}<Icon name="arrowRight" class="h-3.5 w-3.5" /></span>
        </div>
        <div v-if="round" class="mt-3">
          <p class="mb-1 truncate text-xs font-semibold text-ink-muted">{{ round.asset }} · {{ round.when }}</p>
          <PriceChart :before="round.before" :unit="round.unit" mini :label="$t('upDown.chart', { asset: round.asset, when: round.when })" />
        </div>
      </RouterLink>

      <RouterLink :to="{ name: 'practice' }" class="games-tile group">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="flex items-center gap-2 font-bold text-ink">
              <Icon name="target" class="h-4 w-4 text-brand-600 dark:text-brand-400" />
              {{ $t('trainer.title') }}
            </p>
            <p class="mt-1 text-sm text-ink-muted">{{ $t('games.practiceSub') }}</p>
          </div>
          <span class="games-go">{{ $t('games.open') }}<Icon name="arrowRight" class="h-3.5 w-3.5" /></span>
        </div>
        <div class="mt-3 grid grid-cols-2 gap-1.5" aria-hidden="true">
          <span v-for="letter in ['A', 'B', 'C', 'D']" :key="letter" class="games-option">
            <span class="games-option__letter" :class="{ 'is-right': letter === 'B' }">{{ letter }}</span>
            <span class="h-1.5 flex-1 rounded-full bg-slate-200 dark:bg-slate-700" />
          </span>
        </div>
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.games-tile {
  display: block;
  border-radius: 1.25rem;
  border: 1px solid var(--color-hairline);
  background: var(--surface);
  padding: 1rem 1.1rem;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}
.games-tile:hover {
  transform: translateY(-2px);
  border-color: color-mix(in oklab, var(--brand-500, #3b82f6) 45%, transparent);
  box-shadow: 0 18px 40px -28px rgb(15 23 42 / 0.45);
}
.games-tile:focus-visible {
  outline: 2px solid var(--brand-500, #3b82f6);
  outline-offset: 2px;
}
.games-go {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 0.25rem;
  border-radius: 999px;
  background: var(--brand-600, #2563eb);
  padding: 0.3rem 0.7rem;
  font-size: 0.78rem;
  font-weight: 700;
  color: #fff;
}
.games-option {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  border-radius: 0.6rem;
  border: 1px solid var(--color-hairline);
  padding: 0.3rem 0.45rem;
}
.games-option__letter {
  display: grid;
  height: 1.1rem;
  width: 1.1rem;
  place-items: center;
  border-radius: 0.35rem;
  background: var(--surface-2, #f1f5f9);
  font-size: 0.6rem;
  font-weight: 800;
  color: var(--color-ink-muted);
}
.games-option__letter.is-right {
  background: #22c55e;
  color: #fff;
}
@media (prefers-reduced-motion: reduce) {
  .games-tile,
  .games-tile:hover {
    transform: none;
  }
}
</style>
