<script setup>
// NodeView for the Mermaid diagram node. Renders `node.attrs.code` to SVG via the
// mermaid library, which is imported lazily (dynamic import) so its ~big bundle
// only loads when a document actually contains a diagram. Re-renders when the
// source changes or the color theme flips. Double-click to edit is handled by the
// editor (handleDoubleClickOn) — this view only draws.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { NodeViewWrapper } from '@tiptap/vue-3'

import { renderMermaid } from './mermaidRenderer'

const props = defineProps({
  node: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})

const host = ref(null) // the SVG container
const error = ref('') // parse-error message (shows the source as a fallback)
const rendering = ref(false)

async function render() {
  const code = (props.node.attrs.code || '').trim()
  error.value = ''
  if (!code) return // empty → the template shows a placeholder
  rendering.value = true
  try {
    // Serialized against every other diagram on the page — see mermaidRenderer.
    // Rendering concurrently is what made diagrams intermittently fail to open.
    const svg = await renderMermaid(code)
    if (host.value) host.value.innerHTML = svg
  } catch (e) {
    error.value = (e && e.message) || 'Invalid diagram syntax'
    if (host.value) host.value.innerHTML = ''
  } finally {
    rendering.value = false
  }
}

// Re-render when the source changes.
watch(() => props.node.attrs.code, render)

// Re-theme when the app toggles .dark on <html>.
let themeObserver = null
onMounted(() => {
  render()
  themeObserver = new MutationObserver(() => render())
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
})
onBeforeUnmount(() => themeObserver?.disconnect())
</script>

<template>
  <NodeViewWrapper
    as="div"
    class="mermaid-block"
    :class="selected ? 'mermaid-selected' : ''"
    data-drag-handle
  >
    <!-- Rendered SVG -->
    <div v-show="node.attrs.code && !error" ref="host" class="mermaid-canvas" />

    <!-- Empty state -->
    <div v-if="!node.attrs.code" class="mermaid-empty">
      <span>{{ $t('editor.diagram.empty') }}</span>
    </div>

    <!-- Parse error: show the message + the raw source so it's recoverable -->
    <div v-else-if="error" class="mermaid-error">
      <p class="mermaid-error-title">⚠ {{ error }}</p>
      <pre class="mermaid-error-source">{{ node.attrs.code }}</pre>
      <p class="mermaid-error-hint">{{ $t('editor.diagram.fix') }}</p>
    </div>
  </NodeViewWrapper>
</template>
