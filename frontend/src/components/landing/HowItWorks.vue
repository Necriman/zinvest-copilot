<script setup>
import Icon from '@/components/ui/Icon.vue'
import Reveal from './Reveal.vue'
import SectionHeading from './SectionHeading.vue'

// Each step maps to something the product actually does: the 8-question
// assessment, the AI plan build, the split-screen lesson view, and the
// lesson/test-gated streak.
const STEPS = [
  { key: 's1', icon: 'target', tone: 'text-brand-600 bg-brand-50 dark:bg-brand-500/15 dark:text-brand-300' },
  { key: 's2', icon: 'map', tone: 'text-violet-600 bg-violet-50 dark:bg-violet-500/15 dark:text-violet-300' },
  { key: 's3', icon: 'book', tone: 'text-sky-600 bg-sky-50 dark:bg-sky-500/15 dark:text-sky-300' },
  { key: 's4', icon: 'flame', tone: 'text-orange-600 bg-orange-50 dark:bg-orange-500/15 dark:text-orange-300' },
]
</script>

<template>
  <section id="how-it-works" class="scroll-mt-28 px-6 py-16 sm:py-24">
    <div class="mx-auto max-w-6xl">
      <Reveal>
        <SectionHeading
          :eyebrow="$t('landing.how.eyebrow')"
          :title="$t('landing.how.title')"
          :subtitle="$t('landing.how.subtitle')"
        />
      </Reveal>

      <ol class="mt-10 grid gap-6 sm:mt-16 sm:grid-cols-2 lg:grid-cols-4">
        <Reveal
          v-for="(step, i) in STEPS"
          :key="step.key"
          as="li"
          :delay="i * 80"
          class="relative"
        >
          <!-- Connector to the next step; hidden on the last one and whenever
               the grid wraps to a single column. -->
          <span
            v-if="i < STEPS.length - 1"
            aria-hidden="true"
            class="absolute left-[calc(100%+0.4rem)] top-7 hidden h-px w-6 bg-gradient-to-r from-slate-200 to-transparent lg:block dark:from-hairline"
          />

          <div class="card group h-full p-6 transition duration-300 hover:-translate-y-1 hover:shadow-float">
            <div
              class="flex h-11 w-11 items-center justify-center rounded-2xl transition-transform duration-300 group-hover:scale-110"
              :class="step.tone"
            >
              <Icon :name="step.icon" class="h-5 w-5" />
            </div>
            <p class="mt-5 text-xs font-bold uppercase tracking-[0.14em] text-slate-400">
              {{ $t('landing.how.step', { n: i + 1 }) }}
            </p>
            <h3 class="mt-1.5 text-base font-bold text-slate-900 dark:text-white">
              {{ $t(`landing.how.${step.key}.title`) }}
            </h3>
            <p class="mt-2 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
              {{ $t(`landing.how.${step.key}.body`) }}
            </p>
          </div>
        </Reveal>
      </ol>
    </div>
  </section>
</template>
