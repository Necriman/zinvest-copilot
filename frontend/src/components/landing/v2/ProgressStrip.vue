<script setup>
/**
 * Progress, kept deliberately quiet.
 *
 * Four real counters from the product — streak, coins, league, unit progress
 * — set as one band of figures rather than four trophy cards. The brief for
 * this section was "show progress without making the page childish", and the
 * restraint is the whole design: the numbers are small, the frame is a single
 * hairline row, and nothing sparkles.
 */
import Icon from '@/components/ui/Icon.vue'
import Reveal from '../Reveal.vue'

const STATS = [
  { key: 'streak', icon: 'flame', tone: 'budget' },
  { key: 'coins', icon: 'coin', tone: 'cash' },
  { key: 'league', icon: 'trophy', tone: 'risk' },
  { key: 'unit', icon: 'chart', tone: 'invest' },
]
</script>

<template>
  <section class="px-6 py-20 sm:py-24">
    <div class="mx-auto max-w-6xl">
      <Reveal>
        <div class="max-w-[44ch]">
          <p class="text-xs font-bold uppercase tracking-[0.18em] text-brand-600 dark:text-brand-400">
            {{ $t('v2.progress.eyebrow') }}
          </p>
          <h2
            class="mt-4 text-[1.75rem] font-extrabold leading-[1.12] tracking-[-0.03em] text-slate-900 sm:text-[2.1rem] dark:text-white"
          >
            {{ $t('v2.progress.title') }}
          </h2>
          <p class="mt-4 text-base leading-[1.7] text-slate-500 dark:text-slate-400">
            {{ $t('v2.progress.body') }}
          </p>
        </div>
      </Reveal>

      <Reveal :delay="120">
        <dl class="zps">
          <div v-for="stat in STATS" :key="stat.key" class="zps__cell">
            <dt class="zps__label">
              <Icon :name="stat.icon" class="h-3.5 w-3.5" :data-tone="stat.tone" />
              {{ $t(`v2.progress.${stat.key}.label`) }}
            </dt>
            <dd class="zps__value">{{ $t(`v2.progress.${stat.key}.value`) }}</dd>
            <dd class="zps__note">{{ $t(`v2.progress.${stat.key}.note`) }}</dd>
          </div>
        </dl>
      </Reveal>
    </div>
  </section>
</template>

<style scoped>
.zps {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 2.5rem;
  border-top: 1px solid var(--color-hairline);
  border-bottom: 1px solid var(--color-hairline);
}
.zps__cell {
  padding: 1.35rem 1.25rem;
}
/* Rules between, never around: the band is one object. */
.zps__cell:nth-child(odd) {
  border-right: 1px solid var(--color-hairline);
}
.zps__cell:nth-child(-n + 2) {
  border-bottom: 1px solid var(--color-hairline);
}
.zps__cell:first-child,
.zps__cell:nth-child(3) {
  padding-left: 0;
}

.zps__label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-ink-faint);
}
.zps__label [data-tone='budget'] {
  color: var(--color-budget);
}
.zps__label [data-tone='cash'] {
  color: var(--color-cash);
}
.zps__label [data-tone='risk'] {
  color: var(--color-risk);
}
.zps__label [data-tone='invest'] {
  color: var(--color-invest);
}

.zps__value {
  margin-top: 0.5rem;
  font-size: clamp(1.4rem, 4vw, 1.85rem);
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1.05;
  color: var(--color-ink);
}
.zps__note {
  margin-top: 0.3rem;
  font-size: 0.78rem;
  line-height: 1.5;
  color: var(--color-ink-muted);
}

@media (min-width: 768px) {
  .zps {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
  .zps__cell:nth-child(-n + 2) {
    border-bottom: 0;
  }
  .zps__cell:nth-child(odd) {
    border-right: 0;
  }
  .zps__cell:not(:last-child) {
    border-right: 1px solid var(--color-hairline);
  }
  .zps__cell:nth-child(3) {
    padding-left: 1.25rem;
  }
}
</style>
