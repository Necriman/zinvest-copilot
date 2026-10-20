<script setup>
// Visual flowchart canvas (Vue Flow). Drag a node's side handle onto another node
// to connect them; double-click a node to rename; use the toolbar to add nodes,
// change the selected node's shape, flip direction, or delete. Every change emits a
// normalized model { direction, nodes:[{id,label,shape,x,y}], edges:[{source,target,label}] }
// which the modal serializes to mermaid text.
import { computed, markRaw, onBeforeUnmount, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarkerType, Panel, VueFlow, useVueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

import Icon from '@/components/ui/Icon.vue'
import FlowShapeNode from './FlowShapeNode.vue'

const props = defineProps({
  model: { type: Object, default: () => ({ direction: 'TD', nodes: [], edges: [] }) },
  flowId: { type: String, required: true },
})
const emit = defineEmits(['change'])

const nodeTypes = { shape: markRaw(FlowShapeNode) }
const edgeOptions = { type: 'smoothstep', markerEnd: MarkerType.ArrowClosed, updatable: true }
let direction = props.model.direction || 'TD'

const initialNodes = (props.model.nodes || []).map((n) => ({
  id: n.id,
  type: 'shape',
  position: { x: n.x ?? 0, y: n.y ?? 0 },
  data: { label: n.label ?? n.id, shape: n.shape || 'rect' },
}))
const initialEdges = (props.model.edges || []).map((e, i) => ({
  id: e.id || `e${i}`,
  source: e.source,
  target: e.target,
  label: e.label || '',
  ...edgeOptions,
}))

const {
  onConnect,
  onNodesChange,
  onEdgesChange,
  onPaneReady,
  addEdges,
  addNodes,
  getNodes,
  getEdges,
  removeNodes,
  removeEdges,
  getSelectedNodes,
  getSelectedEdges,
  updateNodeData,
  fitView,
} = useVueFlow(props.flowId)

let emitTimer = null
function scheduleEmit() {
  clearTimeout(emitTimer)
  emitTimer = setTimeout(emitModel, 120)
}
function emitModel() {
  emit('change', {
    direction,
    nodes: getNodes.value.map((n) => ({
      id: n.id,
      label: n.data?.label ?? n.id,
      shape: n.data?.shape || 'rect',
      x: Math.round(n.position.x),
      y: Math.round(n.position.y),
    })),
    edges: getEdges.value.map((e) => ({ id: e.id, source: e.source, target: e.target, label: e.label || '' })),
  })
}

onConnect((conn) => {
  addEdges([{ id: `e-${conn.source}-${conn.target}-${Date.now()}`, source: conn.source, target: conn.target, label: '', ...edgeOptions }])
})
onNodesChange(() => scheduleEmit())
onEdgesChange(() => scheduleEmit())
onPaneReady(() => setTimeout(() => fitView({ padding: 0.25 }), 30))

const hasSelection = computed(() => getSelectedNodes.value.length > 0)

function nextId() {
  const ids = new Set(getNodes.value.map((n) => n.id))
  let i = 1
  while (ids.has(`n${i}`)) i++
  return `n${i}`
}
const { t: tr } = useI18n()

function addNode() {
  const count = getNodes.value.length
  addNodes([{ id: nextId(), type: 'shape', position: { x: 80 + (count % 4) * 175, y: 70 + Math.floor(count / 4) * 115 }, data: { label: tr('editor.diagram.newNode'), shape: 'rect' } }])
}
function deleteSelected() {
  const sn = getSelectedNodes.value.map((n) => n.id)
  const se = getSelectedEdges.value.map((e) => e.id)
  if (sn.length) removeNodes(sn, true)
  if (se.length) removeEdges(se)
}
function applyShape(shape) {
  for (const n of getSelectedNodes.value) updateNodeData(n.id, { shape })
  scheduleEmit()
}
function setDirection(d) {
  direction = d
  scheduleEmit()
}

// Label edits come up from FlowShapeNode.
provide('flowEdit', {
  setLabel: (id, label) => {
    updateNodeData(id, { label })
    scheduleEmit()
  },
})

onBeforeUnmount(() => clearTimeout(emitTimer))

const SHAPES = [
  { val: 'rect', label: 'editor.diagram.shapes.rect', icon: 'square' },
  { val: 'round', label: 'editor.diagram.shapes.round', icon: 'squareRound' },
  { val: 'stadium', label: 'editor.diagram.shapes.stadium', icon: 'pill' },
  { val: 'diamond', label: 'editor.diagram.shapes.diamond', icon: 'diamond' },
  { val: 'circle', label: 'editor.diagram.shapes.circle', icon: 'circle' },
  { val: 'hexagon', label: 'editor.diagram.shapes.hexagon', icon: 'hexagon' },
]
const btn =
  'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold transition-colors disabled:opacity-40 disabled:pointer-events-none'
</script>

<template>
  <div class="visual-canvas">
    <VueFlow
      :id="flowId"
      :nodes="initialNodes"
      :edges="initialEdges"
      :node-types="nodeTypes"
      connection-mode="loose"
      :default-edge-options="edgeOptions"
      :min-zoom="0.2"
      :max-zoom="2"
      :delete-key-code="['Delete', 'Backspace']"
      :connection-radius="30"
      fit-view-on-init
      @nodes-change="scheduleEmit"
    >
      <!-- Toolbar -->
      <Panel position="top-left">
        <div class="vf-toolbar">
          <button type="button" :class="[btn, 'bg-brand-600 text-white hover:bg-brand-700']" @click="addNode">
            <Icon name="plus" class="h-3.5 w-3.5" /> {{ $t('editor.diagram.node') }}
          </button>

          <span class="vf-sep" />

          <!-- shapes apply to the selected node -->
          <div class="flex items-center gap-0.5">
            <button
              v-for="s in SHAPES"
              :key="s.val"
              type="button"
              :class="[btn, 'px-1.5 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2']"
              :disabled="!hasSelection"
              :title="$t(s.label)"
              @click="applyShape(s.val)"
            >
              <Icon :name="s.icon" class="h-4 w-4" />
            </button>
          </div>

          <span class="vf-sep" />

          <!-- direction -->
          <div class="vf-seg">
            <button type="button" :class="direction === 'TD' ? 'vf-seg-on' : ''" :title="$t('editor.diagram.topDown')" @click="setDirection('TD')">↓</button>
            <button type="button" :class="direction === 'LR' ? 'vf-seg-on' : ''" :title="$t('editor.diagram.leftRight')" @click="setDirection('LR')">→</button>
          </div>

          <span class="vf-sep" />

          <button
            type="button"
            :class="[btn, 'text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10']"
            :disabled="!hasSelection && !getSelectedEdges.length"
            @click="deleteSelected"
          >
            <Icon name="trash" class="h-3.5 w-3.5" /> {{ $t('editor.diagram.delete') }}
          </button>
        </div>
      </Panel>

      <Panel position="bottom-left">
        <p class="vf-hint">{{ $t('editor.diagram.dragHint') }}</p>
      </Panel>
    </VueFlow>
  </div>
</template>

<style scoped>
.visual-canvas {
  position: relative;
  width: 100%;
  height: 100%;
  background:
    radial-gradient(circle, color-mix(in srgb, var(--text-muted), transparent 82%) 1px, transparent 1px) 0 0 / 20px 20px;
  background-color: var(--bg);
}
.vf-toolbar {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem;
  border-radius: 0.85rem;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: 0 8px 24px rgb(15 23 42 / 0.12);
}
.vf-sep {
  width: 1px;
  height: 20px;
  background: var(--border);
}
.vf-seg {
  display: flex;
  overflow: hidden;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
}
.vf-seg button {
  width: 30px;
  height: 28px;
  font-size: 15px;
  color: var(--text-muted);
}
.vf-seg button.vf-seg-on {
  background: var(--brand-600);
  color: #fff;
}
.vf-hint {
  padding: 0.3rem 0.6rem;
  border-radius: 0.6rem;
  background: color-mix(in srgb, var(--surface), transparent 10%);
  border: 1px solid var(--border);
  font-size: 11px;
  color: var(--text-muted);
}
</style>
