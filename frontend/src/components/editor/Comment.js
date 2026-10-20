// Comment mark. Highlights a text range and carries the comment's metadata
// (author, ISO date, text, resolved) directly on the mark, so comments round-trip
// with the document HTML — no separate store or backend change needed. Serialized
// as <span data-comment-id="…" data-comment-author="…" …>.
import { Mark, mergeAttributes } from '@tiptap/core'

export const Comment = Mark.create({
  name: 'comment',
  // Don't grow the mark when typing right after it, and keep it out of copied
  // plain-text runs — a comment belongs to the exact range it was placed on.
  inclusive: false,

  addAttributes() {
    return {
      commentId: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-comment-id'),
        renderHTML: (a) => (a.commentId ? { 'data-comment-id': a.commentId } : {}),
      },
      author: {
        default: '',
        parseHTML: (el) => el.getAttribute('data-comment-author') || '',
        renderHTML: (a) => (a.author ? { 'data-comment-author': a.author } : {}),
      },
      date: {
        default: '',
        parseHTML: (el) => el.getAttribute('data-comment-date') || '',
        renderHTML: (a) => (a.date ? { 'data-comment-date': a.date } : {}),
      },
      text: {
        default: '',
        parseHTML: (el) => el.getAttribute('data-comment-text') || '',
        renderHTML: (a) => (a.text ? { 'data-comment-text': a.text } : {}),
      },
      // The comment's highlight color. Rendered as a CSS var so the highlight and
      // the card can share one source of truth (CSS mixes in the alpha).
      color: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-comment-color') || null,
        renderHTML: (a) => (a.color ? { style: `--comment-color: ${a.color}`, 'data-comment-color': a.color } : {}),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'span[data-comment-id]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['span', mergeAttributes({ class: 'comment-mark' }, HTMLAttributes), 0]
  },

  addCommands() {
    return {
      // Place a comment on the current selection.
      setComment:
        (attrs) =>
        ({ commands }) =>
          commands.setMark(this.name, attrs),

      // Patch every text range AND node that carries this commentId (edit text,
      // recolor, …). Node comments use comment-prefixed attrs (see Commentable).
      updateComment:
        (commentId, patch) =>
        ({ tr, state, dispatch }) => {
          const type = state.schema.marks.comment
          const NODE_KEY = { text: 'commentText', color: 'commentColor', author: 'commentAuthor', date: 'commentDate' }
          const nodePatch = {}
          for (const k in patch) if (NODE_KEY[k]) nodePatch[NODE_KEY[k]] = patch[k]
          let changed = false
          state.doc.descendants((node, pos) => {
            if (node.isText) {
              const m = node.marks.find((mk) => mk.type === type && mk.attrs.commentId === commentId)
              if (!m) return
              if (dispatch) {
                tr.removeMark(pos, pos + node.nodeSize, type)
                tr.addMark(pos, pos + node.nodeSize, type.create({ ...m.attrs, ...patch }))
              }
              changed = true
            } else if (node.attrs?.commentId === commentId) {
              if (dispatch) tr.setNodeMarkup(pos, undefined, { ...node.attrs, ...nodePatch })
              changed = true
            }
          })
          return changed
        },

      // Remove every text range AND node that carries this commentId.
      removeComment:
        (commentId) =>
        ({ tr, state, dispatch }) => {
          const type = state.schema.marks.comment
          const CLEARED = { commentId: null, commentAuthor: null, commentDate: null, commentText: null, commentColor: null }
          let changed = false
          state.doc.descendants((node, pos) => {
            if (node.isText) {
              const m = node.marks.find((mk) => mk.type === type && mk.attrs.commentId === commentId)
              if (!m) return
              if (dispatch) tr.removeMark(pos, pos + node.nodeSize, type)
              changed = true
            } else if (node.attrs?.commentId === commentId) {
              if (dispatch) tr.setNodeMarkup(pos, undefined, { ...node.attrs, ...CLEARED })
              changed = true
            }
          })
          return changed
        },
    }
  },
})

export default Comment
