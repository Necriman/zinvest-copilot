<script setup>
/**
 * Stylised shot of the dashboard, drawn in DOM rather than shipped as an image
 * so it re-tints with the brand colour and the dark theme like the real thing.
 * Decorative only — hidden from assistive tech, since everything it says is
 * already in the surrounding copy.
 */
import Icon from '@/components/ui/Icon.vue'
import BrandMark from '@/components/ui/BrandMark.vue'

// Labels go through i18n like the real chrome they're imitating — an English
// mock sitting under Russian copy reads as a screenshot someone forgot to swap.
const STATS = [
  { icon: 'coin', value: '1,240', label: 'common.coins', tone: 'text-amber-500' },
  { icon: 'flame', value: '12', label: 'common.streak', tone: 'text-orange-500' },
  { icon: 'trophy', value: '68%', label: 'common.progress', tone: 'text-emerald-500' },
]

const SIDEBAR = [
  { icon: 'map', label: 'nav.studyPlan' },
  { icon: 'book', label: 'nav.lessons' },
  { icon: 'note', label: 'nav.notes' },
  { icon: 'bot', label: 'nav.zinvestAI' },
]

// Node states down the mock study path: done → done → current → locked.
const NODES = ['done', 'done', 'current', 'todo', 'todo']
</script>

<template>
  <div aria-hidden="true" class="select-none">
    <div class="card overflow-hidden shadow-float">
      <!-- Window chrome -->
      <div
        class="flex items-center gap-2 border-b border-hairline bg-slate-50/80 px-4 py-3 dark:bg-surface-2/60"
      >
        <span class="h-2.5 w-2.5 rounded-full bg-red-400/80" />
        <span class="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
        <span class="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
        <div
          class="ml-3 hidden flex-1 rounded-full bg-white px-3 py-1 text-[11px] text-slate-400 sm:block dark:bg-surface"
        >
          zinvest.app/app
        </div>
      </div>

      <div class="flex">
        <!-- Sidebar sliver -->
        <div class="hidden w-36 shrink-0 border-r border-hairline p-3 sm:block">
          <div class="mb-4 flex items-center gap-2">
            <BrandMark class="h-5 w-5 rounded-md" />
            <span class="text-xs font-extrabold tracking-tight text-slate-900 dark:text-white">
              Zinvest
            </span>
          </div>
          <div
            class="mb-1 flex items-center gap-2 truncate rounded-lg bg-brand-50 px-2 py-1.5 text-[11px] font-semibold text-brand-700 dark:bg-brand-500/15 dark:text-brand-300"
          >
            <Icon name="home" class="h-3 w-3 shrink-0" />
            <span class="truncate">{{ $t('nav.today') }}</span>
          </div>
          <div
            v-for="item in SIDEBAR"
            :key="item.label"
            class="mb-1 flex items-center gap-2 px-2 py-1.5 text-[11px] font-medium text-slate-400"
          >
            <Icon :name="item.icon" class="h-3 w-3 shrink-0" />
            <span class="truncate">{{ $t(item.label) }}</span>
          </div>
        </div>

        <!-- Main column -->
        <div class="min-w-0 flex-1 p-4">
          <div class="mb-3 h-2.5 w-32 rounded-full bg-slate-200 dark:bg-surface-2" />

          <div class="mb-4 grid grid-cols-3 gap-2">
            <div
              v-for="stat in STATS"
              :key="stat.label"
              class="rounded-xl border border-hairline p-2.5"
            >
              <Icon :name="stat.icon" class="h-3.5 w-3.5" :class="stat.tone" />
              <p class="mt-1.5 text-sm font-extrabold text-slate-900 dark:text-white">
                {{ stat.value }}
              </p>
              <p class="truncate text-[10px] text-slate-400">{{ $t(stat.label) }}</p>
            </div>
          </div>

          <!-- Study path snippet -->
          <div class="rounded-xl border border-hairline p-3">
            <div class="mb-3 flex items-center justify-between gap-2">
              <span class="truncate text-[11px] font-bold text-slate-700 dark:text-slate-200">
                {{ $t('landing.curriculum.u2.title') }}
              </span>
              <span
                class="rounded-full bg-sky-50 px-2 py-0.5 text-[10px] font-semibold text-sky-700 dark:bg-sky-500/15 dark:text-sky-300"
              >
                02
              </span>
            </div>
            <div class="flex items-center">
              <template v-for="(node, i) in NODES" :key="i">
                <span
                  v-if="i > 0"
                  class="h-0.5 flex-1"
                  :class="node === 'todo' ? 'bg-slate-200 dark:bg-surface-2' : 'bg-sky-400'"
                />
                <span
                  class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-white"
                  :class="{
                    'bg-sky-500': node === 'done',
                    'bg-brand-600 ring-4 ring-brand-500/25': node === 'current',
                    'bg-slate-200 dark:bg-surface-2': node === 'todo',
                  }"
                >
                  <Icon v-if="node === 'done'" name="check" class="h-3 w-3" />
                  <Icon v-else-if="node === 'current'" name="play" class="h-3 w-3" />
                  <Icon v-else name="lock" class="h-2.5 w-2.5 text-slate-400" />
                </span>
              </template>
            </div>
          </div>
        </div>

        <!-- Right rail sliver -->
        <div class="hidden w-32 shrink-0 border-l border-hairline p-3 lg:block">
          <div class="mb-2 h-2 w-16 rounded-full bg-slate-200 dark:bg-surface-2" />
          <div class="mb-3 grid grid-cols-7 gap-1">
            <span
              v-for="d in 7"
              :key="d"
              class="h-4 rounded"
              :class="d <= 5 ? 'bg-brand-500' : 'bg-slate-200 dark:bg-surface-2'"
            />
          </div>
          <div class="mb-2 h-2 w-20 rounded-full bg-slate-200 dark:bg-surface-2" />
          <div v-for="t in 3" :key="t" class="mb-1.5 flex items-center gap-1.5">
            <span
              class="h-3 w-3 shrink-0 rounded-[4px] border"
              :class="
                t === 1
                  ? 'border-brand-600 bg-brand-600'
                  : 'border-slate-300 dark:border-hairline'
              "
            />
            <span class="h-1.5 flex-1 rounded-full bg-slate-200 dark:bg-surface-2" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
