<script setup>
/**
 * FAQ accordion.
 *
 * Native <details> can't be eased open — the browser snaps it — so this is a
 * button + panel pair animating grid-template-rows 0fr → 1fr. The answer stays
 * in the DOM whether open or closed, so find-in-page still reaches it; only the
 * row track collapses.
 */
import { ref, useId } from 'vue'

import Icon from '@/components/ui/Icon.vue'
import Reveal from './Reveal.vue'
import SectionHeading from './SectionHeading.vue'

const QUESTIONS = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6']

const uid = useId()
// Open one at a time: with six of them, letting every panel stay open turns the
// section into a wall of text and loses the scannable list of questions.
const open = ref('')
const toggle = (key) => (open.value = open.value === key ? '' : key)
</script>

<template>
  <section id="faq" class="scroll-mt-28 px-6 py-16 sm:py-24">
    <div class="mx-auto max-w-3xl">
      <Reveal>
        <SectionHeading :eyebrow="$t('landing.faq.eyebrow')" :title="$t('landing.faq.title')" />
      </Reveal>

      <div class="mt-10 space-y-3 sm:mt-14">
        <Reveal v-for="(key, i) in QUESTIONS" :key="key" :delay="i * 50">
          <div
            class="card overflow-hidden px-6 transition-colors duration-200"
            :class="open === key ? 'border-brand-200 dark:border-brand-500/30' : ''"
          >
            <h3>
              <button
                :id="`${uid}-${key}-btn`"
                type="button"
                :aria-expanded="open === key"
                :aria-controls="`${uid}-${key}`"
                class="flex w-full cursor-pointer items-center justify-between gap-4 py-5 text-left text-sm font-bold text-slate-900 transition-colors hover:text-brand-600 dark:text-white dark:hover:text-brand-400"
                @click="toggle(key)"
              >
                {{ $t(`landing.faq.${key}.q`) }}
                <span
                  class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-all duration-300"
                  :class="
                    open === key
                      ? 'rotate-180 bg-brand-600 text-white'
                      : 'bg-slate-100 text-slate-400 dark:bg-surface-2'
                  "
                >
                  <Icon name="chevronDown" class="h-4 w-4" />
                </span>
              </button>
            </h3>

            <div
              :id="`${uid}-${key}`"
              role="region"
              :aria-labelledby="`${uid}-${key}-btn`"
              class="zx-disclosure"
              :class="open === key ? 'zx-disclosure-open' : ''"
            >
              <div>
                <p class="pb-5 pr-10 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                  {{ $t(`landing.faq.${key}.a`) }}
                </p>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </div>
  </section>
</template>
