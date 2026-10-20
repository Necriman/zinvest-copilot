<script setup>
/**
 * The learning path, shown rather than described.
 *
 * The units are the real ones from the library, in the real order, and the
 * node vocabulary is the product's own: finished, where you are, a checkpoint
 * that tests the unit, and content that is simply further along. "Locked" is
 * drawn faint rather than barred — nothing in Zinvest is actually paywalled
 * at this point in the journey, and a padlock would say otherwise.
 *
 * The node the learner is on is the only thing moving on this screen.
 */
import Icon from '@/components/ui/Icon.vue'
import Reveal from '../Reveal.vue'

const NODES = [
  { key: 'n1', state: 'done' },
  { key: 'n2', state: 'done' },
  { key: 'n3', state: 'now' },
  { key: 'n4', state: 'check' },
  { key: 'n5', state: 'ahead' },
  { key: 'n6', state: 'ahead' },
]

const LEGEND = ['done', 'now', 'check', 'ahead']
</script>

<template>
  <section id="path" class="scroll-mt-28 px-6 py-20 sm:py-28">
    <div class="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[minmax(0,0.88fr)_minmax(0,1fr)] lg:items-center lg:gap-20">
      <div>
        <Reveal>
          <p class="text-xs font-bold uppercase tracking-[0.18em] text-brand-600 dark:text-brand-400">
            {{ $t('v2.path.eyebrow') }}
          </p>
          <h2
            class="mt-4 max-w-[16ch] text-[2rem] font-extrabold leading-[1.08] tracking-[-0.03em] text-slate-900 sm:text-[2.6rem] dark:text-white"
          >
            {{ $t('v2.path.title') }}
          </h2>
          <p class="mt-5 max-w-[42ch] text-base leading-[1.7] text-slate-500 dark:text-slate-400">
            {{ $t('v2.path.body') }}
          </p>
        </Reveal>

        <!-- The legend earns its place: it teaches the map's own vocabulary,
             which the app then reuses. -->
        <Reveal :delay="140">
          <dl class="zpp__legend">
            <div v-for="state in LEGEND" :key="state" class="zpp__legendRow">
              <span class="zpp__node zpp__node--sm" :data-state="state" aria-hidden="true">
                <Icon v-if="state === 'done'" name="check" class="h-3 w-3" />
                <Icon v-else-if="state === 'check'" name="shield" class="h-3 w-3" />
              </span>
              <dt class="zpp__legendTerm">{{ $t(`v2.path.legend.${state}.term`) }}</dt>
              <dd class="zpp__legendDef">{{ $t(`v2.path.legend.${state}.def`) }}</dd>
            </div>
          </dl>
        </Reveal>
      </div>

      <Reveal :delay="120">
        <ol class="zpp">
          <li v-for="node in NODES" :key="node.key" class="zpp__row" :data-state="node.state">
            <span class="zpp__node" aria-hidden="true">
              <Icon v-if="node.state === 'done'" name="check" class="h-3.5 w-3.5" />
              <Icon v-else-if="node.state === 'check'" name="shield" class="h-3.5 w-3.5" />
            </span>
            <div class="min-w-0">
              <p class="zpp__title">{{ $t(`v2.path.${node.key}.title`) }}</p>
              <p class="zpp__meta">{{ $t(`v2.path.${node.key}.meta`) }}</p>
            </div>
            <span v-if="node.state === 'now'" class="zpp__here">{{ $t('v2.path.here') }}</span>
          </li>
        </ol>
      </Reveal>
    </div>
  </section>
</template>

<style scoped>
/* ---- the map ---- */
.zpp {
  position: relative;
  display: grid;
  gap: 0.15rem;
  border-radius: 1.5rem;
  border: 1px solid var(--color-hairline);
  background-color: color-mix(in oklab, var(--surface) 92%, transparent);
  padding: 1.25rem 1.25rem 1.4rem;
  box-shadow: 0 24px 60px -40px rgb(15 23 42 / 0.45);
}

.zpp__row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 0.7rem 0.25rem;
}
/* The spine: drawn per row so it stops cleanly at the last node. */
.zpp__row:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 0.94rem;
  top: 2.2rem;
  bottom: -0.55rem;
  width: 1px;
  background: var(--color-hairline);
}
.zpp__row[data-state='done']:not(:last-child)::before {
  background: color-mix(in oklab, var(--brand-500) 45%, transparent);
}

.zpp__node {
  display: grid;
  place-items: center;
  width: 1.4rem;
  aspect-ratio: 1;
  flex-shrink: 0;
  border-radius: 999px;
  border: 1px solid var(--color-hairline);
  background: var(--surface);
  color: var(--color-ink-faint);
}
.zpp__node--sm {
  width: 1.15rem;
}

.zpp__row[data-state='done'] .zpp__node,
.zpp__node--sm[data-state='done'] {
  background: var(--brand-600);
  border-color: var(--brand-600);
  color: #fff;
}

/* Where you are. A ring that breathes — one moving thing on the page. */
.zpp__row[data-state='now'] .zpp__node,
.zpp__node--sm[data-state='now'] {
  background: var(--surface);
  border-color: var(--brand-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--brand-500) 18%, transparent);
}
.zpp__row[data-state='now'] .zpp__node::after {
  content: '';
  width: 0.5rem;
  aspect-ratio: 1;
  border-radius: 999px;
  background: var(--brand-500);
  animation: zpp-pulse 2.4s ease-in-out infinite;
}
.zpp__node--sm[data-state='now']::after {
  content: '';
  width: 0.4rem;
  aspect-ratio: 1;
  border-radius: 999px;
  background: var(--brand-500);
}
@keyframes zpp-pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(0.72);
    opacity: 0.6;
  }
}

/* A checkpoint is the unit test: same node, turned 45°, so it reads as a
   different kind of thing without a different colour. */
.zpp__row[data-state='check'] .zpp__node,
.zpp__node--sm[data-state='check'] {
  border-radius: 0.3rem;
  transform: rotate(45deg);
  border-color: color-mix(in oklab, var(--color-risk) 55%, transparent);
  color: var(--color-risk);
}
.zpp__row[data-state='check'] .zpp__node > *,
.zpp__node--sm[data-state='check'] > * {
  transform: rotate(-45deg);
}

.zpp__row[data-state='ahead'] {
  opacity: 0.45;
}

.zpp__title {
  font-size: 0.95rem;
  font-weight: 650;
  color: var(--color-ink);
}
.zpp__row[data-state='now'] .zpp__title {
  font-weight: 750;
}
.zpp__meta {
  margin-top: 0.1rem;
  font-size: 0.78rem;
  color: var(--color-ink-muted);
}

.zpp__here {
  margin-left: auto;
  flex-shrink: 0;
  border-radius: 999px;
  background: color-mix(in oklab, var(--brand-500) 14%, transparent);
  padding: 0.2rem 0.6rem;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--brand-700);
}
.dark .zpp__here {
  color: var(--brand-300);
}

/* ---- legend ---- */
.zpp__legend {
  display: grid;
  gap: 0.85rem;
  margin-top: 2.25rem;
}
.zpp__legendRow {
  display: grid;
  grid-template-columns: 1.15rem auto 1fr;
  align-items: center;
  gap: 0.6rem;
}
.zpp__legendTerm {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--color-ink);
}
.zpp__legendDef {
  font-size: 0.82rem;
  color: var(--color-ink-muted);
}
.zpp__legendRow .zpp__node--sm[data-state='ahead'] {
  opacity: 0.45;
}

@media (prefers-reduced-motion: reduce) {
  .zpp__row[data-state='now'] .zpp__node::after {
    animation: none;
  }
}
</style>
