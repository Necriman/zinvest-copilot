// Mermaid diagram node. The diagram *source* lives in a `code` attribute (so it
// round-trips in the document HTML as <div data-type="mermaid" data-code="…">),
// and a Vue NodeView renders it to SVG with the lazily-loaded mermaid library.
// It's an atom (no editable inner content) — the source is edited through the
// MermaidEditorModal, opened on double-click (see DocumentEditor).
import { Node, mergeAttributes } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'

import MermaidView from './MermaidView.vue'

export const Mermaid = Node.create({
  name: 'mermaid',
  group: 'block',
  atom: true,
  draggable: true,
  selectable: true,

  addAttributes() {
    return {
      code: {
        default: '',
        parseHTML: (el) => el.getAttribute('data-code') || el.textContent || '',
        renderHTML: (attrs) => ({ 'data-code': attrs.code || '' }),
      },
      // Visual-editor node positions (id → [x,y]). Ignored by the renderer (mermaid
      // auto-lays-out from `code`); used only to restore the canvas arrangement.
      layout: {
        default: null,
        parseHTML: (el) => {
          try {
            return JSON.parse(el.getAttribute('data-layout') || 'null')
          } catch {
            return null
          }
        },
        renderHTML: (attrs) => (attrs.layout ? { 'data-layout': JSON.stringify(attrs.layout) } : {}),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-type="mermaid"]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes({ 'data-type': 'mermaid' }, HTMLAttributes)]
  },

  addNodeView() {
    return VueNodeViewRenderer(MermaidView)
  },

  addCommands() {
    return {
      // Insert a new diagram at the caret.
      insertMermaid:
        (code = '', layout = null) =>
        ({ commands }) =>
          commands.insertContent({ type: this.name, attrs: { code, layout } }),

      // Replace the source (+ layout) of the diagram node at `pos` (edit flow).
      updateMermaid:
        (code, layout, pos) =>
        ({ tr, state, dispatch }) => {
          if (dispatch) {
            const node = state.doc.nodeAt(pos)
            tr.setNodeMarkup(pos, undefined, { ...(node?.attrs || {}), code, layout })
          }
          return true
        },
    }
  },
})

export default Mermaid
