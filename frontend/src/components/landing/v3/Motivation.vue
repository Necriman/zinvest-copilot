<script setup>
/**
 * What keeps people coming back, as a bento of the app's real mechanics:
 * the streak (with its week), coins counting up, the weekly league table and
 * the daily questions. Nothing here can be bought, which the tiles say.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import Icon from '@/components/ui/Icon.vue'
import Reveal from '../Reveal.vue'
import Icon3d from './Icon3d.vue'

const { t } = useI18n()
const days = computed(() => t('v3.motivation.days').split(','))

// The league table is an illustration; "you" sit second, one push from first.
const TABLE = [
  { name: 'Aziz', pts: 540 },
  { name: null, pts: 420 },
  { name: 'Malika', pts: 385 },
  { name: 'Timur', pts: 310 },
]

// Coins count up once the tile is on screen.
const COINS = 420
const coins = ref(0)
const coinTile = ref(null)
let io = null
let raf = 0
onMounted(() => {
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (reduced || typeof IntersectionObserver === 'undefined') {
    coins.value = COINS
    return
  }
  io = new IntersectionObserver(([e]) => {
    if (!e.isIntersecting) return
    io.disconnect()
    const t0 = performance.now()
    const step = (now) => {
      const u = Math.min(1, (now - t0) / 1200)
      coins.value = Math.round(COINS * (1 - Math.pow(1 - u, 3)))
      if (u < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
  }, { threshold: 0.4 })
  if (coinTile.value) io.observe(coinTile.value.$el || coinTile.value)
})
onBeforeUnmount(() => {
  io?.disconnect()
  cancelAnimationFrame(raf)
})
</script>

<template>
  <section class="z3-section">
    <div class="z3-wrap">
      <div class="text-center">
        <p class="z3-eyebrow">{{ $t('v3.motivation.eyebrow') }}</p>
        <h2 class="z3-h2 mx-auto max-w-[18ch]">{{ $t('v3.motivation.title') }}</h2>
      </div>

      <div class="zm">
        <!-- streak -->
        <Reveal class="zm__tile zm__tile--streak">
          <Icon3d name="flame" class="zm__flame" />
          <h3 class="zm__big">{{ $t('v3.motivation.streakTitle') }}</h3>
          <ul class="zm__week">
            <li v-for="(d, i) in days" :key="i" :data-today="i === 6 ? 'true' : undefined">
              <span class="zm__dot">
                <Icon v-if="i < 6" name="check" class="h-4 w-4" />
              </span>
              <span class="zm__day">{{ d }}</span>
            </li>
          </ul>
          <p class="zm__note">{{ $t('v3.motivation.streakNote') }}</p>
        </Reveal>

        <!-- coins -->
        <Reveal ref="coinTile" :delay="80" class="zm__tile zm__tile--coins">
          <div class="flex items-center gap-4">
            <Icon3d name="coins" class="h-20 w-20 shrink-0" />
            <p class="zm__count">
              <span class="zm__num">{{ coins }}</span>
              <span class="zm__unit">{{ $t('v3.motivation.coinsLabel') }}</span>
            </p>
          </div>
          <p class="zm__note">{{ $t('v3.motivation.coinsNote') }}</p>
        </Reveal>

        <!-- league -->
        <Reveal :delay="160" class="zm__tile zm__tile--league">
          <div class="flex items-center justify-between gap-3">
            <h3 class="zm__title">{{ $t('v3.motivation.leagueTitle') }}</h3>
            <Icon3d name="trophy" class="h-14 w-14 shrink-0" />
          </div>
          <ol class="zm__table">
            <li v-for="(row, i) in TABLE" :key="i" :data-you="row.name ? undefined : 'true'">
              <span class="zm__rank">{{ i + 1 }}</span>
              <span class="zm__avatar">{{ (row.name || $t('v3.motivation.you'))[0] }}</span>
              <span class="zm__name">{{ row.name || $t('v3.motivation.you') }}</span>
              <span class="zm__pts">{{ row.pts }} {{ $t('v3.motivation.pts') }}</span>
            </li>
          </ol>
          <p class="zm__note">{{ $t('v3.motivation.leagueNote') }}</p>
        </Reveal>

        <!-- daily -->
        <Reveal :delay="120" class="zm__tile zm__tile--daily">
          <div class="flex items-center gap-4">
            <Icon3d name="target" class="h-16 w-16 shrink-0" />
            <div>
              <h3 class="zm__title">{{ $t('v3.motivation.dailyTitle') }}</h3>
              <div class="zm__five" aria-hidden="true">
                <i v-for="k in 5" :key="k" :data-on="k <= 3 ? 'true' : undefined" />
              </div>
            </div>
          </div>
          <p class="zm__note">{{ $t('v3.motivation.dailyNote') }}</p>
        </Reveal>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zm {
  margin-top: 3.5rem;
  display: grid;
  gap: 1.25rem;
}
@media (min-width: 768px) {
  .zm {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (min-width: 1024px) {
  .zm {
    grid-template-columns: 1.1fr 1fr 1.1fr;
    grid-template-rows: auto auto;
  }
  .zm__tile--streak {
    grid-row: 1 / span 2;
  }
  .zm__tile--league {
    grid-column: 3;
    grid-row: 1 / span 2;
  }
  .zm__tile--coins {
    grid-column: 2;
    grid-row: 1;
  }
  .zm__tile--daily {
    grid-column: 2;
    grid-row: 2;
  }
}
.zm__tile {
  --tint: var(--z3-card);
  --edge: var(--z3-card-edge);
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.75rem;
  border-radius: 1.75rem;
  background: var(--tint);
  border: 2px solid var(--edge);
  box-shadow: 0 6px 0 var(--edge);
}
.zm__tile--streak {
  --tint: var(--z3-yellow-soft);
  --edge: color-mix(in oklab, var(--z3-yellow) 45%, var(--z3-card-edge));
  align-items: center;
  text-align: center;
  justify-content: center;
}
.zm__tile--coins {
  --tint: var(--z3-purple-soft);
  --edge: color-mix(in oklab, var(--z3-purple) 22%, var(--z3-card-edge));
}
.zm__tile--league {
  --tint: var(--z3-blue-soft);
  --edge: color-mix(in oklab, var(--z3-blue) 30%, var(--z3-card-edge));
}
.zm__tile--daily {
  --tint: var(--z3-green-soft);
  --edge: color-mix(in oklab, var(--z3-green) 35%, var(--z3-card-edge));
}
.zm__flame {
  width: 8.5rem;
  height: 8.5rem;
}
.zm__big {
  font: 900 2rem/1.1 var(--z3-font);
  color: #c2410c;
}
.dark .zm__big {
  color: #ffb36b;
}
.zm__title {
  font: 900 1.4rem/1.2 var(--z3-font);
  color: var(--z3-ink);
}
.zm__note {
  font: 600 0.98rem/1.55 var(--z3-font);
  color: var(--z3-muted);
}
.zm__week {
  display: flex;
  gap: 0.45rem;
}
.zm__week li {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
}
.zm__dot {
  display: inline-flex;
  width: 2.2rem;
  height: 2.2rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #fb8c2b;
  box-shadow: 0 3px 0 #d4691a;
  color: #fff;
}
.zm__week li[data-today] .zm__dot {
  background: transparent;
  box-shadow: none;
  border: 3px dashed #fb8c2b;
  animation: zm-pulse 1.6s ease-in-out infinite;
}
.zm__day {
  font: 800 0.72rem/1 var(--z3-font);
  color: var(--z3-muted);
}
@keyframes zm-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.12); }
}
.zm__count {
  display: flex;
  flex-direction: column;
}
.zm__num {
  font: 900 3.2rem/1 var(--z3-font);
  color: var(--z3-purple);
  font-variant-numeric: tabular-nums;
}
.zm__unit {
  font: 800 1rem/1.2 var(--z3-font);
  color: var(--z3-muted);
}
.zm__table {
  display: grid;
  gap: 0.55rem;
}
.zm__table li {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.6rem 0.8rem;
  border-radius: 0.9rem;
  background: var(--z3-card);
  font: 800 0.98rem/1.2 var(--z3-font);
  color: var(--z3-ink);
}
.zm__table li[data-you] {
  background: var(--z3-blue);
  color: #fff;
  box-shadow: 0 4px 0 var(--z3-blue-edge);
}
.zm__rank {
  width: 1.2rem;
  text-align: center;
  color: var(--z3-muted);
}
.zm__table li[data-you] .zm__rank {
  color: #fff;
}
.zm__avatar {
  display: inline-flex;
  width: 2rem;
  height: 2rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--z3-purple-soft);
  color: var(--z3-purple);
  font-size: 0.9rem;
}
.zm__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.zm__pts {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.zm__five {
  margin-top: 0.5rem;
  display: flex;
  gap: 0.35rem;
}
.zm__five i {
  width: 1.6rem;
  height: 0.7rem;
  border-radius: 999px;
  background: var(--z3-card);
  border: 2px solid color-mix(in oklab, var(--z3-green) 40%, var(--z3-card-edge));
}
.zm__five i[data-on] {
  background: var(--z3-green);
  border-color: var(--z3-green-edge);
}
@media (prefers-reduced-motion: reduce) {
  .zm__week li[data-today] .zm__dot {
    animation: none;
  }
}
</style>
