<script setup>
/**
 * Roadmap block on My Startup: a glance at the road (stage, how far along,
 * the stop to do now) with the way into the full map (views/StartupRoadmap).
 * Building, the AI's questions and ticking stops off all happen on the map.
 */
import { computed, onMounted, ref } from 'vue'

import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import BlockCard from './BlockCard.vue'
import { getRoadmap } from '@/api/startup'

const roadmap = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    roadmap.value = (await getRoadmap()).roadmap
  } catch {
    roadmap.value = null
  } finally {
    loading.value = false
  }
})

const items = computed(() =>
  (roadmap.value?.phases || []).flatMap((p) => [
    ...p.steps.map((s) => ({ ...s, kind: 'step', phase: p })),
    { ...p, kind: 'milestone', phase: p },
  ]),
)
const open = computed(() => items.value.filter((i) => !i.already_done))
const done = computed(() => open.value.filter((i) => i.done).length)
const pct = computed(() => (open.value.length ? (100 * done.value) / open.value.length : 0))
const current = computed(() => items.value.find((i) => !i.done) || null)
const phaseNo = computed(() => (current.value ? (roadmap.value.phases.filter((p) => !p.already_done).indexOf(current.value.phase) + 1) : 0))
</script>

<template>
  <BlockCard icon="map" :title="$t('roadmap.title')" :subtitle="$t('roadmap.subtitle')">
    <LoadingSkeleton v-if="loading" height="h-28" rounded="rounded-2xl" />

    <div v-else-if="!roadmap" class="rounded-2xl bg-slate-50 p-4 dark:bg-surface-2">
      <p class="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{{ $t('roadmap.intro') }}</p>
      <RouterLink
        :to="{ name: 'startupRoadmap', query: { start: 1 } }"
        class="pill mt-4 inline-flex min-h-11 items-center gap-2 bg-brand-600 px-5 text-sm font-semibold text-white hover:bg-brand-700"
      >
        <Icon name="sparkles" class="h-4 w-4" />{{ $t('roadmap.build') }}
      </RouterLink>
    </div>

    <template v-else>
      <div class="flex flex-wrap items-center gap-2">
        <PillBadge color="brand" variant="solid" size="sm">{{ $t(`roadmap.stage_${roadmap.position?.stage || 'idea'}`) }}</PillBadge>
        <p class="min-w-0 flex-1 truncate text-sm font-bold text-slate-900 dark:text-white">{{ roadmap.position?.headline }}</p>
      </div>
      <div class="mt-3">
        <div class="mb-1.5 flex items-center justify-between text-xs font-semibold text-slate-500">
          <span>{{ $t('roadmap.progress', { done, total: open.length }) }}</span>
          <span>{{ Math.round(pct) }}%</span>
        </div>
        <ProgressBar :value="pct" />
      </div>
      <RouterLink
        :to="{ name: 'startupRoadmap' }"
        class="mt-3 flex items-center gap-3 rounded-2xl border border-slate-200 p-3 transition hover:border-brand-300 hover:shadow-sm dark:border-hairline"
      >
        <span
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white"
          :class="!current ? 'bg-amber-400' : current.kind === 'milestone' ? 'bg-amber-500' : 'bg-brand-600'"
        >
          <Icon :name="!current ? 'trophy' : current.kind === 'milestone' ? 'flag' : 'play'" class="h-5 w-5" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="block text-[11px] font-bold uppercase tracking-wide text-brand-600 dark:text-brand-300">
            {{ current ? `${$t('roadmap.now')} · ${$t('roadmap.phaseN', { n: phaseNo })}` : $t('roadmap.finaleTitle') }}
          </span>
          <span class="block text-sm font-semibold leading-snug text-slate-800 dark:text-ink">
            {{ !current ? $t('roadmap.finaleDone') : current.kind === 'milestone' ? current.milestone.title : current.title }}
          </span>
        </span>
        <Icon name="chevronRight" class="h-4 w-4 shrink-0 text-slate-400" />
      </RouterLink>
    </template>
  </BlockCard>
</template>
