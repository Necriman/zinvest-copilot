<script setup>
/**
 * The market check the intake produced (profile.blocks.research): a verdict,
 * the demand in the founder's place, the competitors with links, the gap left,
 * the risks, the next steps and the pages the search found. Shown once after
 * the intake and again from the advisor block.
 */
import Icon from '@/components/ui/Icon.vue'

defineProps({
  research: { type: Object, required: true },
  place: { type: String, default: '' }, // "Uzbekistan, Tashkent", from the answers
})
</script>

<template>
  <div>
    <span class="so-verdict" :data-verdict="research.verdict">
      {{ $t(`startup.research.verdict.${research.verdict}`) }}
    </span>
    <p class="mt-4 text-[15px] leading-relaxed text-slate-700 dark:text-slate-200">{{ research.summary }}</p>

    <section v-if="research.demand" class="so-sec">
      <h3>{{ $t('startup.research.demand', { place: place || '—' }) }}</h3>
      <p>{{ research.demand }}</p>
    </section>

    <section v-if="research.competitors?.length" class="so-sec">
      <h3>{{ $t('startup.research.competitors') }}</h3>
      <ul class="mt-2 grid gap-2">
        <li v-for="c in research.competitors" :key="c.name" class="so-comp">
          <div class="flex items-baseline justify-between gap-3">
            <a v-if="c.url" :href="c.url" target="_blank" rel="noopener noreferrer" class="so-comp__name">
              {{ c.name }}
              <Icon name="arrowRight" class="inline h-3 w-3 -rotate-45" />
            </a>
            <span v-else class="so-comp__name">{{ c.name }}</span>
            <span v-if="c.where" class="shrink-0 text-xs text-slate-500 dark:text-slate-400">{{ c.where }}</span>
          </div>
          <p v-if="c.what" class="mt-1 text-sm text-slate-600 dark:text-slate-300">{{ c.what }}</p>
        </li>
      </ul>
    </section>

    <section v-if="research.gap" class="so-sec so-sec--gap">
      <h3>{{ $t('startup.research.gap') }}</h3>
      <p>{{ research.gap }}</p>
    </section>

    <div class="grid gap-x-6 sm:grid-cols-2">
      <section v-if="research.risks?.length" class="so-sec">
        <h3>{{ $t('startup.research.risks') }}</h3>
        <ul class="so-list">
          <li v-for="r in research.risks" :key="r">{{ r }}</li>
        </ul>
      </section>
      <section v-if="research.next_steps?.length" class="so-sec">
        <h3>{{ $t('startup.research.nextSteps') }}</h3>
        <ol class="so-list so-list--num">
          <li v-for="s in research.next_steps" :key="s">{{ s }}</li>
        </ol>
      </section>
    </div>

    <section v-if="research.sources?.length" class="so-sec">
      <h3>{{ $t('startup.research.sources') }}</h3>
      <div class="mt-2 flex flex-wrap gap-1.5">
        <a
          v-for="s in research.sources"
          :key="s.url"
          :href="s.url"
          target="_blank"
          rel="noopener noreferrer"
          class="so-source"
        >{{ s.title }}</a>
      </div>
    </section>
    <p v-if="!research.searched" class="mt-4 text-xs text-slate-500 dark:text-slate-400">{{ $t('startup.research.notSearched') }}</p>
    <p class="mt-4 text-xs text-slate-500 dark:text-slate-400">{{ $t('startup.research.disclaimer') }}</p>
  </div>
</template>

<style scoped>
.so-verdict {
  display: inline-flex;
  padding: 0.35rem 0.85rem;
  border-radius: 99px;
  font-size: 0.82rem;
  font-weight: 700;
}
.so-verdict[data-verdict='strong'] {
  background: rgba(48, 164, 108, 0.14);
  color: #1a6b45;
}
.so-verdict[data-verdict='promising'] {
  background: color-mix(in oklab, var(--brand-500) 14%, transparent);
  color: var(--brand-700);
}
.so-verdict[data-verdict='uncertain'] {
  background: rgba(245, 165, 36, 0.16);
  color: #8a5100;
}
.so-verdict[data-verdict='weak'] {
  background: rgba(229, 72, 77, 0.12);
  color: #a8232a;
}
:where(.dark) .so-verdict[data-verdict='strong'] {
  color: #6fdba5;
}
:where(.dark) .so-verdict[data-verdict='promising'] {
  color: var(--brand-300);
}
:where(.dark) .so-verdict[data-verdict='uncertain'] {
  color: #fbbf24;
}
:where(.dark) .so-verdict[data-verdict='weak'] {
  color: #ff9592;
}
.so-sec {
  margin-top: 1.4rem;
}
.so-sec h3 {
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.so-sec > p {
  margin-top: 0.4rem;
  font-size: 0.93rem;
  line-height: 1.6;
  color: var(--text);
}
.so-sec--gap {
  padding: 1rem 1.1rem;
  border-radius: 1rem;
  background: color-mix(in oklab, var(--brand-500) 8%, var(--surface));
}
.so-comp {
  padding: 0.8rem 1rem;
  border-radius: 1rem;
  border: 1px solid var(--border);
}
.so-comp__name {
  font-weight: 700;
  color: var(--text);
}
a.so-comp__name:hover,
a.so-comp__name:focus-visible {
  color: var(--brand-600);
}
.so-list {
  margin-top: 0.5rem;
  display: grid;
  gap: 0.4rem;
  padding-left: 1.1rem;
  list-style: disc;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text);
}
.so-list--num {
  list-style: decimal;
}
.so-source {
  padding: 0.3rem 0.7rem;
  border-radius: 99px;
  background: var(--surface-2);
  font-size: 0.78rem;
  color: var(--text-muted);
  text-decoration: none;
  transition: color 0.2s ease;
}
.so-source:hover,
.so-source:focus-visible {
  color: var(--brand-600);
}
</style>
