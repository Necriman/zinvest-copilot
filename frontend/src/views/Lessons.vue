<script setup>
/**
 * Lessons — the open catalogue.
 *
 * Every lesson in the course, grouped by unit and openable in any order. This
 * is the counterpart to the study plan: the plan is the *recommended* linear
 * route, this is "go read whatever you like".
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import EmptyState from '@/components/ui/EmptyState.vue'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import SearchField from '@/components/ui/SearchField.vue'
import { listLessons } from '@/api/units'
import { readCache, writeCache } from '@/utils/viewCache'

const router = useRouter()

// Start from the last payload if there is one. Coming back from a lesson this
// is always warm, so the catalogue paints at its full height immediately and the
// restored scroll offset has somewhere to land.
const units = ref(readCache('lessons') || [])
const loading = ref(!units.value.length)
const error = ref('')
const query = ref('')

onMounted(async () => {
  try {
    units.value = (await listLessons()).units
    writeCache('lessons', units.value)
  } catch (e) {
    // A failed background refresh must not replace a list we can still show.
    if (!units.value.length) error.value = e?.response?.data?.detail || 'generic'
  } finally {
    loading.value = false
  }
})

const visible = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return units.value
  return units.value
    .map((u) => ({ ...u, lessons: u.lessons.filter((l) => l.title.toLowerCase().includes(q)) }))
    .filter((u) => u.lessons.length)
})

const STATUS_ICON = { completed: 'check', in_progress: 'play', not_started: 'book' }

function open(lesson) {
  router.push({ name: 'lesson', params: { lessonId: lesson.id } })
}
</script>

<template>
  <div>
    <div class="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {{ $t('nav.lessons') }}
        </h1>
        <p class="mt-1 text-sm text-slate-500">{{ $t('lessons.browseHint') }}</p>
      </div>
      <SearchField
        v-model="query"
        class="w-full sm:w-56"
        :placeholder="$t('lessons.search')"
        :clear-label="$t('common.clearSearch')"
      />
    </div>

    <div v-if="loading" class="space-y-4">
      <LoadingSkeleton v-for="n in 3" :key="n" height="h-40" rounded="rounded-3xl" />
    </div>

    <p v-else-if="error" class="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10">
      {{ $t('errors.generic') }}
    </p>

    <EmptyState
      v-else-if="!visible.length"
      bear="confused"
      :title="$t('lessons.noMatches')"
      :message="$t('notes.noMatchesHint')"
    />

    <div v-else class="space-y-4">
      <section v-for="unit in visible" :key="unit.id" class="card overflow-hidden">
        <div class="flex items-center gap-3 border-b border-slate-100 px-5 py-4 dark:border-hairline">
          <span
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-sm font-extrabold text-brand-700 dark:bg-brand-500/15 dark:text-brand-300"
          >
            {{ unit.code }}
          </span>
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-bold text-slate-900 dark:text-white">{{ unit.title }}</p>
            <p class="truncate text-xs text-slate-500">{{ unit.subtitle }}</p>
          </div>
          <div class="hidden w-28 shrink-0 sm:block">
            <ProgressBar :value="unit.lessons_total ? (unit.lessons_completed / unit.lessons_total) * 100 : 0" />
            <p class="mt-1 text-right text-[11px] tabular-nums text-slate-400">
              {{ unit.lessons_completed }}/{{ unit.lessons_total }}
            </p>
          </div>
        </div>

        <ul class="divide-y divide-slate-100 dark:divide-hairline">
          <li v-for="lesson in unit.lessons" :key="lesson.id">
            <button
              type="button"
              class="flex w-full items-center gap-3 px-5 py-3 text-left transition hover:bg-slate-50 dark:hover:bg-surface-2"
              @click="open(lesson)"
            >
              <span
                class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
                :class="
                  lesson.status === 'completed'
                    ? 'bg-brand-600 text-white'
                    : lesson.status === 'in_progress'
                      ? 'bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300'
                      : 'bg-slate-100 text-slate-400 dark:bg-surface-2'
                "
              >
                <Icon :name="STATUS_ICON[lesson.status]" class="h-3.5 w-3.5" />
              </span>

              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                  {{ lesson.title }}
                </span>
                <span class="mt-0.5 flex items-center gap-3 text-xs text-slate-400">
                  <span>{{ $t('lessons.minutes', { n: lesson.estimated_minutes }) }}</span>
                  <span class="flex items-center gap-1">
                    <Icon name="coin" class="h-3 w-3" />{{ lesson.coin_reward }}
                  </span>
                </span>
              </span>

              <Icon name="chevronRight" class="h-4 w-4 shrink-0 text-slate-300" />
            </button>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
