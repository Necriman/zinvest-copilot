<script setup>
/**
 * Study plan — one continuous Duolingo-style map.
 *
 * Every unit is stacked in order and you simply keep scrolling to reach the
 * next one; the pill strip at the top is a *position indicator* that tracks
 * where you are, not a tab switcher (clicking one scrolls there rather than
 * swapping the view out).
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import StudyPlanPath from '@/components/study/StudyPlanPath.vue'
import UnitScenery from '@/components/study/UnitScenery.vue'
import { sceneryFor } from '@/components/study/scenery'
import BearAvatar from '@/components/mascot/BearAvatar.vue'
import { accentOf } from '@/components/study/accents'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import { getFullStudyPlan } from '@/api/units'
import { isReturning } from '@/router/navScroll'
import { readCache, writeCache } from '@/utils/viewCache'

const route = useRoute()
const router = useRouter()

// Whether this visit is the trip back out of a lesson. Read during setup on
// purpose: the router consumes the flag a tick later, so by the time the plan
// request lands this would already look like a fresh visit.
const returning = isReturning(route.fullPath)

// Start from the last payload when there is one — on a return trip there always
// is, so the map paints at its real height on the first frame and the restored
// scroll offset has somewhere to land.
const plan = ref(readCache('studyPlan'))
const loading = ref(!plan.value)
const error = ref('')
const activeId = ref(null)

const units = computed(() => plan.value?.units || [])

// section id -> element, for the observer and for jump-scrolling.
const sectionEls = new Map()
function setSection(id, el) {
  if (el) sectionEls.set(id, el)
  else sectionEls.delete(id)
}

function unitStats(entry) {
  const lessons = entry.nodes.filter((n) => n.kind === 'lesson')
  return { total: lessons.length, done: lessons.filter((n) => n.state === 'completed').length }
}

// --- progress since the last visit -----------------------------------------
// The cache holds the map as the learner last saw it. Comparing the fresh plan
// with it tells each unit what moved: how many stops were completed since, and
// which stop became current. The path then draws that stretch in and the new
// stop pops up — finishing a lesson and coming back shows the step being taken
// instead of a map that has silently changed.
const motion = ref({})

function leadingDone(nodes) {
  let count = 0
  for (const node of nodes) {
    if (node.state !== 'completed') break
    count++
  }
  return count
}

function progressSince(before, after) {
  const seen = new Map((before?.units || []).map((entry) => [entry.unit.id, entry]))
  const moved = {}
  for (const entry of after?.units || []) {
    const old = seen.get(entry.unit.id)
    if (!old) continue
    const gained = Math.max(0, leadingDone(entry.nodes) - leadingDone(old.nodes))
    const now = entry.nodes.find((n) => n.state === 'current')
    const was = old.nodes.find((n) => n.state === 'current')
    const freshId = now && now.id !== was?.id ? now.id : null
    if (gained || freshId) moved[entry.unit.id] = { gained, freshId }
  }
  return moved
}

async function load() {
  error.value = ''
  try {
    const fresh = await getFullStudyPlan()
    motion.value = plan.value ? progressSince(plan.value, fresh) : {}
    plan.value = fresh
    writeCache('studyPlan', plan.value)
  } catch (e) {
    // A failed background refresh must not replace a map we can still show.
    if (!plan.value) error.value = e?.response?.data?.detail || 'generic'
  } finally {
    loading.value = false
  }
}

// --- scroll tracking -------------------------------------------------------
// `settling` marks the window during which WE are moving the page. The observer
// ignores that window, so the sections flying past a jump don't rewrite the URL
// (and fight the scroll) on the way.
let observer = null
let settleTimer = null
let settling = false
let restoration = null

function setActive(id, writeUrl = true) {
  if (!id || id === activeId.value) return
  activeId.value = id
  if (writeUrl && id !== route.query.unit) {
    router.replace({ query: { ...route.query, unit: id } })
  }
}

function observeSections() {
  observer?.disconnect()
  observer = new IntersectionObserver(
    (entries) => {
      if (settling) return
      // The unit whose section occupies the upper band of the viewport wins.
      const visible = entries
        .filter((e) => e.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)
      if (visible[0]) setActive(visible[0].target.dataset.unitId)
    },
    { rootMargin: '-96px 0px -55% 0px', threshold: [0, 0.15, 0.5] },
  )
  sectionEls.forEach((el) => observer.observe(el))
}

function scrollToUnit(id, smooth = true) {
  const el = sectionEls.get(id)
  if (!el) return
  settling = true
  clearTimeout(settleTimer)
  setActive(id)
  el.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' })
  settleTimer = setTimeout(() => {
    settling = false
  }, smooth ? 600 : 120)
}

onMounted(() => {
  // Stop the browser restoring its own scroll position on reload — it would
  // land somewhere, then our deep-link jump would move again: the jitter.
  if ('scrollRestoration' in history) {
    restoration = history.scrollRestoration
    history.scrollRestoration = 'manual'
  }
  // A warm cache means the units are already here, so the watcher below will
  // never fire for them — position from here instead.
  positionOnce()
  load()
})
onBeforeUnmount(() => {
  observer?.disconnect()
  clearTimeout(settleTimer)
  if (restoration) history.scrollRestoration = restoration
})

// Runs once per visit. The background refresh replaces `plan` and so re-fires
// the watcher; re-positioning then would move the map out from under whoever is
// already reading it.
let positioned = false
async function positionOnce() {
  if (positioned || !units.value.length) return
  positioned = true
  await nextTick()
  const deepLink = route.query.unit && sectionEls.has(route.query.unit) ? route.query.unit : null
  // Two frames: let fonts, the sticky bar and the SVG tracks lay out before
  // measuring, so the jump lands right first time instead of correcting itself.
  requestAnimationFrame(() =>
    requestAnimationFrame(() => {
      // On the way back out of a lesson the router has already restored the
      // exact offset the map was left at — jumping to the top of a unit on top
      // of that is the lurch. The observer picks the right pill up on its own
      // as soon as it starts watching.
      if (!returning) {
        // Instant, not smooth — on load there is nothing to animate *from*.
        if (deepLink) scrollToUnit(deepLink, false)
        else setActive(units.value[0].unit.id, false)
      }
      observeSections() // observe only once we're in position
    }),
  )
}
watch(units, positionOnce)

function onSelect(node) {
  if (node.kind === 'test') {
    router.push({ name: 'unitTest', params: { unitId: node.id } })
    return
  }
  router.push({ name: 'lesson', params: { lessonId: node.id } })
}
</script>

<template>
  <div>
    <div class="mb-5">
      <h1 class="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
        {{ $t('study.title') }}
      </h1>
      <p class="mt-1 text-sm text-slate-500">{{ $t('study.scrollHint') }}</p>
    </div>

    <!-- Nudge toward the assessment while the plan is still the generic one. -->
    <RouterLink
      v-if="!loading && plan && plan.source !== 'ai'"
      :to="{ name: 'onboarding' }"
      class="mb-4 flex items-center gap-3 rounded-2xl border border-brand-100 bg-brand-50/60 px-4 py-3 transition hover:bg-brand-50 dark:border-brand-500/20 dark:bg-brand-500/10 dark:hover:bg-brand-500/20"
    >
      <BearAvatar name="tablet" class="h-10 w-10" />
      <span class="min-w-0 flex-1">
        <span class="block text-sm font-semibold text-brand-800 dark:text-brand-200">
          {{ $t('study.personaliseTitle') }}
        </span>
        <span class="block text-xs text-brand-700/80 dark:text-brand-300/80">
          {{ $t('study.personaliseBody') }}
        </span>
      </span>
      <Icon name="chevronRight" class="h-4 w-4 shrink-0 text-brand-600" />
    </RouterLink>

    <p
      v-else-if="!loading && plan?.rationale"
      class="mb-4 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:bg-surface-2/50 dark:text-slate-300"
    >
      {{ plan.rationale }}
    </p>

    <!-- Position indicator: follows the scroll, and doubles as a jump control. -->
    <div
      v-if="units.length"
      class="sticky top-16 z-20 -mx-2 mb-4 flex gap-2 overflow-x-auto bg-canvas/85 px-2 py-2 backdrop-blur dark:bg-slate-950/70"
    >
      <button
        v-for="entry in units"
        :key="entry.unit.id"
        type="button"
        class="pill shrink-0 gap-1.5 px-3.5 py-1.5 text-xs font-semibold transition"
        :class="
          entry.unit.id === activeId
            ? `${accentOf(entry.unit.color).soft} shadow-sm`
            : 'bg-white text-slate-500 hover:bg-slate-50 dark:bg-surface dark:text-slate-400 dark:hover:bg-surface-2 dark:hover:text-slate-200'
        "
        :title="`${entry.unit.code} · ${entry.unit.title}`"
        @click="scrollToUnit(entry.unit.id)"
      >
        <Icon v-if="entry.unit.icon" :name="entry.unit.icon" class="h-3.5 w-3.5" />
        {{ entry.unit.code }}
        <Icon v-if="entry.unit.locked" name="lock" class="h-3 w-3 opacity-70" />
      </button>
    </div>

    <div v-if="loading" class="card p-6">
      <LoadingSkeleton height="h-96" rounded="rounded-2xl" />
    </div>

    <p v-else-if="error" class="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10">
      {{ $t('errors.generic') }}
    </p>

    <div v-else class="card overflow-hidden">
      <section
        v-for="(entry, i) in units"
        :key="entry.unit.id"
        :ref="(el) => setSection(entry.unit.id, el)"
        :data-unit-id="entry.unit.id"
        class="scroll-mt-32"
        :class="i > 0 ? 'border-t border-slate-100 dark:border-hairline' : ''"
      >
        <!-- Category banner: each unit gets its own accent + icon so the four
             categories read as different places, not repeats of one. -->
        <div class="relative z-10 flex items-center gap-3 px-6 pb-2 pt-7">
          <!-- The unit's emblem: the first object of its scenery, so the
               header already says which world this is — and on a phone, where
               the margins are too narrow for the scenery, it is the scenery. -->
          <img
            v-if="sceneryFor(entry.unit.slug)"
            :src="sceneryFor(entry.unit.slug).emblem"
            alt=""
            aria-hidden="true"
            loading="lazy"
            decoding="async"
            draggable="false"
            class="h-12 w-12 shrink-0 object-contain drop-shadow-[0_6px_8px_rgb(15_23_42_/_0.14)]"
            :class="entry.unit.locked ? 'opacity-60 grayscale' : ''"
          />
          <span
            v-else
            class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl"
            :class="
              entry.unit.locked
                ? 'bg-slate-100 text-slate-400 dark:bg-surface-2'
                : accentOf(entry.unit.color).soft
            "
          >
            <Icon :name="entry.unit.icon || 'book'" class="h-5 w-5" />
          </span>
          <div class="min-w-0 flex-1">
            <p class="flex items-center gap-2">
              <span
                class="text-[11px] font-extrabold tracking-widest"
                :class="entry.unit.locked ? 'text-slate-400' : accentOf(entry.unit.color).ink"
              >
                {{ entry.unit.code }}
              </span>
              <span class="truncate text-base font-bold tracking-tight text-slate-900 dark:text-white">
                {{ entry.unit.title }}
              </span>
            </p>
            <p class="truncate text-xs text-slate-500">
              {{ entry.unit.locked ? $t('study.unitLocked') : entry.unit.subtitle }}
            </p>
            <!-- How far through this unit, in its own colour — the same bar the
                 Today card shows for the unit the learner is in. -->
            <div v-if="!entry.unit.locked && unitStats(entry).total" class="mt-2 flex items-center gap-2.5">
              <span class="h-1.5 max-w-[11rem] flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-surface-2">
                <span
                  class="block h-full rounded-full transition-[width] duration-700 ease-out"
                  :class="accentOf(entry.unit.color).fill"
                  :style="{ width: (100 * unitStats(entry).done) / unitStats(entry).total + '%' }"
                />
              </span>
              <span class="shrink-0 text-[11px] font-semibold tabular-nums text-slate-400">
                {{ $t('studyV2.unitLessons', { done: unitStats(entry).done, total: unitStats(entry).total }) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Dimmed, but not so far that the unit's accent stops reading. The
             scenery sits behind the path in the same box. -->
        <div class="relative" :class="entry.unit.locked ? 'opacity-80' : ''">
          <UnitScenery :slug="entry.unit.slug || ''" :accent="entry.unit.color" :locked="entry.unit.locked" />
          <StudyPlanPath
            :nodes="entry.nodes"
            :accent="entry.unit.color"
            :variant="i"
            :gained="motion[entry.unit.id]?.gained || 0"
            :fresh-id="motion[entry.unit.id]?.freshId || null"
            @select="onSelect"
          />
        </div>
      </section>
    </div>
  </div>
</template>
