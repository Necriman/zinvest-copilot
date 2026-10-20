<script setup>
// A single flowchart node inside the Vue Flow canvas. Renders one of the mermaid
// shapes, shows a connect handle on each side (drag one to another node to link),
// and edits its label inline on double-click. Label/shape changes flow back to the
// visual editor through the injected `flowEdit` callbacks.
import { computed, inject, nextTick, ref } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})

const flowEdit = inject('flowEdit', null)

const editing = ref(false)
const draft = ref('')
const inputEl = ref(null)

function startEdit() {
  draft.value = props.data.label ?? ''
  editing.value = true
  nextTick(() => {
    inputEl.value?.focus()
    inputEl.value?.select()
  })
}
function commit() {
  if (!editing.value) return
  editing.value = false
  flowEdit?.setLabel?.(props.id, draft.value.trim())
}

const shapeClass = computed(() => `shape-${props.data.shape || 'rect'}`)
</script>

<template>
  <div class="flow-node" :class="[shapeClass, selected ? 'is-selected' : '']" @dblclick.stop="startEdit">
    <Handle id="t" type="source" :position="Position.Top" />
    <Handle id="r" type="source" :position="Position.Right" />
    <Handle id="b" type="source" :position="Position.Bottom" />
    <Handle id="l" type="source" :position="Position.Left" />
    <input
      v-if="editing"
      ref="inputEl"
      v-model="draft"
      class="flow-node-input"
      @blur="commit"
      @keydown.enter.prevent="commit"
      @keydown.stop
      @dblclick.stop
    />
    <span v-else class="flow-node-label">{{ data.label || '…' }}</span>
  </div>
</template>

<style scoped>
.flow-node {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 90px;
  min-height: 44px;
  padding: 8px 14px;
  box-sizing: border-box;
  background: var(--surface);
  border: 1.5px solid var(--brand-500);
  border-radius: 8px;
  color: var(--text);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.25;
  text-align: center;
  cursor: grab;
}
.flow-node.is-selected {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
}
.flow-node-label {
  pointer-events: none;
  word-break: break-word;
}
.flow-node-input {
  width: 100%;
  min-width: 60px;
  border: none;
  background: transparent;
  text-align: center;
  font: inherit;
  color: inherit;
  outline: none;
}

/* Shapes */
.shape-round {
  border-radius: 16px;
}
.shape-stadium {
  border-radius: 999px;
  padding-left: 20px;
  padding-right: 20px;
}
.shape-circle {
  min-width: 78px;
  min-height: 78px;
  border-radius: 50%;
  padding: 8px;
}
/* Clipped shapes can't show a border, so they carry a tinted fill instead. */
.shape-diamond,
.shape-hexagon {
  border: none;
  background: color-mix(in srgb, var(--brand-500), transparent 82%);
  color: var(--text);
}
.shape-diamond {
  min-width: 120px;
  min-height: 96px;
  padding: 18px 26px;
  clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%);
}
.shape-hexagon {
  min-width: 118px;
  min-height: 64px;
  padding: 10px 26px;
  clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%);
}
.shape-diamond.is-selected,
.shape-hexagon.is-selected {
  outline: none;
  background: color-mix(in srgb, var(--brand-500), transparent 62%);
}

/* Connect handles — brand dots, enlarged hit area. */
.flow-node :deep(.vue-flow__handle) {
  width: 9px;
  height: 9px;
  background: var(--brand-600);
  border: 2px solid var(--surface);
}
</style>
