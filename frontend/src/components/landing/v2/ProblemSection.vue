<script setup>
/**
 * The turn from "here is a product" to "here is why it exists".
 *
 * Deliberately card-free. Three symptoms a visitor will recognise in
 * themselves, set as a plain list with a rule down the side, because putting
 * them in boxes would make them look like features being sold rather than
 * problems being named.
 */
import Reveal from '../Reveal.vue'

const SYMPTOMS = ['s1', 's2', 's3']
</script>

<template>
  <section id="why" class="scroll-mt-28 px-6 py-20 sm:py-28">
    <div class="mx-auto max-w-6xl">
      <Reveal>
        <p class="text-xs font-bold uppercase tracking-[0.18em] text-brand-600 dark:text-brand-400">
          {{ $t('v2.problem.eyebrow') }}
        </p>
      </Reveal>

      <Reveal :delay="80">
        <!-- Two sentences, and the second starts its own line: the assertion
             lands first, then the explanation drops under it in a lighter
             weight. Letting them run together made one long ragged block and
             lost the turn between them. -->
        <p
          class="mt-6 max-w-[20ch] text-[2rem] font-extrabold leading-[1.12] tracking-[-0.03em] text-slate-900 sm:max-w-[24ch] sm:text-[2.9rem] sm:leading-[1.08] dark:text-white"
        >
          {{ $t('v2.problem.lead') }}
          <span class="block text-slate-400 dark:text-slate-500">{{ $t('v2.problem.leadMuted') }}</span>
        </p>
      </Reveal>

      <div class="mt-12 grid gap-10 sm:mt-16 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-16">
        <ul class="zp__list">
          <Reveal v-for="(key, i) in SYMPTOMS" :key="key" as="li" :delay="120 + i * 80" class="zp__item">
            <p class="zp__itemTitle">{{ $t(`v2.problem.${key}.title`) }}</p>
            <p class="zp__itemBody">{{ $t(`v2.problem.${key}.body`) }}</p>
          </Reveal>
        </ul>

        <Reveal :delay="220" class="self-center">
          <p class="text-lg leading-[1.7] text-slate-600 sm:text-xl dark:text-slate-300">
            {{ $t('v2.problem.answer') }}
          </p>
          <p class="mt-5 text-base leading-[1.7] text-slate-500 dark:text-slate-400">
            {{ $t('v2.problem.answer2') }}
          </p>
        </Reveal>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* A single hairline down the left, with each symptom marked on it. Cheaper
   than three borders, and it reads as one list instead of three objects. */
.zp__list {
  border-left: 1px solid var(--color-hairline);
  padding-left: 1.5rem;
}
.zp__item {
  position: relative;
  padding-block: 0.9rem;
}
.zp__item + .zp__item {
  border-top: 1px solid var(--color-hairline);
}
.zp__item::before {
  content: '';
  position: absolute;
  left: -1.78rem;
  top: 1.55rem;
  width: 0.4rem;
  aspect-ratio: 1;
  border-radius: 999px;
  background: color-mix(in oklab, var(--text) 28%, transparent);
}
.zp__itemTitle {
  font-size: 1.02rem;
  font-weight: 700;
  color: var(--color-ink);
}
.zp__itemBody {
  margin-top: 0.3rem;
  font-size: 0.92rem;
  line-height: 1.65;
  color: var(--color-ink-muted);
}
</style>
