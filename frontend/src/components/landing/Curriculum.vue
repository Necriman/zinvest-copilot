<script setup>
/**
 * The first four course units, with their real lesson titles (the rest are
 * named in the "more" card). Kept in
 * i18n rather than fetched, because the landing page is public and the
 * catalogue endpoint is behind auth.
 */
import Icon from '@/components/ui/Icon.vue'
import Reveal from './Reveal.vue'
import SectionHeading from './SectionHeading.vue'

const UNITS = [
  {
    key: 'u1',
    code: '01',
    icon: 'book',
    chip: 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300',
    bar: 'bg-brand-600',
    dot: 'text-brand-500',
  },
  {
    key: 'u2',
    code: '02',
    icon: 'trending',
    chip: 'bg-sky-50 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300',
    bar: 'bg-sky-500',
    dot: 'text-sky-500',
  },
  {
    key: 'u3',
    code: '03',
    icon: 'wallet',
    chip: 'bg-violet-50 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300',
    bar: 'bg-violet-500',
    dot: 'text-violet-500',
  },
  {
    key: 'u4',
    code: '04',
    icon: 'coin',
    chip: 'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
    bar: 'bg-amber-500',
    dot: 'text-amber-500',
  },
]

// Lesson titles ship as one "·"-joined string per unit so translators keep a
// unit's list together instead of matching up parallel arrays.
const lessonsOf = (text) => text.split('·').map((s) => s.trim()).filter(Boolean)
</script>

<template>
  <section id="learning" class="scroll-mt-28 px-6 py-16 sm:py-24">
    <div class="mx-auto max-w-6xl">
      <Reveal>
        <SectionHeading
          :eyebrow="$t('landing.curriculum.eyebrow')"
          :title="$t('landing.curriculum.title')"
          :subtitle="$t('landing.curriculum.subtitle')"
        />
      </Reveal>

      <div class="mt-10 grid gap-6 sm:mt-16 md:grid-cols-2">
        <Reveal v-for="(unit, i) in UNITS" :key="unit.key" :delay="i * 80">
          <article
            class="card group h-full overflow-hidden p-7 transition duration-300 hover:-translate-y-1 hover:shadow-float"
          >
            <!-- The accent rule stretches on hover — the one moving part, so
                 the grid feels alive without anything jumping around. -->
            <span
              class="mb-6 block h-1 w-12 rounded-full transition-all duration-500 group-hover:w-20"
              :class="unit.bar"
            />

            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <p class="text-xs font-bold tracking-[0.14em] text-slate-300 dark:text-slate-600">
                  {{ unit.code }}
                </p>
                <h3 class="mt-1 text-lg font-extrabold text-slate-900 dark:text-white">
                  {{ $t(`landing.curriculum.${unit.key}.title`) }}
                </h3>
                <p class="mt-1.5 text-sm text-slate-500 dark:text-slate-400">
                  {{ $t(`landing.curriculum.${unit.key}.body`) }}
                </p>
              </div>
              <span
                class="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl transition-transform duration-300 group-hover:scale-110"
                :class="unit.chip"
              >
                <Icon :name="unit.icon" class="h-4 w-4" />
              </span>
            </div>

            <!-- Per-lesson list is detail most phone visitors skim past; it's
                 hidden below sm to keep the mobile page from running long. -->
            <ul class="mt-6 hidden space-y-2.5 border-t border-hairline pt-5 sm:block">
              <li
                v-for="lesson in lessonsOf($t(`landing.curriculum.${unit.key}.l`))"
                :key="lesson"
                class="flex items-start gap-2.5 text-sm text-slate-600 dark:text-slate-300"
              >
                <span class="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-current" :class="unit.dot" />
                {{ lesson }}
              </li>
            </ul>
          </article>
        </Reveal>
      </div>

      <!-- The library isn't finished, and the grid above shouldn't read as the
           whole of it. -->
      <Reveal :delay="120">
        <div
          class="mt-6 flex flex-col items-start gap-5 rounded-3xl border border-dashed border-hairline p-7 sm:flex-row sm:items-center"
        >
          <span
            class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-slate-100 text-slate-400 dark:bg-surface-2 dark:text-slate-300"
          >
            <Icon name="plus" class="h-5 w-5" />
          </span>
          <div class="min-w-0 flex-1">
            <h3 class="text-base font-bold text-slate-900 dark:text-white">
              {{ $t('landing.curriculum.more.title') }}
            </h3>
            <p class="mt-1.5 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
              {{ $t('landing.curriculum.more.body') }}
            </p>
          </div>
        </div>
      </Reveal>
    </div>
  </section>
</template>
