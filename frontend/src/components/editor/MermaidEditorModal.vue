<script setup>
// Mermaid diagram editor with a Visual mode and a Code mode.
//   Visual — pick a type (Flowchart / Class / Pie / Gantt) and build it without
//     writing mermaid: flowcharts use a drag-to-connect canvas, the others use
//     structured forms. Each keeps the mermaid source in sync in a collapsible
//     drawer. Non-visual types (sequence, mindmap, …) fall back to Code.
//   Code  — a raw mermaid textarea + starter templates + live preview.
// "Insert" emits the source plus a flowchart layout map (id → [x,y]).
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import Icon from '@/components/ui/Icon.vue'
import { autoLayout, parseFlowchart, serializeFlowchart } from './mermaidFlowchart'
import { STARTERS, VISUAL_TYPES, detectType } from './mermaidDiagrams'
import MermaidPreview from './MermaidPreview.vue'
import PieBuilder from './PieBuilder.vue'
import GanttBuilder from './GanttBuilder.vue'
import ClassBuilder from './ClassBuilder.vue'

// Vue Flow (heavy) only loads when the flowchart canvas is actually shown.
const MermaidVisualEditor = defineAsyncComponent(() => import('./MermaidVisualEditor.vue'))

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  initialCode: { type: String, default: '' },
  initialLayout: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['insert', 'cancel', 'update:modelValue'])

const mode = ref('visual') // 'visual' | 'code'
const code = ref('')
const builderType = ref('flowchart') // flowchart | class | pie | gantt
const model = ref({ direction: 'TD', nodes: [], edges: [] }) // flowchart model
const canVisual = ref(true)
const builderKey = ref(0) // bump to remount the active builder when code is set externally
const showDrawer = ref(false)

const dialogEl = ref(null)
const textareaEl = ref(null)
let restoreEl = null

const TYPE_OPTIONS = [
  { val: 'flowchart', label: 'editor.diagram.kinds.flowchart' },
  { val: 'class', label: 'editor.diagram.kinds.class' },
  { val: 'pie', label: 'editor.diagram.kinds.pie' },
  { val: 'gantt', label: 'editor.diagram.kinds.gantt' },
]
const emptyModel = () => ({ direction: 'TD', nodes: [], edges: [] })

// --- code <-> builder ------------------------------------------------------
function currentLayout() {
  const out = {}
  for (const n of model.value.nodes || []) if (n.x != null && n.y != null) out[n.id] = [n.x, n.y]
  return out
}
function makeFlowModel(src, layout) {
  const parsed = parseFlowchart(src)
  if (!parsed) return emptyModel()
  let missing = false
  parsed.nodes.forEach((n) => {
    const p = layout?.[n.id]
    if (p) {
      n.x = p[0]
      n.y = p[1]
    } else {
      missing = true
    }
  })
  if (!layout || !Object.keys(layout).length) autoLayout(parsed)
  else if (missing) parsed.nodes.forEach((n, i) => { if (n.x == null) { n.x = 80 + (i % 4) * 175; n.y = 60 + Math.floor(i / 4) * 115 } })
  return parsed
}
// Set the source from outside the active builder (open, type switch, drawer edit):
// re-detect the type, rebuild the flowchart model, and remount the builder.
function applyExternalCode(newCode, layout) {
  code.value = newCode
  const type = detectType(newCode)
  canVisual.value = type !== 'other'
  if (type === 'empty') builderType.value = 'flowchart'
  else if (VISUAL_TYPES.includes(type)) builderType.value = type
  if (builderType.value === 'flowchart') model.value = newCode.trim() ? makeFlowModel(newCode, layout || currentLayout()) : emptyModel()
  builderKey.value++
}
// Flowchart canvas edited → sync code (no remount).
function onVisualChange(m) {
  model.value = m
  code.value = serializeFlowchart(m)
}
// Form builder edited → sync code (no remount).
function onBuilderChange(c) {
  code.value = c
}
// User typed raw mermaid → re-sync the other views (debounced).
let syncTimer = null
function onCodeInput(e) {
  code.value = e.target.value
  clearTimeout(syncTimer)
  syncTimer = setTimeout(() => {
    canVisual.value = detectType(code.value) !== 'other'
    if (mode.value === 'visual') applyExternalCode(code.value, currentLayout())
  }, 350)
}
function switchType(t) {
  if (t === builderType.value) return
  applyExternalCode(STARTERS[t], null)
}
function switchMode(m) {
  if (m === mode.value) return
  if (m === 'visual') {
    if (!canVisual.value) return
    applyExternalCode(code.value, currentLayout())
  } else {
    nextTick(() => textareaEl.value?.focus())
  }
  mode.value = m
}

// --- templates (code mode) -------------------------------------------------
const TEMPLATES = [
  { label: 'editor.diagram.kinds.flowchart', code: STARTERS.flowchart },
  { label: 'editor.diagram.kinds.sequence', code: 'sequenceDiagram\n    participant User\n    participant App\n    User->>App: Request\n    App-->>User: Response' },
  { label: 'editor.diagram.kinds.class', code: STARTERS.class },
  { label: 'editor.diagram.kinds.pie', code: STARTERS.pie },
  { label: 'editor.diagram.kinds.gantt', code: STARTERS.gantt },
  { label: 'editor.diagram.kinds.mindmap', code: 'mindmap\n  root((Zinvest))\n    Learn\n    Invest\n    Grow' },
]
function useTemplate(t) {
  code.value = t.code
  canVisual.value = detectType(t.code) !== 'other'
}

// --- open / close ----------------------------------------------------------
function close() {
  emit('update:modelValue', false)
}
function onCancel() {
  emit('cancel')
  close()
}
function onInsert() {
  const value = code.value.trim()
  if (!value) return
  emit('insert', value, builderType.value === 'flowchart' ? currentLayout() : null)
  close()
}

function focusables() {
  if (!dialogEl.value) return []
  return Array.from(dialogEl.value.querySelectorAll('button, textarea, input, select, [href], [tabindex]:not([tabindex="-1"])')).filter((el) => !el.disabled && el.offsetParent !== null)
}
function onTab(e) {
  const els = focusables()
  if (!els.length) return
  const first = els[0]
  const last = els[els.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      restoreEl = document.activeElement
      showDrawer.value = false
      applyExternalCode(props.initialCode || '', props.initialLayout)
      mode.value = canVisual.value ? 'visual' : 'code'
      if (mode.value === 'code') nextTick(() => textareaEl.value?.focus())
    } else if (restoreEl) {
      restoreEl.focus?.()
      restoreEl = null
    }
  },
)
onBeforeUnmount(() => clearTimeout(syncTimer))

const flowId = computed(() => `mermaid-flow-${builderKey.value}`)
const segBtn = 'rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors'
</script>

<template>
  <Teleport to="body">
    <Transition name="ml-modal">
      <div
        v-if="modelValue"
        ref="dialogEl"
        class="fixed inset-0 z-[100] flex items-center justify-center p-0 md:p-4"
        role="dialog"
        aria-modal="true"
        :aria-label="$t('editor.diagram.editor')"
        @keydown.esc.prevent="onCancel"
        @keydown.tab="onTab"
      >
        <div class="absolute -inset-[20vmax] bg-slate-900/50" />

        <div class="relative flex h-full w-full flex-col overflow-hidden bg-white shadow-float dark:bg-surface md:h-[86vh] md:max-w-5xl md:rounded-3xl md:border md:border-slate-200 dark:md:border-hairline">
          <!-- Header: title · mode toggle · close -->
          <div class="flex shrink-0 items-center justify-between gap-3 border-b border-slate-200 px-5 py-3 dark:border-hairline">
            <h2 class="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-white">
              <Icon name="diagram" class="h-4 w-4 text-brand-600" /> {{ $t('editor.diagram.title') }}
            </h2>
            <div class="flex items-center gap-1 rounded-xl border border-slate-200 p-0.5 dark:border-hairline">
              <button
                type="button"
                class="flex items-center gap-1.5"
                :class="[segBtn, mode === 'visual' ? 'bg-brand-600 text-white' : 'text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2']"
                :disabled="!canVisual"
                :title="canVisual ? $t('editor.diagram.visualEditor') : $t('editor.diagram.visualSupports')"
                @click="switchMode('visual')"
              >
                <Icon name="diagram" class="h-4 w-4" /> {{ $t('editor.diagram.visual') }}
              </button>
              <button
                type="button"
                class="flex items-center gap-1.5"
                :class="[segBtn, mode === 'code' ? 'bg-brand-600 text-white' : 'text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2']"
                @click="switchMode('code')"
              >
                <Icon name="code" class="h-4 w-4" /> {{ $t('editor.diagram.code') }}
              </button>
            </div>
            <button type="button" class="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-surface-2" :title="$t('editor.diagram.close')" @click="onCancel">
              <Icon name="x" class="h-4 w-4" />
            </button>
          </div>

          <!-- VISUAL MODE -->
          <div v-show="mode === 'visual'" class="flex min-h-0 flex-1 flex-col">
            <!-- type selector -->
            <div class="flex shrink-0 items-center gap-1.5 border-b border-slate-200 px-4 py-2 dark:border-hairline">
              <span class="mr-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">{{ $t('editor.diagram.type') }}</span>
              <button
                v-for="t in TYPE_OPTIONS"
                :key="t.val"
                type="button"
                class="rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors"
                :class="builderType === t.val ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300' : 'text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2'"
                @click="switchType(t.val)"
              >
                {{ $t(t.label) }}
              </button>
            </div>

            <div class="min-h-0 flex-1">
              <MermaidVisualEditor v-if="builderType === 'flowchart'" :key="builderKey" :model="model" :flow-id="flowId" @change="onVisualChange" />
              <PieBuilder v-else-if="builderType === 'pie'" :key="builderKey" :code="code" @change="onBuilderChange" />
              <GanttBuilder v-else-if="builderType === 'gantt'" :key="builderKey" :code="code" @change="onBuilderChange" />
              <ClassBuilder v-else-if="builderType === 'class'" :key="builderKey" :code="code" @change="onBuilderChange" />
            </div>

            <!-- collapsible mermaid source -->
            <div class="shrink-0 border-t border-slate-200 dark:border-hairline">
              <button type="button" class="flex w-full items-center gap-2 px-5 py-2 text-xs font-semibold text-slate-500 transition-colors hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-surface-2" @click="showDrawer = !showDrawer">
                <Icon name="code" class="h-3.5 w-3.5" /> {{ $t('editor.diagram.mermaidCode') }}
                <Icon :name="showDrawer ? 'chevronUp' : 'chevronDown'" class="ml-auto h-3.5 w-3.5" />
              </button>
              <textarea
                v-if="showDrawer"
                :value="code"
                spellcheck="false"
                class="h-28 w-full resize-none border-t border-slate-100 bg-slate-50 p-4 font-mono text-xs leading-relaxed text-slate-800 focus:outline-none dark:border-hairline dark:bg-surface-2/40 dark:text-slate-100"
                @input="onCodeInput"
              />
            </div>
          </div>

          <!-- CODE MODE -->
          <div v-show="mode === 'code'" class="flex min-h-0 flex-1 flex-col">
            <div class="flex shrink-0 flex-wrap items-center gap-1.5 border-b border-slate-200 px-5 py-2.5 dark:border-hairline">
              <span class="mr-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">{{ $t('editor.diagram.templates') }}</span>
              <button
                v-for="t in TEMPLATES"
                :key="t.label"
                type="button"
                class="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 dark:border-hairline dark:text-slate-300 dark:hover:bg-brand-500/10 dark:hover:text-brand-300"
                @click="useTemplate(t)"
              >
                {{ $t(t.label) }}
              </button>
            </div>
            <div class="grid min-h-0 flex-1 grid-cols-1 md:grid-cols-2">
              <textarea
                ref="textareaEl"
                :value="code"
                spellcheck="false"
                placeholder="flowchart TD&#10;    A --> B"
                class="min-h-[220px] flex-1 resize-none border-b border-slate-200 bg-transparent p-4 font-mono text-sm leading-relaxed text-slate-800 focus:outline-none md:border-b-0 md:border-r dark:border-hairline dark:text-slate-100"
                @input="onCodeInput"
              />
              <div class="min-h-[220px] bg-slate-50 dark:bg-surface-2/40">
                <MermaidPreview :code="code" />
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex shrink-0 items-center justify-end gap-2 border-t border-slate-200 px-5 py-3 dark:border-hairline">
            <button type="button" class="rounded-full px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2" @click="onCancel">{{ $t('editor.diagram.cancel') }}</button>
            <button type="button" class="rounded-full bg-brand-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-700 disabled:opacity-50" :disabled="!code.trim()" @click="onInsert">{{ $t('editor.diagram.insert') }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
