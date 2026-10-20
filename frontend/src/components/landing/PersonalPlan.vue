<script setup>
/**
 * "A study plan made only for you" — the personalisation pitch, with a mock of
 * the real study path beside it. The mock deliberately shows a reordered plan
 * (compounding pulled ahead of index funds) and the AI's stated reason, because
 * that reason string is the thing that makes the plan feel personal.
 */
import { computed } from 'vue'

import AppButton from '@/components/ui/AppButton.vue'
import Icon from '@/components/ui/Icon.vue'
import Reveal from './Reveal.vue'
import SectionHeading from './SectionHeading.vue'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const startTo = computed(() => (auth.isAuthenticated ? { name: 'studyPlan' } : { name: 'register' }))

const POINTS = [
  { key: 'b1', icon: 'target' },
  { key: 'b2', icon: 'comment' },
  { key: 'b3', icon: 'undo' },
  { key: 'b4', icon: 'book' },
]

const NODES = [
  { title: 'What is money?', unit: '01', state: 'done' },
  { title: 'Assets vs. liabilities', unit: '01', state: 'done' },
  { title: 'The power of compounding', unit: '02', state: 'current' },
  { title: 'Index funds & ETFs', unit: '02', state: 'todo' },
  { title: 'Risk and return', unit: '02', state: 'todo' },
]
</script>

<template>
  <section id="learning-paths" class="scroll-mt-28 px-6 py-16 sm:py-24">
    <div class="mx-auto grid max-w-6xl items-center gap-10 sm:gap-14 lg:grid-cols-2">
      <!-- Copy -->
      <div>
        <Reveal>
          <SectionHeading
            align="left"
            :eyebrow="$t('landing.plan.eyebrow')"
            :title="$t('landing.plan.title')"
            :subtitle="$t('landing.plan.subtitle')"
          />
        </Reveal>

        <dl class="mt-10 space-y-6">
          <Reveal v-for="(point, i) in POINTS" :key="point.key" :delay="i * 70">
            <div class="flex gap-4">
              <div
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300"
              >
                <Icon :name="point.icon" class="h-4 w-4" />
              </div>
              <div>
                <dt class="text-sm font-bold text-slate-900 dark:text-white">
                  {{ $t(`landing.plan.${point.key}.title`) }}
                </dt>
                <dd class="mt-1 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                  {{ $t(`landing.plan.${point.key}.body`) }}
                </dd>
              </div>
            </div>
          </Reveal>
        </dl>

        <Reveal :delay="300">
          <AppButton :to="startTo" class="mt-10" icon-right="arrowRight">
            {{ $t('landing.plan.cta') }}
          </AppButton>
        </Reveal>
      </div>

      <!-- Plan mock -->
      <Reveal :delay="120">
        <div class="card relative p-6 shadow-float sm:p-8">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <span
                class="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-600 text-white"
              >
                <Icon name="map" class="h-4 w-4" />
              </span>
              <span class="text-sm font-extrabold text-slate-900 dark:text-white">
                {{ $t('landing.plan.mockTitle') }}
              </span>
            </div>
            <span
              class="pill bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-700 dark:bg-violet-500/15 dark:text-violet-300"
            >
              <Icon name="target" class="h-3.5 w-3.5" />
              {{ $t('landing.plan.mockLevel') }}
            </span>
          </div>

          <ol class="mt-7 space-y-1">
            <li v-for="(node, i) in NODES" :key="node.title" class="flex gap-4">
              <!-- Rail: dot + the connector down to the next dot -->
              <div class="flex flex-col items-center">
                <span
                  class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white"
                  :class="{
                    'bg-emerald-500': node.state === 'done',
                    'bg-brand-600 ring-4 ring-brand-500/25': node.state === 'current',
                    'bg-slate-100 dark:bg-surface-2': node.state === 'todo',
                  }"
                >
                  <Icon v-if="node.state === 'done'" name="check" class="h-4 w-4" />
                  <Icon v-else-if="node.state === 'current'" name="play" class="h-3.5 w-3.5" />
                  <span v-else class="text-xs font-bold text-slate-400">{{ i + 1 }}</span>
                </span>
                <span
                  v-if="i < NODES.length - 1"
                  class="w-0.5 flex-1"
                  :class="node.state === 'done' ? 'bg-emerald-500/40' : 'bg-slate-200 dark:bg-surface-2'"
                />
              </div>

              <div class="min-w-0 flex-1 pb-4">
                <div class="flex items-center gap-2">
                  <p
                    class="truncate text-sm font-semibold"
                    :class="
                      node.state === 'todo'
                        ? 'text-slate-400'
                        : 'text-slate-900 dark:text-white'
                    "
                  >
                    {{ node.title }}
                  </p>
                  <span class="shrink-0 text-[11px] font-bold text-slate-300 dark:text-slate-600">
                    {{ node.unit }}
                  </span>
                </div>
                <p
                  v-if="node.state === 'done'"
                  class="mt-0.5 text-xs font-medium text-emerald-600 dark:text-emerald-400"
                >
                  {{ $t('landing.plan.mockDone') }}
                </p>
                <p
                  v-else-if="node.state === 'current'"
                  class="mt-0.5 text-xs font-medium text-brand-600 dark:text-brand-400"
                >
                  {{ $t('landing.plan.mockCurrent') }}
                </p>

                <!-- The reason string is the whole point of the section. -->
                <div
                  v-if="node.state === 'current'"
                  class="mt-3 rounded-2xl border border-brand-100 bg-brand-50/60 p-3.5 dark:border-brand-500/20 dark:bg-brand-500/10"
                >
                  <p
                    class="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.12em] text-brand-700 dark:text-brand-300"
                  >
                    <Icon name="map" class="h-3 w-3" />
                    {{ $t('landing.plan.mockWhy') }}
                  </p>
                  <p class="mt-1.5 text-xs leading-relaxed text-brand-900/80 dark:text-brand-100/80">
                    {{ $t('landing.plan.mockReason') }}
                  </p>
                </div>
              </div>
            </li>
          </ol>
        </div>
      </Reveal>
    </div>
  </section>
</template>
