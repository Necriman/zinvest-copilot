<script setup>
/**
 * Startup roadmap — the road from where the startup stands to a full startup,
 * drawn like the study plan: each phase is a stretch of winding path whose
 * stops are steps, ending in a checkpoint (the phase's milestone); the bear
 * waits by the stop to do next, and the finish line is "a full startup".
 *
 * Building one: the AI first asks what it cannot tell from the workspace (is
 * there an MVP, has anyone paid yet…), the founder answers what they can, and
 * the map branches on those answers. Phases follow the stages of a startup
 * playbook (backend startup/playbook.py); a step can show how a real startup
 * did something similar and the mistake founders usually make there. Stops are done strictly in order; a done
 * stop can carry a short note that the AI reads when the map is rebuilt.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import AiAvatar from '@/components/ai/AiAvatar.vue'
import BearSticker from '@/components/mascot/BearSticker.vue'
import StudyPlanPath from '@/components/study/StudyPlanPath.vue'
import UnitScenery from '@/components/study/UnitScenery.vue'
import { accentOf } from '@/components/study/accents'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import {
  askRoadmapQuestions,
  buildRoadmap,
  createStartupTodo,
  getRoadmap,
  listStartupTodos,
  setRoadmapItem,
} from '@/api/startup'

const { t, locale } = useI18n()
const route = useRoute()

const ACCENTS = ['brand', 'invest', 'budget', 'cash', 'startup', 'risk']
const accentKey = (i) => ACCENTS[i % ACCENTS.length]

const roadmap = ref(null)
const loading = ref(true)
const mode = ref('map') // map | asking | questions | building
const questions = ref([])
const answers = reactive({}) // question id -> { choice, text }
const error = ref('')
const quota = ref(null)
const motion = ref({}) // phase id -> { gained, freshId }
const todoTitles = ref(new Set())

// --- the sequence ------------------------------------------------------------
const phases = computed(() => roadmap.value?.phases || [])
const behind = computed(() => phases.value.filter((p) => p.already_done))
const ahead = computed(() => phases.value.filter((p) => !p.already_done))
const items = computed(() =>
  phases.value.flatMap((p) => [
    ...p.steps.map((s) => ({ ...s, kind: 'step', phase: p })),
    { ...p, kind: 'milestone', phase: p },
  ]),
)
const currentIndex = computed(() => items.value.findIndex((i) => !i.done))
const finished = computed(() => items.value.length > 0 && currentIndex.value === -1)
const current = computed(() => items.value[currentIndex.value] || null)
const indexOf = (id) => items.value.findIndex((i) => i.id === id)
function stateOf(id) {
  const i = indexOf(id)
  if (items.value[i]?.done) return 'completed'
  return i === currentIndex.value ? 'current' : 'locked'
}
const openSteps = computed(() => items.value.filter((i) => !i.already_done))
const doneCount = computed(() => openSteps.value.filter((i) => i.done).length)
const pct = computed(() => (openSteps.value.length ? (100 * doneCount.value) / openSteps.value.length : 0))

const behindNodes = computed(() =>
  behind.value.map((p) => ({ id: p.id, kind: 'test', label: p.milestone.title, icon: 'flag', state: 'completed' })),
)
function nodesOf(phase) {
  return [
    ...phase.steps.map((s) => ({ id: s.id, kind: 'lesson', title: s.title, reason: s.why, state: stateOf(s.id), peek: true })),
    { id: phase.id, kind: 'test', label: phase.milestone.title, icon: 'flag', state: stateOf(phase.id), peek: true },
  ]
}
const phaseStats = (phase) => ({ done: phase.steps.filter((s) => s.done).length + (phase.done ? 1 : 0), total: phase.steps.length + 1 })

const position = computed(() => roadmap.value?.position || {})
const otherLanguage = computed(() => roadmap.value?.language && roadmap.value.language !== locale.value)
const fmtDate = (iso) =>
  iso ? new Intl.DateTimeFormat(locale.value === 'uz' ? 'uz-Latn' : locale.value, { day: 'numeric', month: 'long' }).format(new Date(iso)) : ''

// --- loading, questions, building ---------------------------------------------
onMounted(async () => {
  try {
    const [res, todos] = await Promise.all([getRoadmap(), listStartupTodos().catch(() => null)])
    roadmap.value = res.roadmap
    todoTitles.value = new Set((todos?.todos || []).map((x) => x.title.trim().toLowerCase()))
  } catch (e) {
    error.value = e?.response?.data?.detail || t('errors.generic')
  } finally {
    loading.value = false
  }
  if (!roadmap.value && route.query.start) startQuestions()
  else scrollToCurrent()
})

async function startQuestions() {
  mode.value = 'asking'
  error.value = ''
  try {
    const res = await askRoadmapQuestions(locale.value)
    quota.value = res.quota || quota.value
    if (!res.questions.length) return build()
    questions.value = res.questions
    const before = new Map((roadmap.value?.answers || []).map((a) => [a.question, a.answer]))
    for (const q of res.questions) {
      const said = before.get(q.text) || ''
      const choice = q.options.find((o) => said === o || said.startsWith(`${o} — `)) || ''
      answers[q.id] = { choice, text: choice ? said.slice(choice.length + 3) : said }
    }
    mode.value = 'questions'
  } catch (e) {
    error.value = e?.response?.data?.detail || t('errors.generic')
    mode.value = 'map'
  }
}

function collectAnswers() {
  const fresh = questions.value
    .map((q) => {
      const a = answers[q.id] || {}
      const parts = [a.choice, (a.text || '').trim()].filter(Boolean)
      return parts.length ? { question: q.text, answer: parts.join(' — ') } : null
    })
    .filter(Boolean)
  const asked = new Set(questions.value.map((q) => q.text))
  const kept = (roadmap.value?.answers || []).filter((a) => !asked.has(a.question))
  return [...fresh, ...kept].slice(0, 8)
}

async function build(list) {
  mode.value = 'building'
  error.value = ''
  try {
    const res = await buildRoadmap(locale.value, list)
    roadmap.value = res.roadmap
    quota.value = res.quota || quota.value
    motion.value = {}
    questions.value = []
    mode.value = 'map'
    scrollToCurrent()
  } catch (e) {
    error.value = e?.response?.data?.detail || t('errors.generic')
    mode.value = questions.value.length ? 'questions' : 'map'
  }
}

// --- scrolling to a phase -------------------------------------------------------
const sectionEls = new Map()
function setSection(id, el) {
  if (el) sectionEls.set(id, el)
  else sectionEls.delete(id)
}
async function scrollTo(id, smooth = true) {
  await nextTick()
  sectionEls.get(id)?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' })
}
function scrollToCurrent() {
  const phase = current.value?.phase
  if (phase && phase.id !== ahead.value[0]?.id) requestAnimationFrame(() => scrollTo(phase.id, false))
}

// --- one stop -------------------------------------------------------------------
const selectedId = ref(null)
const note = ref('')
const busy = ref(false)
const dialog = ref(null)
const selected = computed(() => items.value.find((i) => i.id === selectedId.value) || null)
const selectedState = computed(() => (selected.value ? stateOf(selected.value.id) : null))
const canReopen = computed(() => {
  if (!selected.value || selected.value.already_done || !selected.value.done) return false
  const last = currentIndex.value === -1 ? items.value.length - 1 : currentIndex.value - 1
  return indexOf(selected.value.id) === last
})

async function open(node) {
  selectedId.value = node.id
  note.value = selected.value?.note || ''
  await nextTick()
  dialog.value?.focus()
}
function close() {
  selectedId.value = null
}
const onKey = (e) => {
  if (e.key === 'Escape' && selectedId.value) close()
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

async function setDone(item, done) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const res = await setRoadmapItem(item.id, done ? { done: true, note: note.value.trim() } : { done: false })
    roadmap.value = res.roadmap
    const next = current.value
    motion.value = done
      ? {
          [item.phase.id]: { gained: 1, freshId: next && next.phase.id === item.phase.id ? next.id : null },
          ...(next && next.phase.id !== item.phase.id ? { [next.phase.id]: { gained: 0, freshId: next.id } } : {}),
        }
      : {}
    close()
    if (done && next && next.phase.id !== item.phase.id) scrollTo(next.phase.id)
  } catch (e) {
    error.value = e?.response?.data?.detail || t('errors.generic')
  } finally {
    busy.value = false
  }
}

const inTodo = (item) => todoTitles.value.has(item.title.trim().toLowerCase())
async function toTodo(item) {
  if (inTodo(item)) return
  try {
    await createStartupTodo(item.title.slice(0, 200))
    todoTitles.value = new Set([...todoTitles.value, item.title.trim().toLowerCase()])
  } catch (e) {
    error.value = e?.response?.data?.detail || t('errors.generic')
  }
}

watch(mode, () => window.scrollTo({ top: 0 }))
</script>

<template>
  <div>
    <RouterLink :to="{ name: 'myStartup' }" class="mb-3 inline-flex min-h-9 items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-brand-600">
      <Icon name="arrowLeft" class="h-4 w-4" />{{ $t('roadmap.back') }}
    </RouterLink>
    <div class="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div class="min-w-0">
        <h1 class="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">{{ $t('roadmap.pageTitle') }}</h1>
        <p class="mt-1 max-w-2xl text-sm text-slate-500">{{ $t('roadmap.pageIntro') }}</p>
      </div>
      <PillBadge v-if="quota" color="brand" variant="soft" icon="coin" size="sm">{{ quota.remaining }} / {{ quota.limit }}</PillBadge>
    </div>

    <p v-if="error" role="alert" class="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10">{{ error }}</p>

    <div v-if="loading" class="card p-6"><LoadingSkeleton height="h-96" rounded="rounded-2xl" /></div>

    <!-- The AI at work -->
    <div v-else-if="mode === 'asking' || mode === 'building'" class="card flex items-center gap-4 p-6" role="status">
      <AiAvatar thinking class="h-12 w-12 shrink-0" />
      <div>
        <p class="font-semibold text-slate-800 dark:text-ink">{{ mode === 'asking' ? $t('roadmap.asking') : $t('roadmap.building') }}</p>
        <p class="text-xs text-slate-500">{{ $t('roadmap.buildingHint') }}</p>
      </div>
    </div>

    <!-- Questions -->
    <form v-else-if="mode === 'questions'" class="card mx-auto max-w-2xl p-6" @submit.prevent="build(collectAnswers())">
      <div class="flex items-start gap-3">
        <AiAvatar class="h-10 w-10 shrink-0" />
        <div>
          <h2 class="text-lg font-extrabold text-slate-900 dark:text-white">{{ $t('roadmap.questionsTitle') }}</h2>
          <p class="mt-1 text-sm text-slate-600 dark:text-slate-300">{{ $t('roadmap.questionsIntro') }}</p>
          <p class="mt-1 text-xs text-slate-400">{{ $t('roadmap.answerHint') }}</p>
        </div>
      </div>
      <fieldset v-for="(q, i) in questions" :key="q.id" class="mt-5 border-t border-slate-100 pt-4 dark:border-hairline">
        <legend class="sr-only">{{ q.text }}</legend>
        <p class="font-semibold text-slate-800 dark:text-ink"><span class="mr-1 text-brand-600">{{ i + 1 }}.</span>{{ q.text }}</p>
        <p v-if="q.why" class="mt-0.5 text-xs text-slate-400">{{ q.why }}</p>
        <div v-if="q.options.length" class="mt-2.5 flex flex-wrap gap-2">
          <button
            v-for="o in q.options"
            :key="o"
            type="button"
            class="min-h-10 rounded-xl border px-3.5 text-sm font-medium transition"
            :class="answers[q.id].choice === o ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-200 text-slate-700 hover:border-brand-300 dark:border-hairline dark:text-slate-200'"
            :aria-pressed="answers[q.id].choice === o"
            @click="answers[q.id].choice = answers[q.id].choice === o ? '' : o"
          >{{ o }}</button>
        </div>
        <input
          v-model="answers[q.id].text"
          maxlength="400"
          :aria-label="q.options.length ? $t('roadmap.ownAnswer') : q.text"
          :placeholder="q.options.length ? $t('roadmap.ownAnswer') : q.placeholder || $t('roadmap.ownAnswer')"
          class="zx-input mt-2.5 w-full py-2 text-sm"
        />
      </fieldset>
      <div class="mt-6 flex flex-wrap justify-end gap-2">
        <button v-if="roadmap" type="button" class="min-h-11 rounded-xl px-4 text-sm font-semibold text-slate-500 hover:bg-slate-100 dark:hover:bg-surface-2" @click="mode = 'map'; questions = []">{{ $t('common.cancel') }}</button>
        <button type="submit" class="pill flex min-h-11 items-center gap-2 bg-brand-600 px-6 text-sm font-semibold text-white hover:bg-brand-700">
          <Icon name="sparkles" class="h-4 w-4" />{{ $t('roadmap.buildFromAnswers') }}
        </button>
      </div>
    </form>

    <!-- Nothing built yet -->
    <div v-else-if="!roadmap" class="card mx-auto flex max-w-2xl flex-col items-center p-8 text-center">
      <BearSticker name="tablet" float class="h-40 w-40" />
      <p class="mt-2 max-w-lg text-sm leading-relaxed text-slate-600 dark:text-slate-300">{{ $t('roadmap.intro') }}</p>
      <button type="button" class="pill mt-5 flex min-h-11 items-center gap-2 bg-brand-600 px-6 text-sm font-semibold text-white hover:bg-brand-700" @click="startQuestions">
        <Icon name="sparkles" class="h-4 w-4" />{{ $t('roadmap.build') }}
      </button>
    </div>

    <!-- The map -->
    <template v-else>
      <p v-if="otherLanguage" class="mb-3 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-500/10 dark:text-amber-200">{{ $t('roadmap.otherLanguage') }}</p>

      <!-- Where the startup stands -->
      <section class="card mb-4 p-5">
        <div class="flex flex-wrap items-start gap-4">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <p class="text-xs font-bold uppercase tracking-widest text-brand-600 dark:text-brand-300">{{ $t('roadmap.where') }}</p>
              <PillBadge color="brand" variant="solid" size="sm">{{ $t(`roadmap.stage_${position.stage || 'idea'}`) }}</PillBadge>
            </div>
            <p v-if="position.headline" class="mt-2 text-xl font-extrabold leading-snug text-slate-900 dark:text-white">{{ position.headline }}</p>
            <p v-if="position.summary" class="mt-1 max-w-3xl text-sm leading-relaxed text-slate-600 dark:text-slate-300">{{ position.summary }}</p>
          </div>
          <button type="button" class="flex min-h-10 items-center gap-1.5 rounded-xl border border-slate-200 px-3 text-sm font-semibold text-brand-600 transition hover:border-brand-300 hover:bg-brand-50 dark:border-hairline dark:hover:bg-brand-500/10" :title="$t('roadmap.rebuildHint')" @click="startQuestions">
            <Icon name="refresh" class="h-4 w-4" />{{ $t('roadmap.refine') }}
          </button>
        </div>
        <p v-if="position.focus" class="mt-3 flex gap-2 rounded-xl bg-brand-50/70 px-3 py-2 text-sm font-semibold text-slate-800 dark:bg-brand-500/10 dark:text-ink">
          <Icon name="target" class="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />
          <span><span class="text-brand-600 dark:text-brand-300">{{ $t('roadmap.focus') }}:</span> {{ position.focus }}</span>
        </p>
        <details v-if="position.strengths?.length || position.gaps?.length || roadmap.answers?.length" class="mt-3">
          <summary class="cursor-pointer text-sm font-semibold text-slate-500">{{ $t('roadmap.details') }}</summary>
          <div class="mt-3 grid gap-4 sm:grid-cols-3">
            <div v-if="position.strengths?.length">
              <p class="mb-1 text-xs font-semibold text-slate-500">{{ $t('roadmap.strengths') }}</p>
              <ul class="space-y-1">
                <li v-for="s in position.strengths" :key="s" class="flex gap-1.5 text-sm text-slate-700 dark:text-slate-200"><Icon name="check" class="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />{{ s }}</li>
              </ul>
            </div>
            <div v-if="position.gaps?.length">
              <p class="mb-1 text-xs font-semibold text-slate-500">{{ $t('roadmap.gaps') }}</p>
              <ul class="space-y-1">
                <li v-for="g in position.gaps" :key="g" class="flex gap-1.5 text-sm text-slate-700 dark:text-slate-200"><Icon name="alert" class="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />{{ g }}</li>
              </ul>
            </div>
            <div v-if="roadmap.answers?.length">
              <p class="mb-1 text-xs font-semibold text-slate-500">{{ $t('roadmap.yourAnswers') }}</p>
              <ul class="space-y-1.5 text-sm">
                <li v-for="a in roadmap.answers" :key="a.question"><span class="block text-xs text-slate-400">{{ a.question }}</span><span class="text-slate-700 dark:text-slate-200">{{ a.answer }}</span></li>
              </ul>
            </div>
          </div>
        </details>
        <div class="mt-4">
          <div class="mb-1.5 flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>{{ $t('roadmap.progress', { done: doneCount, total: openSteps.length }) }}</span>
            <span>{{ Math.round(pct) }}%</span>
          </div>
          <ProgressBar :value="pct" />
        </div>
      </section>

      <!-- Where you are on the road; doubles as a jump control -->
      <div class="sticky top-16 z-20 -mx-2 mb-4 flex gap-2 overflow-x-auto bg-canvas/85 px-2 py-2 backdrop-blur dark:bg-slate-950/70">
        <button
          v-for="(phase, i) in ahead"
          :key="phase.id"
          type="button"
          class="pill shrink-0 gap-1.5 px-3.5 py-1.5 text-xs font-semibold transition"
          :class="current?.phase.id === phase.id ? `${accentOf(accentKey(i)).soft} shadow-sm` : 'bg-white text-slate-500 hover:bg-slate-50 dark:bg-surface dark:text-slate-400'"
          :title="phase.title"
          @click="scrollTo(phase.id)"
        >
          <Icon v-if="phase.done" name="check" class="h-3.5 w-3.5" />
          {{ $t('roadmap.phaseN', { n: i + 1 }) }}
        </button>
      </div>

      <div class="card overflow-hidden">
        <!-- Phases already behind -->
        <section v-if="behind.length" class="relative">
          <div class="relative z-10 flex items-center gap-3 px-6 pb-2 pt-7">
            <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15"><Icon name="check" class="h-5 w-5" /></span>
            <div class="min-w-0">
              <p class="text-base font-bold text-slate-900 dark:text-white">{{ $t('roadmap.behind') }}</p>
              <p class="text-xs text-slate-500">{{ behind.map((p) => p.title).join(' · ') }}</p>
            </div>
          </div>
          <div class="relative">
            <UnitScenery slug="" accent="cash" />
            <StudyPlanPath :nodes="behindNodes" accent="cash" :variant="3" />
          </div>
        </section>

        <!-- The road ahead -->
        <section
          v-for="(phase, i) in ahead"
          :key="phase.id"
          :ref="(el) => setSection(phase.id, el)"
          class="scroll-mt-32"
          :class="i > 0 || behind.length ? 'border-t border-slate-100 dark:border-hairline' : ''"
        >
          <div class="relative z-10 flex items-center gap-3 px-6 pb-2 pt-7">
            <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl" :class="accentOf(accentKey(i)).soft">
              <Icon :name="phase.done ? 'check' : 'flag'" class="h-5 w-5" />
            </span>
            <div class="min-w-0 flex-1">
              <p class="flex flex-wrap items-baseline gap-x-2">
                <span class="text-[11px] font-extrabold uppercase tracking-widest" :class="accentOf(accentKey(i)).ink">{{ $t('roadmap.phaseN', { n: i + 1 }) }}</span>
                <span class="text-base font-bold tracking-tight text-slate-900 dark:text-white">{{ phase.title }}</span>
                <span v-if="phase.horizon" class="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-500 dark:bg-surface-2">{{ phase.horizon }}</span>
                <span v-if="phase.stage" class="rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="accentOf(accentKey(i)).soft">{{ $t(`roadmap.stage_${phase.stage}`) }}</span>
              </p>
              <p v-if="phase.goal" class="mt-0.5 text-xs text-slate-500">{{ phase.goal }}</p>
              <div class="mt-2 flex items-center gap-2.5">
                <span class="h-1.5 max-w-[11rem] flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-surface-2">
                  <span class="block h-full rounded-full transition-[width] duration-700 ease-out" :class="accentOf(accentKey(i)).fill" :style="{ width: (100 * phaseStats(phase).done) / phaseStats(phase).total + '%' }" />
                </span>
                <span class="shrink-0 text-[11px] font-semibold tabular-nums text-slate-400">{{ phaseStats(phase).done }} / {{ phaseStats(phase).total }}</span>
              </div>
            </div>
          </div>
          <div class="relative">
            <UnitScenery slug="" :accent="accentKey(i)" />
            <StudyPlanPath
              :nodes="nodesOf(phase)"
              :accent="accentKey(i)"
              :variant="i"
              :gained="motion[phase.id]?.gained || 0"
              :fresh-id="motion[phase.id]?.freshId || null"
              @select="open"
            />
          </div>
        </section>

        <!-- The finish -->
        <section class="border-t border-slate-100 px-6 pb-10 pt-8 text-center dark:border-hairline">
          <BearSticker v-if="finished" name="celebrate" pop float class="mx-auto h-36 w-36" />
          <div
            v-else
            class="mx-auto flex h-24 w-24 items-center justify-center rounded-full"
            :class="'bg-slate-100 text-slate-400 dark:bg-surface-2'"
          >
            <Icon name="trophy" class="h-11 w-11" />
          </div>
          <p class="mt-3 text-lg font-extrabold text-slate-900 dark:text-white">{{ $t('roadmap.finaleTitle') }}</p>
          <p class="mx-auto mt-1 max-w-md text-sm text-slate-500">{{ finished ? $t('roadmap.finaleDone') : $t('roadmap.finaleLocked') }}</p>
          <p class="mt-4 text-[11px] text-slate-400">{{ $t('roadmap.updated', { date: fmtDate(roadmap.generated_at) }) }} · {{ $t('roadmap.rebuildHint') }}</p>
        </section>
      </div>
    </template>

    <!-- One stop -->
    <Teleport to="body">
      <div v-if="selected" class="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 sm:items-center sm:p-4" @click.self="close">
        <div
          ref="dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="rm-stop-title"
          tabindex="-1"
          class="max-h-[90vh] w-full overflow-y-auto rounded-t-3xl bg-white p-5 shadow-2xl outline-none sm:max-w-lg sm:rounded-3xl dark:bg-surface"
        >
          <div class="flex items-start justify-between gap-3">
            <span class="rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide" :class="selected.kind === 'milestone' ? 'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300' : 'bg-slate-100 text-slate-500 dark:bg-surface-2'">
              {{ selected.kind === 'milestone' ? $t('roadmap.milestone') : $t(`roadmap.area_${selected.area}`) }}
            </span>
            <button type="button" class="-mr-1 -mt-1 flex h-9 w-9 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-100 dark:hover:bg-surface-2" :aria-label="$t('roadmap.close')" @click="close">
              <Icon name="x" class="h-5 w-5" />
            </button>
          </div>
          <h2 id="rm-stop-title" class="mt-2 text-lg font-extrabold leading-snug text-slate-900 dark:text-white">
            {{ selected.kind === 'milestone' ? selected.milestone.title : selected.title }}
          </h2>
          <p class="mt-0.5 text-xs text-slate-400">{{ selected.phase.title }}<template v-if="selected.phase.horizon"> · {{ selected.phase.horizon }}</template></p>

          <div class="mt-4 space-y-3 text-sm">
            <template v-if="selected.kind === 'step'">
              <p v-if="selected.why"><span class="font-semibold text-slate-700 dark:text-slate-200">{{ $t('roadmap.why') }}:</span> <span class="text-slate-600 dark:text-slate-300">{{ selected.why }}</span></p>
              <div v-if="selected.how?.length">
                <p class="font-semibold text-slate-700 dark:text-slate-200">{{ $t('roadmap.how') }}:</p>
                <ol class="mt-1 list-decimal space-y-1 pl-5 text-slate-600 dark:text-slate-300">
                  <li v-for="h in selected.how" :key="h">{{ h }}</li>
                </ol>
              </div>
              <p v-if="selected.metric" class="flex gap-1.5 rounded-xl bg-emerald-50 px-3 py-2 text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-200">
                <Icon name="flag" class="mt-0.5 h-4 w-4 shrink-0" />
                <span><span class="font-semibold">{{ $t('roadmap.metric') }}:</span> {{ selected.metric }}</span>
              </p>
              <!-- A real startup that did something similar (only from the curated list). -->
              <div v-if="selected.case" class="rounded-xl border border-brand-100 bg-brand-50/50 px-3 py-2.5 dark:border-brand-500/20 dark:bg-brand-500/10">
                <p class="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-brand-600 dark:text-brand-300">
                  <Icon name="sparkles" class="h-3.5 w-3.5" />{{ $t('roadmap.caseTitle') }} · {{ selected.case.name }}
                </p>
                <p class="mt-1 text-slate-700 dark:text-slate-200">{{ selected.case.what_they_did }}</p>
                <p v-if="selected.case.apply" class="mt-1 text-slate-600 dark:text-slate-300"><span class="font-semibold">{{ $t('roadmap.caseApply') }}:</span> {{ selected.case.apply }}</p>
              </div>
              <p v-if="selected.pitfall" class="flex gap-1.5 rounded-xl bg-red-50 px-3 py-2 text-red-800 dark:bg-red-500/10 dark:text-red-200">
                <Icon name="alert" class="mt-0.5 h-4 w-4 shrink-0" />
                <span><span class="font-semibold">{{ $t('roadmap.pitfall') }}:</span> {{ selected.pitfall }}</span>
              </p>
            </template>
            <template v-else>
              <p v-if="selected.goal" class="text-slate-600 dark:text-slate-300">{{ selected.goal }}</p>
              <div v-if="selected.milestone.criteria" class="rounded-xl bg-amber-50 px-3 py-2 dark:bg-amber-500/10">
                <p class="text-xs font-semibold text-amber-700 dark:text-amber-300">{{ $t('roadmap.milestoneHint') }}</p>
                <p class="mt-0.5 text-amber-900 dark:text-amber-100">{{ selected.milestone.criteria }}</p>
              </div>
            </template>
          </div>

          <!-- Done: when, and what came of it -->
          <div v-if="selectedState === 'completed'" class="mt-4 rounded-xl border border-emerald-200 bg-emerald-50/60 px-3 py-2 text-sm dark:border-emerald-500/30 dark:bg-emerald-500/10">
            <p class="flex items-center gap-1.5 font-semibold text-emerald-700 dark:text-emerald-300"><Icon name="checkCircle" class="h-4 w-4" />{{ selected.done_at ? $t('roadmap.doneOn', { date: fmtDate(selected.done_at) }) : $t('roadmap.complete') }}</p>
            <p v-if="selected.note" class="mt-1 whitespace-pre-wrap text-slate-600 dark:text-slate-300">{{ selected.note }}</p>
          </div>
          <p v-else-if="selectedState === 'locked'" class="mt-4 flex gap-2 rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-500 dark:bg-surface-2">
            <Icon name="lock" class="mt-0.5 h-4 w-4 shrink-0" />{{ $t('roadmap.lockedHint') }}
          </p>
          <textarea
            v-else
            v-model="note"
            rows="2"
            maxlength="1000"
            :aria-label="$t('roadmap.notePlaceholder')"
            :placeholder="$t('roadmap.notePlaceholder')"
            class="zx-input mt-4 w-full resize-y py-2 text-sm"
          />

          <div class="mt-4 flex flex-wrap items-center justify-between gap-2">
            <button
              v-if="selected.kind === 'step' && !selected.done"
              type="button"
              :disabled="inTodo(selected)"
              class="flex min-h-10 items-center gap-1.5 rounded-xl border border-slate-200 px-3 text-sm font-semibold text-slate-600 transition hover:border-brand-300 hover:text-brand-700 disabled:opacity-60 dark:border-hairline dark:text-slate-300"
              @click="toTodo(selected)"
            >
              <Icon :name="inTodo(selected) ? 'check' : 'plus'" class="h-4 w-4" />{{ inTodo(selected) ? $t('roadmap.inTodo') : $t('roadmap.toTodo') }}
            </button>
            <span v-else />
            <button
              v-if="selectedState === 'current'"
              type="button"
              :disabled="busy"
              class="pill flex min-h-11 items-center gap-2 px-6 text-sm font-semibold text-white disabled:opacity-50"
              :class="selected.kind === 'milestone' ? 'bg-amber-500 hover:bg-amber-600' : 'bg-brand-600 hover:bg-brand-700'"
              @click="setDone(selected, true)"
            >
              <Icon :name="selected.kind === 'milestone' ? 'flag' : 'check'" class="h-4 w-4" />
              {{ selected.kind === 'milestone' ? $t('roadmap.reachMilestone') : $t('roadmap.complete') }}
            </button>
            <button
              v-else-if="canReopen"
              type="button"
              :disabled="busy"
              class="flex min-h-10 items-center gap-1.5 rounded-xl px-3 text-sm font-semibold text-slate-500 hover:bg-slate-100 disabled:opacity-50 dark:hover:bg-surface-2"
              @click="setDone(selected, false)"
            >
              <Icon name="undo" class="h-4 w-4" />{{ $t('roadmap.reopen') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
