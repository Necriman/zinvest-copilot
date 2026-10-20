<script setup>
// Renders a mermaid `code` prop to SVG (lazily-loaded mermaid, theme-aware, with an
// error state). Shared by the code editor and every visual builder's live preview.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { renderMermaid } from './mermaidRenderer'

const props = defineProps({ code: { type: String, default: '' } })

const host = ref(null)
const error = ref('')

let timer = null
function schedule() {
  clearTimeout(timer)
  timer = setTimeout(render, 200)
}
async function render() {
  const src = (props.code || '').trim()
  error.value = ''
  if (!src) {
    if (host.value) host.value.innerHTML = ''
    return
  }
  try {
    // Shared, serialized renderer — see mermaidRenderer. Keeps a builder's live
    // preview from racing the document's diagrams (or another preview).
    const svg = await renderMermaid(src)
    if (host.value) host.value.innerHTML = svg
  } catch (e) {
    error.value = (e && e.message) || 'Invalid diagram syntax'
    if (host.value) host.value.innerHTML = ''
  }
}

watch(() => props.code, schedule)

let themeObserver = null
onMounted(() => {
  render()
  themeObserver = new MutationObserver(() => render())
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
})
onBeforeUnmount(() => {
  clearTimeout(timer)
  themeObserver?.disconnect()
})
</script>

<template>
  <div class="relative flex h-full w-full items-center justify-center overflow-auto p-4">
    <div v-show="!error" ref="host" class="mermaid-preview flex w-full items-center justify-center" />
    <div v-if="error" class="max-w-full px-4 text-center">
      <p class="text-sm font-semibold text-red-600 dark:text-red-400">{{ $t('editor.diagram.invalid') }}</p>
      <p class="mt-1 text-xs text-slate-500">{{ error }}</p>
    </div>
    <p v-if="!code.trim()" class="pointer-events-none absolute text-sm text-slate-400">{{ $t('editor.diagram.previewHere') }}</p>
  </div>
</template>
