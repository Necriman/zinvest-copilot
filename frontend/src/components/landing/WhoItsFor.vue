<script setup>
import Icon from '@/components/ui/Icon.vue'
import Reveal from './Reveal.vue'
import SectionHeading from './SectionHeading.vue'

const AUDIENCES = [
  { key: 'w1', icon: 'book', tone: 'bg-brand-600' },
  { key: 'w2', icon: 'wallet', tone: 'bg-emerald-500' },
  { key: 'w3', icon: 'store', tone: 'bg-pink-500' },
  { key: 'w4', icon: 'trending', tone: 'bg-violet-500' },
]
</script>

<template>
  <section id="who-its-for" class="scroll-mt-28 px-6 py-16 sm:py-24">
    <div class="mx-auto max-w-6xl">
      <Reveal>
        <SectionHeading
          :eyebrow="$t('landing.who.eyebrow')"
          :title="$t('landing.who.title')"
          :subtitle="$t('landing.who.subtitle')"
        />
      </Reveal>

      <div class="mt-10 grid gap-6 sm:mt-16 sm:grid-cols-2 lg:grid-cols-4">
        <Reveal v-for="(audience, i) in AUDIENCES" :key="audience.key" :delay="i * 80">
          <article
            class="card h-full p-7 transition duration-300 hover:-translate-y-1 hover:shadow-float"
          >
            <div
              class="flex h-12 w-12 items-center justify-center rounded-2xl text-white"
              :class="audience.tone"
            >
              <Icon :name="audience.icon" class="h-5 w-5" />
            </div>
            <h3 class="mt-5 text-base font-bold text-slate-900 dark:text-white">
              {{ $t(`landing.who.${audience.key}.title`) }}
            </h3>
            <p class="mt-2 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
              {{ $t(`landing.who.${audience.key}.body`) }}
            </p>
          </article>
        </Reveal>
      </div>
    </div>
  </section>
</template>
