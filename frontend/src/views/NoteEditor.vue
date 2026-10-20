<script setup>
/**
 * Full-screen note editor.
 *
 * Deliberately chrome-free — no sidebar, no right rail — so it's just the
 * document. The body is a centred sheet of "paper" whose width the user drags
 * with the grips on either edge; the choice is remembered across notes.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'

import DocumentEditor from '@/components/editor/DocumentEditor.vue'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import { getNote } from '@/api/notes'
import { useNotes } from '@/composables/useNotes'

const route = useRoute()
const router = useRouter()
const { update } = useNotes()

const note = ref(null)
const loading = ref(true)
const loadError = ref('')
const title = ref('')
const status = ref('saved') // 'saved' | 'saving' | 'unsaved' | 'error'
const dirty = ref(false)
const editorRef = ref(null)

// --- paper width -----------------------------------------------------------
const WIDTH_KEY = 'zinvest.note.paperWidth'
const DEFAULT_W = 816 // ≈ US Letter at 96dpi
const MIN_W = 520
const MAX_W = 1142
const stageRef = ref(null)
const paperWidth = ref(Number(localStorage.getItem(WIDTH_KEY)) || DEFAULT_W)
const dragging = ref(false)
// Which edge the pointer is currently near — the grips stay invisible until you
// actually move toward one, so the page reads as plain paper the rest of the time.
const nearSide = ref(null)
const REVEAL_PX = 90

// Grip insets, in px from each edge of the stage. MEASURED from the sheet's real
// box rather than derived from `paperWidth`, so they stay glued to the paper
// mid-drag and when the sheet is capped at the stage width.
const gripLeft = ref(0)
const gripRight = ref(0)

const clamp = (n) => Math.min(MAX_W, Math.max(MIN_W, Math.round(n)))

/** Measure the sheet's real edges. Exact, but only valid once Vue has painted. */
function syncGrips() {
  const stage = stageRef.value
  const paper = stage?.querySelector('.zx-paper')
  if (!stage || !paper) return
  const s = stage.getBoundingClientRect()
  const p = paper.getBoundingClientRect()
  gripLeft.value = Math.max(0, Math.round(p.left - s.left))
  gripRight.value = Math.max(0, Math.round(s.right - p.right))
}

/** Width the sheet is actually allowed to occupy (the scroller minus its padding).
 *  Found via `closest`, not `parentElement`: the sheet is nested inside the
 *  comment-rail wrapper, so its parent is no longer the scroller. */
function availableWidth() {
  const scroller = stageRef.value?.querySelector('.zx-paper')?.closest('.overflow-y-auto')
  if (!scroller) return stageRef.value?.clientWidth || 0
  const cs = getComputedStyle(scroller)
  return scroller.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0)
}

function startResize(side, event) {
  event.preventDefault()
  dragging.value = true
  const startX = event.clientX
  const startW = paperWidth.value
  // Captured once: the stage can't change size mid-drag, and re-reading layout
  // every frame would just cost us forced reflows.
  const stageW = stageRef.value?.clientWidth || 0
  const avail = availableWidth()
  const sheet = stageRef.value?.querySelector('.zx-paper')
  const scroller = sheet?.closest('.overflow-y-auto')
  const padLeft = scroller ? parseFloat(getComputedStyle(scroller).paddingLeft) || 0 : 0
  // How much wider than the sheet its wrapper is. Zero normally; the width of
  // the comment rail when the cards sit beside the page. It's what stops the
  // sheet being centred in the stage, and it doesn't change during a drag.
  const wrapExtra = Math.max(
    0,
    Math.round((sheet?.parentElement?.getBoundingClientRect().width || 0) - startW),
  )

  const move = (e) => {
    // Centred sheet: dragging a grip out by dx widens both sides, hence ×2.
    const dx = (e.clientX - startX) * (side === 'right' ? 1 : -1)
    const width = clamp(startW + dx * 2)
    paperWidth.value = width
    // Position the handles from the width we just applied rather than measuring
    // afterwards. Measuring lands a frame late, which during a fast drag leaves
    // the handles far enough behind the sheet to look frozen.
    //
    // The wrapper is what's centred, and the sheet sits at its left edge — so
    // with a comment rail alongside, the sheet is off-centre by half the rail.
    // Deriving both handles from one `inset` put them symmetrically about the
    // stage, which is why they drifted away from the page's real edges.
    const shown = Math.min(width, avail)
    const wrapW = Math.min(shown + wrapExtra, avail)
    const left = Math.max(0, Math.round(padLeft + (avail - wrapW) / 2))
    gripLeft.value = left
    gripRight.value = Math.max(0, Math.round(stageW - (left + shown)))
  }
  const stop = () => {
    dragging.value = false
    localStorage.setItem(WIDTH_KEY, String(paperWidth.value))
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', stop)
    window.removeEventListener('pointercancel', stop)
    // Re-measure once at rest, so the handles end up on the true edges even if
    // the layout disagrees with the arithmetic by a pixel.
    requestAnimationFrame(syncGrips)
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', stop)
  window.addEventListener('pointercancel', stop)
}

function resetWidth() {
  paperWidth.value = DEFAULT_W
  localStorage.setItem(WIDTH_KEY, String(DEFAULT_W))
  nextTick(syncGrips)
}

/** Reveal the nearer grip as the pointer approaches that edge of the sheet. */
function onStageMove(e) {
  if (dragging.value) return
  const rect = stageRef.value?.getBoundingClientRect()
  if (!rect) return
  const x = e.clientX - rect.left
  if (Math.abs(x - gripLeft.value) < REVEAL_PX) nearSide.value = 'left'
  else if (Math.abs(x - (rect.width - gripRight.value)) < REVEAL_PX) nearSide.value = 'right'
  else nearSide.value = null
}

let ro = null
/** (Re)observe everything whose size can move the sheet. The stage alone isn't
 *  enough: adding the first comment widens the sheet's wrapper to make room for
 *  the rail, which slides the sheet sideways *without* resizing it or the
 *  stage — so the handles stayed where the sheet used to be. */
function observeLayout() {
  if (!ro) return
  ro.disconnect()
  if (stageRef.value) ro.observe(stageRef.value)
  const sheet = stageRef.value?.querySelector('.zx-paper')
  if (sheet) {
    ro.observe(sheet)
    if (sheet.parentElement) ro.observe(sheet.parentElement)
  }
}
onMounted(() => {
  ro = new ResizeObserver(syncGrips)
  observeLayout()
  nextTick(syncGrips)
  window.addEventListener('keydown', onKey)
  window.addEventListener('beforeunload', onBeforeUnload)
})
onBeforeUnmount(() => {
  ro?.disconnect()
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('beforeunload', onBeforeUnload)
  if (titleTimer) clearTimeout(titleTimer)
})

// --- load ------------------------------------------------------------------
async function load(id) {
  loading.value = true
  loadError.value = ''
  try {
    note.value = await getNote(id)
    title.value = note.value.untitled ? '' : note.value.title
    status.value = 'saved'
    dirty.value = false
  } catch (e) {
    loadError.value = e?.response?.status === 404 ? 'notFound' : 'generic'
  } finally {
    loading.value = false
    // The sheet only exists once the note has loaded — measure and watch it then.
    nextTick(() => {
      observeLayout()
      syncGrips()
    })
  }
}
watch(() => route.params.noteId, (id) => id && load(id), { immediate: true })

// --- save ------------------------------------------------------------------
let titleTimer = null

async function save() {
  if (!note.value || status.value === 'saving') return
  status.value = 'saving'
  try {
    await editorRef.value?.finalizeTempImages?.()
    const content = editorRef.value?.getHTML?.() ?? note.value.content
    const saved = await update(note.value.id, { title: title.value.trim(), content })
    note.value = { ...note.value, ...saved }
    editorRef.value?.markSaved?.()
    dirty.value = false
    status.value = 'saved'
  } catch {
    status.value = 'error'
  }
}

function onTitleInput() {
  status.value = 'unsaved'
  if (titleTimer) clearTimeout(titleTimer)
  titleTimer = setTimeout(save, 900)
}

function onDirty(value) {
  dirty.value = value
  if (value) status.value = 'unsaved'
}

function onKey(e) {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    save()
  }
}
function onBeforeUnload(e) {
  if (dirty.value || status.value === 'unsaved') e.preventDefault()
}

// Flush pending edits rather than dropping them when navigating away.
onBeforeRouteLeave(async () => {
  if (dirty.value || status.value === 'unsaved') await save()
  return true
})

function back() {
  router.push({ name: 'notes' })
}

const statusLabel = computed(
  () => ({ saved: 'notes.saved', saving: 'notes.saving', unsaved: 'notes.unsaved', error: 'notes.saveFailed' })[status.value],
)
</script>

<template>
  <div class="flex h-screen flex-col bg-slate-100 dark:bg-slate-950/40">
    <!-- Slim header: back · title · status · actions -->
    <header
      class="flex shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 py-2.5 dark:border-hairline dark:bg-surface"
    >
      <button
        type="button"
        class="shrink-0 rounded-xl p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-surface-2 dark:hover:text-slate-100"
        :title="$t('common.back')"
        @click="back"
      >
        <Icon name="arrowLeft" class="h-4 w-4" />
      </button>

      <input
        v-model="title"
        type="text"
        maxlength="200"
        :placeholder="$t('notes.untitled')"
        class="min-w-0 flex-1 rounded-lg bg-transparent px-2 py-1 text-base font-bold text-slate-900 placeholder:font-normal placeholder:text-slate-400 hover:bg-slate-50 focus:bg-slate-50 focus:outline-none dark:text-white dark:hover:bg-surface-2 dark:focus:bg-surface-2"
        @input="onTitleInput"
      />

      <span
        class="hidden shrink-0 text-xs sm:block"
        :class="status === 'error' ? 'text-red-500' : 'text-slate-400'"
      >
        {{ $t(statusLabel) }}
      </span>

      <button
        type="button"
        class="shrink-0 rounded-xl px-3 py-1.5 text-sm font-semibold text-white transition disabled:opacity-50"
        :class="status === 'unsaved' ? 'bg-brand-600 hover:bg-brand-700' : 'bg-slate-300 dark:bg-surface-2'"
        :disabled="status === 'saving'"
        :title="$t('notes.saveTip')"
        @click="save"
      >
        {{ $t('common.save') }}
      </button>
    </header>

    <!-- Stage: the editor, plus the drag grips pinned to the sheet's edges -->
    <div
      ref="stageRef"
      class="relative min-h-0 flex-1"
      @pointermove="onStageMove"
      @pointerleave="nearSide = null"
    >
      <div v-if="loading" class="p-8">
        <LoadingSkeleton height="h-96" rounded="rounded-xl" />
      </div>

      <div v-else-if="loadError" class="flex h-full flex-col items-center justify-center gap-3 text-center">
        <Icon name="note" class="h-10 w-10 text-slate-300" />
        <p class="font-semibold text-slate-700 dark:text-slate-200">
          {{ $t(loadError === 'notFound' ? 'notes.notFound' : 'errors.generic') }}
        </p>
        <button type="button" class="text-sm font-semibold text-brand-600 hover:underline" @click="back">
          {{ $t('notes.allNotes') }}
        </button>
      </div>

      <template v-else>
        <DocumentEditor
          ref="editorRef"
          :content="note?.content || ''"
          paper
          :paper-width="paperWidth"
          @update:dirty="onDirty"
          @autosave="save"
        />

        <!-- Width grips: invisible until the pointer nears that edge (or while
             dragging). Pointer-events only on the handles themselves, so the
             document underneath stays fully clickable and scrollable.
             The transition lists opacity/colour explicitly — `transition-all`
             would animate left/right too, leaving the handle easing along
             behind the sheet during a drag instead of staying on its edge. -->
        <div class="pointer-events-none absolute inset-0 z-20">
          <button
            v-for="side in ['left', 'right']"
            :key="side"
            type="button"
            class="pointer-events-auto absolute top-1/2 h-20 w-2.5 -translate-y-1/2 cursor-col-resize rounded-full transition-[opacity,background-color] duration-200"
            :class="[
              dragging ? 'bg-brand-500' : 'bg-slate-300 hover:bg-brand-400 dark:bg-slate-600',
              dragging || nearSide === side ? 'opacity-100' : 'opacity-0',
            ]"
            :style="side === 'left' ? { left: gripLeft + 'px' } : { right: gripRight + 'px' }"
            :title="$t('notes.resize')"
            :aria-label="$t('notes.resize')"
            @pointerdown="startResize(side, $event)"
            @dblclick="resetWidth"
          />
        </div>

        <span
          v-if="dragging"
          class="pointer-events-none absolute left-1/2 top-4 z-30 -translate-x-1/2 rounded-full bg-slate-900/80 px-3 py-1 text-xs font-semibold text-white tabular-nums"
        >
          {{ paperWidth }}px
        </span>
      </template>
    </div>

  </div>
</template>
