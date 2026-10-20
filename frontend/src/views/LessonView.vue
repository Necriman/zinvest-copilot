<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { Splitpanes, Pane } from 'splitpanes'
import 'splitpanes/dist/splitpanes.css'

import DocumentEditor from '@/components/editor/DocumentEditor.vue'
import AiAvatar from '@/components/ai/AiAvatar.vue'
import LessonCompanion from '@/components/mascot/LessonCompanion.vue'
import LessonCelebration from '@/components/mascot/LessonCelebration.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AlertModal from '@/components/ui/AlertModal.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Icon from '@/components/ui/Icon.vue'
import AdminPrompt from '@/components/admin/AdminPrompt.vue'
import { adminApi } from '@/api/admin'
import { getLesson, saveLessonContent, completeLesson } from '@/api/lessons'
import { useAdmin } from '@/composables/useAdmin'
import { useAskAI } from '@/composables/useAskAI'
import { useAuthStore } from '@/store/auth'
import { returnPath } from '@/router/navScroll'
import { payloadToHtml } from '@/utils/payloadToHtml'

const route = useRoute()
const router = useRouter()

const lesson = ref(null)
const completing = ref(false)
const completionError = ref(false)
const celebration = ref(false)
const completion = ref({ coins: 0, streak: 0, nextLessonId: null, testAvailable: false })
const mobilePanel = ref('document')
// Phones read first: the formatting toolbar stays folded until asked for.
const showToolbar = ref(!window.matchMedia('(max-width: 767px)').matches)
function openNextLesson() {
  celebration.value = false
  if (completion.value.nextLessonId) router.push({ name: 'lesson', params: { lessonId: completion.value.nextLessonId } })
}
function openUnitTest() {
  celebration.value = false
  router.push({ name: 'unitTest', params: { unitId: lesson.value.unit_id } })
}
function backToPlan() {
  celebration.value = false
  router.push({ name: 'studyPlan', query: { unit: lesson.value?.unit_id } })
}

const editorRef = ref(null)
const dirty = ref(false) // mirrors DocumentEditor's isDirty via @update:dirty
const saving = ref(false)
const justSaved = ref(false)
let savedTimer = null

// Unsaved-changes guard modal (async — resolves the route-leave promise).
const leaveOpen = ref(false)
let leaveResolve = null

// Anything asked from this page is asked about this lesson.
const askAI = useAskAI()

async function load(id) {
  celebration.value = false
  completionError.value = false
  try {
    lesson.value = await getLesson(id)
  } catch {
    lesson.value = null
  }
  if (lesson.value) askAI.setScope({ lesson: lesson.value.title, lesson_id: lesson.value.id })
}
onBeforeUnmount(() => askAI.clearScope())
watch(() => route.params.lessonId, (id) => id && load(id), { immediate: true })

// The lesson in the newly picked language — unless there are edits not saved
// yet, which a reload would throw away. Saved edits are the learner's own text
// and stay as written in any language.
const { locale } = useI18n()
watch(locale, () => {
  if (!dirty.value && route.params.lessonId) load(route.params.lessonId)
})

// The lesson as written (HTML, or the older drawn layout turned into HTML).
const masterHtml = computed(() => lesson.value?.content_html || payloadToHtml(lesson.value?.canvas_payload))
// Learners read their own saved copy when they have one; the team, while
// editing the lesson itself, always works on the lesson as written.
const docHtml = computed(() => (authoring.value ? masterHtml.value : lesson.value?.edited_content || masterHtml.value))
const isCompleted = computed(() => lesson.value?.status === 'completed')

// --- Editing the lesson for everyone (owner, admin, content editor) --------
// Same editor, same page: the change is saved to the lesson in the language
// shown, through the admin API (which asks to confirm it's them if needed).
const auth = useAuthStore()
const admin = useAdmin()
const { t } = useI18n()
const canAuthor = computed(() => ['owner', 'admin', 'content'].includes(auth.user?.staff_role))
const authoring = ref(false)
const authorTitle = ref('')
const publishing = ref(false)
const authorError = ref('')
const published = ref(false)
let publishedTimer = null

async function startAuthoring() {
  if (!lesson.value) return
  if (!(await guardUnsaved())) return
  authorTitle.value = lesson.value.title
  authorError.value = ''
  showToolbar.value = true
  authoring.value = true
  if (!admin.state.me) admin.load()
}

async function stopAuthoring() {
  if (!(await guardUnsaved())) return
  authoring.value = false
  dirty.value = false
}

async function publish() {
  if (!lesson.value || !editorRef.value || publishing.value) return
  publishing.value = true
  authorError.value = ''
  try {
    await editorRef.value.finalizeTempImages()
    const html = editorRef.value.getHTML()
    await admin.act(() =>
      adminApi.saveLessonBody(lesson.value.id, { lang: locale.value, html, title: authorTitle.value.trim() }),
    )
    editorRef.value.markSaved()
    authoring.value = false
    published.value = true
    clearTimeout(publishedTimer)
    publishedTimer = setTimeout(() => (published.value = false), 3000)
    await load(lesson.value.id)
  } catch (e) {
    authorError.value = admin.errorText(e, t)
  } finally {
    publishing.value = false
  }
}

async function save() {
  // While the lesson itself is being edited, nothing goes to the learner copy.
  if (authoring.value) return
  if (!lesson.value || !editorRef.value || saving.value) return
  saving.value = true
  try {
    await editorRef.value.finalizeTempImages() // "upload" temp images → permanent
    await saveLessonContent(lesson.value.id, editorRef.value.getHTML())
    editorRef.value.markSaved() // resets the editor's dirty flag (→ @update:dirty false)
    justSaved.value = true
    clearTimeout(savedTimer)
    savedTimer = setTimeout(() => (justSaved.value = false), 2000)
  } catch {
    // Save failed — keep `dirty` true so the user can retry; swallow to avoid an
    // unhandled promise rejection from the click handler.
  } finally {
    saving.value = false
  }
}

// Async guard: block navigation behind a Promise the modal resolves. Registered
// for BOTH leave (a different route) and update — switching lessons via Prev/Next
// reuses the same `/learn/:lessonId` route record, which is an "update", not a
// "leave", so onBeforeRouteLeave alone would miss it and silently drop edits.
function guardUnsaved() {
  if (!dirty.value) return true
  return new Promise((resolve) => {
    leaveResolve = resolve
    leaveOpen.value = true
  })
}
onBeforeRouteLeave(guardUnsaved)
onBeforeRouteUpdate(guardUnsaved)
function onLeaveConfirm() {
  leaveResolve?.(true)
  leaveResolve = null
}
function onLeaveCancel() {
  leaveResolve?.(false)
  leaveResolve = null
}

function goBack() {
  // Back to wherever the lesson was opened from — the catalogue if that is where
  // the learner came from, the study map otherwise. Only a lesson opened cold
  // (a shared link, a reload) has no origin to return to; that falls back to the
  // map, focused on this lesson's unit.
  const origin = returnPath()
  if (origin) router.push(origin)
  else router.push({ name: 'studyPlan', query: { unit: lesson.value?.unit_id } })
}
function goPrev() {
  if (lesson.value?.prev_id) router.push({ name: 'lesson', params: { lessonId: lesson.value.prev_id } })
}
function goNext() {
  if (lesson.value?.next_id) router.push({ name: 'lesson', params: { lessonId: lesson.value.next_id } })
}

async function markComplete() {
  if (!lesson.value || completing.value) return
  completing.value = true
  completionError.value = false
  try {
    const res = await completeLesson(lesson.value.id)
    lesson.value.status = 'completed'
    completion.value = {
      coins: res.coins_awarded || 0,
      streak: res.day_streak || 0,
      nextLessonId: res.unlocked_next?.lesson_id || null,
      testAvailable: !!res.unlocked_next?.unit_test_available,
    }
    celebration.value = true
  } catch {
    completionError.value = true
  } finally {
    completing.value = false
  }
}
</script>

<template>
  <div class="flex h-screen w-screen flex-col bg-canvas">
    <!-- Top navbar: back · title · actions -->
    <header
      class="grid shrink-0 grid-cols-[auto_minmax(0,1fr)] items-center gap-2 border-b border-slate-200 bg-white px-3 py-2.5 md:grid-cols-[1fr_minmax(0,auto)_1fr] md:gap-3 md:px-4 dark:border-hairline dark:bg-surface"
    >
      <div class="justify-self-start">
        <button
          type="button"
          class="flex h-9 items-center gap-2 rounded-full px-3 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-surface-2"
          @click="goBack"
        >
          <Icon name="arrowLeft" class="h-4 w-4" /> {{ $t('lesson.back') }}
        </button>
      </div>

      <p class="min-w-0 max-w-full justify-self-center truncate px-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
        {{ lesson?.title }}
      </p>

      <div class="col-span-2 flex max-w-full flex-wrap items-center justify-self-end gap-1.5 md:col-span-1">
        <button
          type="button"
          :disabled="!lesson?.prev_id"
          class="flex h-9 w-9 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 disabled:opacity-30 dark:text-slate-300 dark:hover:bg-surface-2"
          :title="$t('lesson.previous')"
          @click="goPrev"
        >
          <Icon name="arrowLeft" class="h-4 w-4" />
        </button>
        <button
          type="button"
          :disabled="!lesson?.next_id"
          class="flex h-9 w-9 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 disabled:opacity-30 dark:text-slate-300 dark:hover:bg-surface-2"
          :title="$t('lesson.next')"
          @click="goNext"
        >
          <Icon name="arrowRight" class="h-4 w-4" />
        </button>

        <!-- The full tutor — explain, quiz, example — with this lesson as the
             context. The companion panel keeps its quick inline questions;
             this is the way out to the rest. The bear alone carries it until
             the header has room for the words, so the actions never wrap. -->
        <RouterLink
          v-if="lesson"
          :to="{ name: 'zinvestAI', query: { lesson: route.params.lessonId } }"
          class="flex h-9 shrink-0 items-center gap-1.5 rounded-full border border-hairline p-1 text-sm font-semibold text-brand-700 transition hover:border-brand-300 hover:bg-brand-50 2xl:pr-3 dark:text-brand-300 dark:hover:bg-brand-500/10"
          :title="$t('aiHome.askAbout')"
          :aria-label="$t('aiHome.askAbout')"
        >
          <AiAvatar class="h-7 w-7" />
          <span class="hidden 2xl:inline">{{ $t('aiHome.askAbout') }}</span>
        </RouterLink>

        <!-- The team edits the lesson itself, for every learner. -->
        <button
          v-if="canAuthor && lesson && !authoring"
          type="button"
          class="flex h-9 shrink-0 items-center gap-1.5 rounded-full border border-amber-300 px-3 text-sm font-semibold text-amber-800 transition hover:bg-amber-50 dark:border-amber-500/40 dark:text-amber-200 dark:hover:bg-amber-500/10"
          :title="$t('lesson.author.editHint')"
          @click="startAuthoring"
        >
          <Icon name="pencil" class="h-4 w-4" />
          <span class="hidden lg:inline">{{ $t('lesson.author.edit') }}</span>
        </button>
        <span v-if="published" class="flex items-center gap-1 text-xs font-semibold text-green-600 dark:text-green-400" role="status">
          <Icon name="check" class="h-3.5 w-3.5" /> {{ $t('lesson.author.published') }}
        </span>

        <!-- Autosave status (debounced 5s save runs in the background). -->
        <span
          v-if="docHtml && !authoring && (saving || justSaved || dirty)"
          class="mr-1 hidden items-center gap-1.5 text-xs font-medium sm:flex"
          :class="
            saving
              ? 'text-slate-400'
              : justSaved
                ? 'text-green-600 dark:text-green-400'
                : 'text-amber-600 dark:text-amber-400'
          "
          aria-live="polite"
        >
          <template v-if="saving">
            <span class="h-1.5 w-1.5 animate-pulse rounded-full bg-current" /> {{ $t('lesson.saving') }}
          </template>
          <template v-else-if="justSaved">
            <Icon name="check" class="h-3.5 w-3.5" /> {{ $t('lesson.saved') }}
          </template>
          <template v-else>
            <span class="h-1.5 w-1.5 rounded-full bg-current" /> {{ $t('lesson.unsaved') }}
          </template>
        </span>

        <AppButton
          v-if="docHtml && !authoring"
          variant="primary"
          size="sm"
          icon="save"
          :disabled="!dirty || saving"
          @click="save"
        >
          {{ saving ? $t('lesson.saving') : justSaved ? $t('lesson.saved') : $t('lesson.save') }}
        </AppButton>

        <AppButton
          v-if="!isCompleted"
          variant="outline"
          size="sm"
          icon="check"
          :disabled="completing"
          @click="markComplete"
        >
          {{ $t('lesson.complete') }}
        </AppButton>
        <span
          v-else
          class="pill bg-green-50 px-3 py-2 text-sm font-semibold text-green-700 dark:bg-green-500/15 dark:text-green-300"
        >
          <Icon name="check" class="h-4 w-4" /> {{ $t('lesson.completed') }}
        </span>
      </div>
    </header>
    <p v-if="completionError" role="alert" class="bg-red-50 px-4 py-2 text-sm text-red-700">{{ $t('errors.generic') }}</p>

    <!-- Editing the lesson itself: what is saved here is what every learner reads. -->
    <div
      v-if="authoring"
      class="flex flex-wrap items-center gap-2 border-b border-amber-200 bg-amber-50 px-3 py-2 text-sm md:px-4 dark:border-amber-500/30 dark:bg-amber-500/10"
    >
      <Icon name="pencil" class="h-4 w-4 shrink-0 text-amber-700 dark:text-amber-300" />
      <span class="font-semibold text-amber-900 dark:text-amber-100">
        {{ $t('lesson.author.banner', { lang: $t(`lesson.author.langs.${locale}`) }) }}
      </span>
      <label class="flex min-w-[12rem] flex-1 items-center gap-2">
        <span class="sr-only">{{ $t('lesson.author.titleLabel') }}</span>
        <input
          v-model="authorTitle"
          maxlength="140"
          class="zx-input h-9 min-w-0 flex-1 py-1 text-sm"
          :placeholder="$t('lesson.author.titleLabel')"
        />
      </label>
      <span v-if="authorError" class="text-sm text-red-600 dark:text-red-400" role="alert">{{ authorError }}</span>
      <AppButton variant="ghost" size="sm" :disabled="publishing" @click="stopAuthoring">{{ $t('lesson.author.cancel') }}</AppButton>
      <AppButton size="sm" icon="check" :disabled="publishing || !authorTitle.trim()" @click="publish">
        {{ publishing ? $t('lesson.author.publishing') : $t('lesson.author.publish') }}
      </AppButton>
    </div>

    <!-- Resizable split: editor (60%) | avatar (40%) -->
    <div class="flex gap-2 border-b border-hairline p-2 md:hidden"><button class="min-h-11 flex-1 rounded-xl text-sm font-semibold" :class="mobilePanel==='document'?'bg-brand-600 text-white':''" :aria-pressed="mobilePanel==='document'" @click="mobilePanel='document'">{{ $t('mascot.lessonTab') }}</button><button class="min-h-11 flex-1 rounded-xl text-sm font-semibold" :class="mobilePanel==='companion'?'bg-brand-600 text-white':''" :aria-pressed="mobilePanel==='companion'" @click="mobilePanel='companion'">{{ $t('mascot.helperTab') }}</button><button v-if="docHtml && mobilePanel==='document'" type="button" class="flex min-h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-hairline" :class="showToolbar ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300' : 'text-slate-500'" :aria-pressed="showToolbar" :aria-label="$t('mascot.editTools')" :title="$t('mascot.editTools')" @click="showToolbar = !showToolbar"><Icon name="pencil" class="h-4 w-4" /></button></div>
    <splitpanes class="zinvest-split min-h-0 flex-1" :class="'mobile-'+mobilePanel">
      <pane :size="60" min-size="35">
        <DocumentEditor
          v-if="docHtml"
          :key="authoring ? 'author' : 'learner'"
          ref="editorRef"
          :content="docHtml"
          :toolbar="showToolbar"
          @update:dirty="dirty = $event"
          @autosave="save"
        />
        <div v-else-if="lesson" class="flex h-full items-center justify-center bg-white dark:bg-surface">
          <EmptyState bear="book" :message="$t('lesson.contentSoon')" />
        </div>
        <div v-else class="h-full bg-white dark:bg-surface" />
      </pane>
      <pane :size="40" min-size="20">
        <LessonCompanion class="h-full" :lesson="lesson" :completed="isCompleted" :paused="celebration" />
      </pane>
    </splitpanes>

    <LessonCelebration
      :open="celebration"
      :coins="completion.coins"
      :streak="completion.streak"
      :has-next-lesson="!!completion.nextLessonId"
      :test-available="completion.testAvailable"
      @next="openNextLesson"
      @test="openUnitTest"
      @plan="backToPlan"
      @close="celebration = false"
    />

    <!-- "Confirm it's you" for the team's edits (admin step-up). -->
    <AdminPrompt v-if="canAuthor" />

    <!-- Unsaved-changes confirmation (async route guard) -->
    <AlertModal
      v-model="leaveOpen"
      tone="danger"
      :title="$t('lesson.leaveTitle')"
      :message="$t('lesson.leaveMessage')"
      :confirm-text="$t('lesson.leaveConfirm')"
      :cancel-text="$t('lesson.leaveCancel')"
      @confirm="onLeaveConfirm"
      @cancel="onLeaveCancel"
    />
  </div>
</template>

<style>
@media(max-width:767px){.zinvest-split>.splitpanes__splitter{display:none!important}.zinvest-split>.splitpanes__pane{width:100%!important;min-width:0!important}.zinvest-split.mobile-document>.splitpanes__pane:last-child{display:none}.zinvest-split.mobile-companion>.splitpanes__pane:first-child{display:none}}
/* Subtle, grabbable splitter that fits the Zinvest palette. */
.zinvest-split.splitpanes--vertical > .splitpanes__splitter {
  width: 8px;
  background: var(--border);
  position: relative;
  transition: background 0.15s;
}
.zinvest-split.splitpanes--vertical > .splitpanes__splitter:hover {
  background: var(--brand-400);
}
.zinvest-split .splitpanes__splitter::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 2px;
  height: 28px;
  transform: translate(-50%, -50%);
  border-radius: 9999px;
  background: rgb(148 163 184 / 0.6);
}
</style>
