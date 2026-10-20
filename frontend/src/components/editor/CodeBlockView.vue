<script setup>
// NodeView for syntax-highlighted code blocks (CodeBlockLowlight). Adds a header
// bar with a language picker and a copy button; the code itself stays a normal
// editable ProseMirror text node (NodeViewContent), with lowlight painting the
// `.hljs-*` token spans via decorations.
import { ref } from 'vue'
import { NodeViewContent, NodeViewWrapper } from '@tiptap/vue-3'

const props = defineProps({
  node: { type: Object, required: true },
  updateAttributes: { type: Function, required: true },
  extension: { type: Object, required: true },
})

// Curated language list (label → hljs id). `null` id = auto/plain.
const LANGUAGES = [
  { label: 'Plain text', id: 'plaintext', key: 'editor.code.plain' },
  { label: 'JavaScript', id: 'javascript' },
  { label: 'TypeScript', id: 'typescript' },
  { label: 'Python', id: 'python' },
  { label: 'JSON', id: 'json' },
  { label: 'Bash', id: 'bash' },
  { label: 'HTML', id: 'xml' },
  { label: 'CSS', id: 'css' },
  { label: 'SQL', id: 'sql' },
  { label: 'Java', id: 'java' },
  { label: 'C', id: 'c' },
  { label: 'C++', id: 'cpp' },
  { label: 'C#', id: 'csharp' },
  { label: 'Go', id: 'go' },
  { label: 'Rust', id: 'rust' },
  { label: 'PHP', id: 'php' },
  { label: 'Ruby', id: 'ruby' },
  { label: 'Markdown', id: 'markdown' },
  { label: 'YAML', id: 'yaml' },
]

const language = ref(props.node.attrs.language || 'plaintext')
function onLanguage(e) {
  const id = e.target.value
  language.value = id
  props.updateAttributes({ language: id })
}

const copied = ref(false)
async function copy() {
  try {
    await navigator.clipboard.writeText(props.node.textContent || '')
    copied.value = true
    setTimeout(() => (copied.value = false), 1400)
  } catch {
    /* clipboard blocked — no-op */
  }
}
</script>

<template>
  <NodeViewWrapper class="code-block">
    <!-- Header: language picker + copy (non-editable chrome; the code below stays
         a normal editable ProseMirror text node so you can type right in it). -->
    <div class="code-block-header" contenteditable="false">
      <select
        class="code-block-lang"
        :value="language"
        :title="$t('editor.code.language')"
        @change="onLanguage"
      >
        <option v-for="l in LANGUAGES" :key="l.id" :value="l.id">{{ l.key ? $t(l.key) : l.label }}</option>
      </select>
      <button type="button" class="code-block-copy" :title="$t('editor.code.copy')" @click="copy">
        {{ copied ? 'Copied' : 'Copy' }}
      </button>
    </div>
    <!-- The editable code. `spellcheck=false` — it's code, not prose. -->
    <pre spellcheck="false"><NodeViewContent as="code" :class="`hljs language-${language}`" /></pre>
  </NodeViewWrapper>
</template>
