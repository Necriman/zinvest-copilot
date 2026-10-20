<script setup>
// Notion-style rich document editor. The pane *is* the document (no floating
// paper). A slim static toolbar holds structural controls; text + table controls
// live in contextual bubble menus. Receives HTML via `content`, emits changes.
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { EditorContent, useEditor, VueNodeViewRenderer } from '@tiptap/vue-3'
import { BubbleMenu } from '@tiptap/vue-3/menus'
// StarterKit (v3) bundles Bold/Italic/Underline/Strike/Heading/lists/Link/code.
// TextStyleKit adds Color + FontFamily + FontSize. TableKit adds tables.
import { StarterKit } from '@tiptap/starter-kit'
import { TableKit } from '@tiptap/extension-table'
import { TextStyleKit } from '@tiptap/extension-text-style'
import { Highlight } from '@tiptap/extension-highlight'
import { Image } from '@tiptap/extension-image'
import { BlockMath, InlineMath } from '@tiptap/extension-mathematics'
import { TextAlign } from '@tiptap/extension-text-align'
// Syntax-highlighted code blocks (lowlight = highlight.js) + task lists.
import { CodeBlockLowlight } from '@tiptap/extension-code-block-lowlight'
import { TaskItem, TaskList } from '@tiptap/extension-list'
import { createLowlight } from 'lowlight'
// Only the languages the code-block picker exposes are registered (not the full
// `common` set) — smaller bundle, and the dropdown never offers a language that
// wouldn't highlight. highlight.js auto-registers each grammar's aliases too.
import bash from 'highlight.js/lib/languages/bash'
import c from 'highlight.js/lib/languages/c'
import cpp from 'highlight.js/lib/languages/cpp'
import csharp from 'highlight.js/lib/languages/csharp'
import css from 'highlight.js/lib/languages/css'
import go from 'highlight.js/lib/languages/go'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import markdown from 'highlight.js/lib/languages/markdown'
import php from 'highlight.js/lib/languages/php'
import plaintext from 'highlight.js/lib/languages/plaintext'
import python from 'highlight.js/lib/languages/python'
import ruby from 'highlight.js/lib/languages/ruby'
import rust from 'highlight.js/lib/languages/rust'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'
import katex from 'katex'
import 'katex/dist/katex.min.css'

import Icon from '@/components/ui/Icon.vue'
import ColorPickerMenu from './ColorPickerMenu.vue'
import HighlightPickerMenu from './HighlightPickerMenu.vue'
import ToolbarDropdown from './ToolbarDropdown.vue'
import ResizableImage from './ResizableImage.vue'
import TableGridMenu from './TableGridMenu.vue'
const MathEditorModal = defineAsyncComponent(() => import('./MathEditorModal.vue'))
import ContextMenu from './ContextMenu.vue'
import AlignmentMenu from './AlignmentMenu.vue'
import LineSpacingMenu from './LineSpacingMenu.vue'
import SpacingMenu from './SpacingMenu.vue'
import ListMenu from './ListMenu.vue'
import QuoteMenu from './QuoteMenu.vue'
import CodeStyleMenu from './CodeStyleMenu.vue'
import LinkModal from './LinkModal.vue'
const MermaidEditorModal = defineAsyncComponent(() => import('./MermaidEditorModal.vue'))
import CodeBlockView from './CodeBlockView.vue'
// Custom block-layout extensions — Tiptap ships neither line-height nor spacing
// natively, so we inject them as global attributes (see the extension files).
import LineHeight from './LineHeight'
import Spacing from './Spacing'
import CellBackground from './CellBackground'
import Comment from './Comment'
import Commentable from './Commentable'
import CommentsRail from './CommentsRail.vue'
import CommentCard from './CommentCard.vue'
import ListStyle from './ListStyle'
import QuoteColor from './QuoteColor'
import CodeStyle from './CodeStyle'
import Mermaid from './Mermaid'
import { useAuthStore } from '@/store/auth'
import { useAskAI } from '@/composables/useAskAI'

// Code-block syntax highlighting. `common` bundles ~35 popular languages (keeps the
// payload far smaller than the full set); a Vue NodeView adds the language picker +
// copy button on top of lowlight's token decorations.
const lowlight = createLowlight()
lowlight.register({
  bash, c, cpp, csharp, css, go, java, javascript, json, markdown,
  php, plaintext, python, ruby, rust, sql, typescript, xml, yaml,
})
const CodeBlockHighlighted = CodeBlockLowlight.extend({
  addNodeView() {
    return VueNodeViewRenderer(CodeBlockView)
  },
}).configure({ lowlight, defaultLanguage: 'plaintext' })

const props = defineProps({
  content: { type: String, default: '' },
  editable: { type: Boolean, default: true },
  // The formatting toolbar. Lessons hide it on phones until the reader asks
  // to edit, so the text gets the screen.
  toolbar: { type: Boolean, default: true },
  // Paper mode: the body scrolls inside a tinted backdrop with the document
  // centred on a fixed-width white sheet (notes), instead of filling the pane
  // edge to edge (lessons). `paperWidth` is in CSS pixels.
  paper: { type: Boolean, default: false },
  paperWidth: { type: Number, default: 816 },
})

// A page is a fixed height (≈US Letter at 96dpi) — widening the sheet must not
// make it taller, the way a real page doesn't change length when you widen it.
const PAGE_MIN_HEIGHT = 1056
const emit = defineEmits(['update:content', 'update:dirty', 'autosave'])

// Dirty tracking: flips true on the first edit, reset by the parent after a save.
const isDirty = ref(false)
// The document as it was loaded or last saved. A transaction that leaves it
// unchanged (a normalisation on open, an undo back to the start) is not an
// edit: saving it would store a copy nobody wrote — and a lesson saved like
// that stops following the language switcher.
let baseline = ''
const fileInput = ref(null)
const mathOpen = ref(false)
// Math edit state: null → inserting a new equation; { pos, type } → updating the
// existing node the user clicked. `mathInitial` prefills the modal's <math-field>.
const mathEdit = ref(null)
const mathInitial = ref('')
// Mermaid diagram editor state (mirrors math): null → inserting new, { pos } → edit.
const mermaidOpen = ref(false)
const mermaidEdit = ref(null)
const mermaidInitial = ref('')
const mermaidLayout = ref({}) // node positions restored into the visual canvas
// The equation and diagram editors are heavy (MathLive alone is most of the
// editor's weight) and rarely opened: load each the first time it is needed,
// then keep it mounted so its close animation still plays.
const mathMounted = ref(false)
const mermaidMounted = ref(false)
watch(mathOpen, (open) => open && (mathMounted.value = true))
watch(mermaidOpen, (open) => open && (mermaidMounted.value = true))
// Link editor state.
const linkOpen = ref(false)
const linkInitial = ref('')
const linkEditing = ref(false)

// Comments: inline comment marks + a right-margin rail. All metadata lives on the
// mark, so comments round-trip with the document HTML.
const auth = useAuthStore()
const DEFAULT_COMMENT_COLOR = '#8b5cf6'
const commentsOn = ref(true)
const comments = ref([]) // [{ id, author, date, text, color }]
const commentTops = ref({}) // id -> anchor top (px, relative to the wrapper)
const editingCommentId = ref(null)
const hoveredCommentId = ref(null)
const commentsWrap = ref(null)
// When there are more comments than comfortably fit down the rail, collapse it:
// hide the cards and instead reveal one at a time as a popover on hover (or while
// composing) — so cards never drift far from their anchor. `railCapacity` is how
// many ~cards tall the visible editor is; measured on layout.
const railCapacity = ref(6)
const commentsCollapsed = computed(() => comments.value.length > railCapacity.value)
// On the paper editor the cards belong *beside* the sheet, not floating over it —
// but only when the stage is wide enough to hold both. Below that they fall back
// to overlaying the sheet's right margin, as in the full-width (lesson) editor.
const RAIL_SPACE = 304 // w-72 card + breathing room
const railOutside = ref(false)
const railShown = computed(() => commentsOn.value && comments.value.length > 0 && !commentsCollapsed.value)
// The sheet keeps its own width; the wrapper grows to make room for the rail.
const stageWidth = computed(() =>
  props.paper && railShown.value && railOutside.value
    ? props.paperWidth + RAIL_SPACE
    : props.paperWidth,
)
// The comment shown in the collapsed-mode popover: the one being edited (pinned) or
// the one currently hovered.
const activeCommentId = computed(() => editingCommentId.value || hoveredCommentId.value)
const activeComment = computed(() => comments.value.find((c) => c.id === activeCommentId.value) || null)
const hoverPopStyle = ref(null) // fixed-position style for that popover
// The ProseMirror content DOM, captured on create. Using this (rather than
// editor.value.view.dom) avoids Tiptap throwing "view is not available" when the
// view isn't mounted yet — which happens when the editor is re-created after a
// route change (navigating back into a lesson).
let editorDom = null
// Debounced autosave: every edit restarts a 5s timer; when it fires we ask the
// parent (which owns the API call) to save.
const AUTOSAVE_MS = 5000
let autosaveTimer = null
// Local files behind temp object-URLs, keyed by src → File (resolved on save).
const tempFiles = new Map()

// Base Image + `width`/`temp` attributes + our resizable Vue NodeView.
// `draggable: true` lets ProseMirror pick the node up and move it around the
// document (the NodeView's outer element carries `data-drag-handle`).
const ResizableImageExt = Image.extend({
  draggable: true,
  addAttributes() {
    return {
      ...this.parent?.(),
      width: {
        default: null,
        parseHTML: (el) => {
          const w = el.getAttribute('width') || el.style?.width
          return w ? parseInt(w, 10) || null : null
        },
        renderHTML: (attrs) => (attrs.width ? { width: attrs.width } : {}),
      },
      temp: {
        default: false,
        parseHTML: (el) => el.getAttribute('data-temp') === 'true',
        renderHTML: (attrs) => (attrs.temp ? { 'data-temp': 'true' } : {}),
      },
    }
  },
  addNodeView() {
    return VueNodeViewRenderer(ResizableImage)
  },
})

// Block math extended with a resizable `fontSize` attribute. We re-implement the
// KaTeX NodeView (rather than reuse the extension's) so the stored font-size is
// applied to the live element and updates when the toolbar size changes.
const BlockMathResizable = BlockMath.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      fontSize: {
        default: null,
        parseHTML: (el) => el.style?.fontSize || null,
        renderHTML: (attrs) => (attrs.fontSize ? { style: `font-size: ${attrs.fontSize}` } : {}),
      },
    }
  },
  addNodeView() {
    const options = this.options
    const editable = () => this.editor?.isEditable
    // Structure: an outer block that carries alignment + spacing, wrapping the hug
    // box with the KaTeX render. TextAlign / Spacing are global attributes, but a
    // custom NodeView doesn't auto-apply an attribute's renderHTML, so we set those
    // styles by hand here. No click handler: a single click falls through to
    // ProseMirror so the node gets selected (outline + toolbar resize); editing
    // opens on double-click via editorProps.handleDoubleClickOn.
    return ({ node }) => {
      let current = node
      const outer = document.createElement('div')
      outer.className = 'tiptap-math-block'
      const box = document.createElement('div')
      const inner = document.createElement('div')
      box.className = 'tiptap-mathematics-render'
      if (editable()) box.classList.add('tiptap-mathematics-render--editable')
      inner.className = 'block-math-inner'
      box.dataset.type = 'block-math'
      box.appendChild(inner)
      outer.appendChild(box)
      const render = (n) => {
        box.setAttribute('data-latex', n.attrs.latex ?? '')
        box.style.fontSize = n.attrs.fontSize || ''
        // Alignment positions the hug box; spacing margins/pads the whole block.
        outer.style.textAlign = n.attrs.textAlign || ''
        outer.style.marginTop = n.attrs.marginTop || ''
        outer.style.marginBottom = n.attrs.marginBottom || ''
        outer.style.paddingTop = n.attrs.paddingTop || ''
        outer.style.paddingBottom = n.attrs.paddingBottom || ''
        try {
          katex.render(n.attrs.latex ?? '', inner, options.katexOptions ?? { throwOnError: false })
          box.classList.remove('block-math-error')
        } catch {
          inner.textContent = n.attrs.latex ?? ''
          box.classList.add('block-math-error')
        }
      }
      render(node)
      return {
        dom: outer,
        update: (updated) => {
          if (updated.type.name !== current.type.name) return false
          current = updated
          render(updated)
          return true
        },
      }
    }
  },
})

// Insert a local image file as a *temporary* node (object-URL + data-temp flag).
// `pos` (optional) inserts at an explicit doc position, e.g. the drop point.
// Hoisted so editorProps handlers below can reference it.
function insertTempImageFile(file, pos) {
  if (!file || !file.type?.startsWith('image/')) return
  const url = URL.createObjectURL(file)
  tempFiles.set(url, file)
  const node = { type: 'image', attrs: { src: url, temp: true } }
  const c = editor.value?.chain().focus()
  if (!c) return
  if (typeof pos === 'number') c.insertContentAt(pos, node).run()
  else c.insertContent(node).run()
}

const editor = useEditor({
  content: props.content,
  editable: props.editable,
  extensions: [
    // Disable StarterKit's plain code block (replaced by the highlighted one below)
    // and configure Link: don't navigate on click inside the editor (we edit it
    // instead), auto-link typed URLs, and harden the rendered anchor.
    StarterKit.configure({
      codeBlock: false,
      link: {
        openOnClick: false,
        autolink: true,
        defaultProtocol: 'https',
        HTMLAttributes: { rel: 'noopener noreferrer nofollow', target: '_blank' },
      },
    }),
    // TextStyleKit ships its own `lineHeight` since 3.31; ours (LineHeight.js)
    // sets the attribute on the block types and backs the spacing menu, so the
    // kit's is switched off rather than registered twice.
    TextStyleKit.configure({ lineHeight: false }),
    Highlight.configure({ multicolor: true }), // multicolor → per-selection highlight colors
    CodeBlockHighlighted, // syntax-highlighted fenced code (see module scope)
    TaskList,
    TaskItem.configure({ nested: true }), // checkbox lists, nestable
    TableKit.configure({ table: { resizable: false } }),
    ResizableImageExt.configure({ inline: false, allowBase64: true }),
    Mermaid, // diagram node (lazy-rendered NodeView)
    // Double-click a rendered equation to re-open the visual editor (see
    // handleDoubleClickOn); block math also carries a resizable fontSize attr.
    BlockMathResizable,
    InlineMath,
    // Block layout controls. TextAlign + Spacing target every block type (their
    // attrs are painted by the image / blockMath NodeViews too); LineHeight is
    // text-only. Node NAMES here are schema names (blockMath, listItem) — NOT the
    // DOM data-type values.
    TextAlign.configure({ types: ['heading', 'paragraph', 'image', 'table', 'blockMath'] }),
    LineHeight, // heading / paragraph / listItem
    Spacing, // heading / paragraph / image / table / blockMath
    ListStyle, // list-style-type on bulletList / orderedList (decimal, a·b·c, i·ii·iii …)
    QuoteColor, // accent color on blockquote
    CodeStyle, // per-span text/background color on inline code
    CellBackground, // per-cell fill on tableCell / tableHeader
    Comment, // inline comment mark (metadata stored on the mark → persists in HTML)
    Commentable, // lets image nodes carry a comment too
  ],
  editorProps: {
    attributes: {
      class:
        'prose prose-slate dark:prose-invert prose-a:text-brand-600 max-w-none min-h-full px-12 py-8 focus:outline-none',
    },
    handlePaste(view, event) {
      const files = Array.from(event.clipboardData?.files || []).filter((f) => f.type.startsWith('image/'))
      if (!files.length) return false
      files.forEach(insertTempImageFile)
      return true
    },
    handleDrop(view, event) {
      const files = Array.from(event.dataTransfer?.files || []).filter((f) => f.type.startsWith('image/'))
      if (!files.length) return false
      event.preventDefault()
      const at = view.posAtCoords({ left: event.clientX, top: event.clientY })
      files.forEach((f) => insertTempImageFile(f, at?.pos))
      return true
    },
    // Ctrl / ⌘ + click a link opens it in a new tab (a plain click keeps editing,
    // since Link is configured openOnClick:false). Other clicks fall through.
    handleClick(view, pos, event) {
      if (!(event.metaKey || event.ctrlKey)) return false
      const href = event.target?.closest?.('a')?.getAttribute('href')
      if (!href) return false
      window.open(href, '_blank', 'noopener,noreferrer')
      return true
    },
    // Double-click a rendered equation → open the visual editor prefilled. Single
    // clicks are left to ProseMirror (node selection). Covers block + inline math.
    handleDoubleClickOn(view, pos, node, nodePos) {
      if (node.type.name === 'blockMath' || node.type.name === 'inlineMath') {
        openMathEditor(node.attrs.latex || '', { pos: nodePos, type: node.type.name })
        return true
      }
      if (node.type.name === 'mermaid') {
        openMermaidEditor(node.attrs.code || '', node.attrs.layout || {}, { pos: nodePos })
        return true
      }
      return false
    },
  },
  // Attach comment listeners once the view actually exists (safe on re-create).
  onCreate: ({ editor }) => {
    baseline = editor.getHTML()
    editorDom = editor.view.dom
    editorDom.addEventListener('mouseover', onEditorMouseOver)
    editorDom.addEventListener('mouseleave', onEditorMouseLeave)
    rebuildComments(editor)
    watchLayout()
    scheduleTops()
  },
  onUpdate: ({ editor }) => {
    const html = editor.getHTML()
    emit('update:content', html)
    if (html === baseline) {
      clearTimeout(autosaveTimer)
      if (isDirty.value) {
        isDirty.value = false
        emit('update:dirty', false)
      }
      refreshComments()
      return
    }
    if (!isDirty.value) {
      isDirty.value = true
      emit('update:dirty', true)
    }
    // Restart the debounce window on every keystroke.
    clearTimeout(autosaveTimer)
    autosaveTimer = setTimeout(() => emit('autosave'), AUTOSAVE_MS)
    refreshComments()
  },
})

// --- comments --------------------------------------------------------------
function authorName() {
  const u = auth.user
  const name = [u?.first_name, u?.last_name].filter(Boolean).join(' ').trim()
  return name || u?.email || 'You'
}
// Rebuild the comments list from the comment marks in the doc (dedupe by id).
function rebuildComments(ed = editor.value) {
  if (!ed) return
  const type = ed.schema.marks.comment
  const seen = new Map()
  ed.state.doc.descendants((node) => {
    if (node.isText) {
      const m = node.marks.find((mk) => mk.type === type)
      if (!m || !m.attrs.commentId || seen.has(m.attrs.commentId)) return
      seen.set(m.attrs.commentId, {
        id: m.attrs.commentId,
        author: m.attrs.author,
        date: m.attrs.date,
        text: m.attrs.text,
        color: m.attrs.color,
      })
    } else if (node.attrs?.commentId && !seen.has(node.attrs.commentId)) {
      // node comment (e.g. an image) — comment-prefixed attrs
      seen.set(node.attrs.commentId, {
        id: node.attrs.commentId,
        author: node.attrs.commentAuthor,
        date: node.attrs.commentDate,
        text: node.attrs.commentText,
        color: node.attrs.commentColor,
      })
    }
  })
  comments.value = [...seen.values()]
}
// How many cards tall the visible editor is → the rail's capacity before
// collapsing, plus whether there's room to sit the rail beside the sheet.
function measureCapacity() {
  const scroller = commentsWrap.value?.closest('.overflow-y-auto')
  const h = scroller?.clientHeight || 700
  railCapacity.value = Math.max(3, Math.floor(h / 132))
  if (!props.paper) {
    railOutside.value = false
    return
  }
  const cs = scroller ? getComputedStyle(scroller) : null
  const avail = scroller
    ? scroller.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0)
    : 0
  railOutside.value = avail >= props.paperWidth + RAIL_SPACE
}
// Anchor each card to the vertical position of its highlighted text.
function computeTops() {
  const wrap = commentsWrap.value
  if (!editorDom || !wrap) return
  measureCapacity()
  const wrapTop = wrap.getBoundingClientRect().top
  const tops = {}
  for (const c of comments.value) {
    const el = editorDom.querySelector(`[data-comment-id="${c.id}"]`)
    if (el) tops[c.id] = el.getBoundingClientRect().top - wrapTop
  }
  commentTops.value = tops
}
let topsRaf = null
function scheduleTops() {
  cancelAnimationFrame(topsRaf)
  topsRaf = requestAnimationFrame(computeTops)
}
// Anchors depend on the laid-out document, which isn't final at mount: the note's
// content arrives from the API, the webfont swaps in, images decode. Measuring
// once left every card parked at whatever the height was at that instant — the
// cards only snapped into place later, when some unrelated event re-ran the
// layout. Watch the editor box instead and re-anchor whenever it moves.
let layoutObserver = null
function watchLayout() {
  layoutObserver?.disconnect()
  if (typeof ResizeObserver === 'undefined' || !editorDom) return
  layoutObserver = new ResizeObserver(scheduleTops)
  layoutObserver.observe(editorDom)
  if (commentsWrap.value) layoutObserver.observe(commentsWrap.value)
}
function refreshComments() {
  rebuildComments()
  scheduleTops()
}
// Collapsed-mode popover: pin it beside the active comment's element (to its right,
// flipping left / clamping if it would spill off-screen). Recomputed when the active
// comment changes and on scroll / resize.
let hoverPosRaf = null
function updateHoverPos() {
  cancelAnimationFrame(hoverPosRaf)
  hoverPosRaf = requestAnimationFrame(() => {
    const id = activeCommentId.value
    if (!commentsOn.value || !commentsCollapsed.value || !id || !editorDom) {
      hoverPopStyle.value = null
      return
    }
    const el = editorDom.querySelector(`[data-comment-id="${id}"]`)
    if (!el) {
      hoverPopStyle.value = null
      return
    }
    const r = el.getBoundingClientRect()
    const CARD_W = 288
    const CARD_H = 260 // generous upper bound (composer height) for clamping
    const pad = 10
    let left = r.right + 12
    if (left + CARD_W > window.innerWidth - pad) left = r.left - CARD_W - 12
    left = Math.max(pad, left)
    let top = Math.max(pad, r.top)
    if (top + CARD_H > window.innerHeight - pad) top = Math.max(pad, window.innerHeight - pad - CARD_H)
    hoverPopStyle.value = { left: `${left}px`, top: `${top}px` }
  })
}
watch(activeCommentId, () => nextTick(updateHoverPos))
// Cross-highlight: hovering a comment mark / image (or its card) lights up its
// partner. All updates go through setHovered, whose small clear delay bridges the
// gap when moving between a highlight and its card so it doesn't flicker off — and
// (crucially) clears when the pointer leaves the editor for empty space.
let hoverClearTimer = null
function setHovered(id) {
  clearTimeout(hoverClearTimer)
  if (id == null) {
    hoverClearTimer = setTimeout(() => (hoveredCommentId.value = null), 90)
  } else if (hoveredCommentId.value !== id) {
    hoveredCommentId.value = id
  }
}
function onEditorMouseOver(e) {
  setHovered(e.target?.closest?.('[data-comment-id]')?.getAttribute('data-comment-id') || null)
}
function onEditorMouseLeave() {
  setHovered(null)
}
// Cross-highlighting is done with a generated CSS rule rather than by adding a
// class to the mark. The marks live inside ProseMirror's managed DOM, and
// mutating that DOM makes its observer re-read the document — which both loses
// the class again when PM re-renders the node, and can surface as a spurious
// "unsaved". A stylesheet touches nothing PM owns.
let hoverStyleEl = null
function paintHover(id) {
  if (!hoverStyleEl) {
    hoverStyleEl = document.createElement('style')
    document.head.appendChild(hoverStyleEl)
  }
  // Ids are generated by crypto.randomUUID(), but quote-escape anyway so a
  // hand-authored id can never break out of the selector.
  const safe = String(id ?? '').replace(/["\\]/g, '\\$&')
  hoverStyleEl.textContent = id
    ? `[data-comment-id="${safe}"].comment-mark{background:color-mix(in srgb,var(--c),transparent 60%)}
       [data-comment-id="${safe}"].image-comment{outline-color:var(--comment-color,#8b5cf6)}`
    : ''
}
watch(hoveredCommentId, paintHover)
const COMMENTABLE_NODES = ['image']
function addComment() {
  const ed = editor.value
  if (!ed) return
  const sel = ed.state.selection
  const onNode = sel.node && COMMENTABLE_NODES.includes(sel.node.type.name)
  if (!onNode && sel.empty) return // nothing selected to attach to
  const id = crypto?.randomUUID?.() || `c-${Date.now()}-${Math.random().toString(16).slice(2)}`
  const author = authorName()
  const date = new Date().toISOString()
  if (onNode) {
    // Comment on a node (e.g. an image) — comment-prefixed attrs via Commentable.
    ed.chain()
      .updateAttributes(sel.node.type.name, { commentId: id, commentAuthor: author, commentDate: date, commentText: '', commentColor: DEFAULT_COMMENT_COLOR })
      .run()
  } else {
    // NB: no .focus() here — we deliberately leave the editor unfocused so focus can
    // land on the comment composer (see CommentCard), not back in the document. The
    // mark still applies to the retained selection.
    ed.chain().setComment({ commentId: id, author, date, text: '', color: DEFAULT_COMMENT_COLOR }).run()
  }
  commentsOn.value = true
  editingCommentId.value = id // open the composer immediately (CommentCard focuses it)
}
function saveComment(id, text) {
  const t = (text || '').trim()
  if (!t) return deleteComment(id) // empty composer → discard the comment
  editor.value?.chain().updateComment(id, { text: t }).run()
  editingCommentId.value = null
}
function cancelComment(id) {
  const c = comments.value.find((x) => x.id === id)
  if (c && !c.text) deleteComment(id) // brand-new comment never saved → remove it
  else editingCommentId.value = null
}
function deleteComment(id) {
  editor.value?.chain().removeComment(id).run()
  if (editingCommentId.value === id) editingCommentId.value = null
}
function recolorComment(id, color) {
  editor.value?.chain().updateComment(id, { color }).run()
}

// Listeners + initial rebuild happen in the editor's onCreate (view is ready
// there). Here we just keep anchor positions + the hover popover fresh on resize /
// scroll and after first paint.
function onLayoutChange() {
  scheduleTops()
  updateHoverPos()
}
onMounted(() => {
  window.addEventListener('resize', onLayoutChange)
  window.addEventListener('scroll', updateHoverPos, true) // capture → catches nested scrollers
  scheduleTops()
  watchLayout()
  // The webfont swapping in reflows every line; re-anchor once it lands.
  document.fonts?.ready.then(scheduleTops)
})
// A comment appearing or disappearing changes what there is to anchor.
watch(comments, () => scheduleTops(), { deep: true })

// --- save hooks (parent owns the Save button + API call) -------------------
function markSaved() {
  if (editor.value) baseline = editor.value.getHTML()
  clearTimeout(autosaveTimer) // a save just happened → cancel any pending autosave
  isDirty.value = false
  emit('update:dirty', false)
}
function getHTML() {
  return editor.value?.getHTML() ?? ''
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve(r.result)
    r.onerror = reject
    r.readAsDataURL(file)
  })
}

// On save: "upload" every data-temp image (simulated here by inlining it as a
// self-contained data URL), then clear the temp flag so it persists.
async function finalizeTempImages() {
  const ed = editor.value
  if (!ed) return
  const temps = []
  ed.state.doc.descendants((node) => {
    if (node.type.name === 'image' && node.attrs.temp) temps.push(node.attrs.src)
  })
  if (!temps.length) return

  const resolved = {}
  for (const src of temps) {
    const file = tempFiles.get(src)
    resolved[src] = file ? await fileToDataUrl(file) : src
  }

  let tr = ed.state.tr
  ed.state.doc.descendants((node, pos) => {
    if (node.type.name === 'image' && node.attrs.temp) {
      tr = tr.setNodeMarkup(pos, undefined, {
        ...node.attrs,
        src: resolved[node.attrs.src] ?? node.attrs.src,
        temp: false,
      })
    }
  })
  ed.view.dispatch(tr)

  temps.forEach((src) => {
    if (tempFiles.has(src)) {
      URL.revokeObjectURL(src)
      tempFiles.delete(src)
    }
  })
}

defineExpose({ isDirty, markSaved, getHTML, finalizeTempImages })

watch(
  () => props.content,
  (val) => {
    const ed = editor.value
    if (ed && val !== ed.getHTML()) {
      ed.commands.setContent(val || '', { emitUpdate: false })
      markSaved() // new server-provided content → clean slate
      refreshComments()
    }
  },
)

onBeforeUnmount(() => {
  clearTimeout(autosaveTimer)
  cancelAnimationFrame(topsRaf)
  cancelAnimationFrame(hoverPosRaf)
  window.removeEventListener('resize', onLayoutChange)
  window.removeEventListener('scroll', updateHoverPos, true)
  editorDom?.removeEventListener('mouseover', onEditorMouseOver)
  editorDom?.removeEventListener('mouseleave', onEditorMouseLeave)
  clearTimeout(hoverClearTimer)
  hoverStyleEl?.remove()
  hoverStyleEl = null
  layoutObserver?.disconnect()
  editorDom = null
  tempFiles.forEach((_, src) => URL.revokeObjectURL(src))
  tempFiles.clear()
  editor.value?.destroy()
})

// --- toolbar model ---------------------------------------------------------
// Labels are i18n keys; menus are built when they open, so they speak the
// language picked at that moment.
const { t } = useI18n()
const BLOCKS = [
  { val: 'paragraph', label: 'editor.blocks.paragraph' },
  { val: 'h1', label: 'editor.blocks.h1' },
  { val: 'h2', label: 'editor.blocks.h2' },
  { val: 'h3', label: 'editor.blocks.h3' },
]
const FONTS = [
  { label: 'Default', css: '' },
  { label: 'Sans', css: 'ui-sans-serif, system-ui, sans-serif' },
  { label: 'Serif', css: 'ui-serif, Georgia, Cambria, serif' },
  { label: 'Mono', css: 'ui-monospace, SFMono-Regular, Menlo, monospace' },
]

function chain() {
  return editor.value.chain().focus()
}
function currentBlock() {
  const ed = editor.value
  if (!ed) return 'paragraph'
  if (ed.isActive('heading', { level: 1 })) return 'h1'
  if (ed.isActive('heading', { level: 2 })) return 'h2'
  if (ed.isActive('heading', { level: 3 })) return 'h3'
  return 'paragraph'
}
function blockLabel() {
  return t(BLOCKS.find((b) => b.val === currentBlock())?.label || 'editor.blocks.paragraph')
}
function setBlock(val) {
  const ed = editor.value
  if (!ed) return
  if (val === 'paragraph') {
    ed.chain().focus().setParagraph().run()
    return
  }
  ed.chain().focus().toggleHeading({ level: Number(val[1]) }).run()
  // Word-like: a NEW heading defaults to bold but stays fully toggleable — heading
  // weight is CSS-normal and the bold mark drives it. Bold the whole heading text,
  // then restore the caret.
  if (ed.isActive('heading')) {
    const $from = ed.state.selection.$from
    ed.chain()
      .setTextSelection({ from: $from.start(), to: $from.end() })
      .setBold()
      .setTextSelection($from.pos)
      .run()
  }
}
function setFont(css) {
  css ? chain().setFontFamily(css).run() : chain().unsetFontFamily().run()
}
// A node-selected block equation resizes via its own fontSize attribute (arrow
// onto the equation to select it); otherwise the size control drives the
// textStyle FontSize mark on the current text selection.
function selectedBlockMath() {
  const sel = editor.value?.state.selection
  if (sel?.node && sel.node.type.name === 'blockMath') return { pos: sel.from }
  return null
}
function currentSize() {
  const bm = selectedBlockMath()
  if (bm) return parseInt(editor.value.state.doc.nodeAt(bm.pos)?.attrs.fontSize) || 16
  return parseInt(editor.value?.getAttributes('textStyle').fontSize) || 16
}
function setSize(px) {
  const size = Math.min(72, Math.max(10, px))
  const bm = selectedBlockMath()
  if (bm) {
    editor.value.commands.command(({ tr, state }) => {
      const node = state.doc.nodeAt(bm.pos)
      if (!node) return false
      tr.setNodeMarkup(bm.pos, undefined, { ...node.attrs, fontSize: `${size}px` })
      return true
    })
    return
  }
  chain().setFontSize(`${size}px`).run()
}
// Apply a typed font size (Enter / blur). Parse the number and clamp via setSize;
// revert the field to the current size if it wasn't a number.
function applySizeInput(e) {
  const n = parseInt(e.target.value, 10)
  if (Number.isNaN(n)) e.target.value = currentSize()
  else setSize(n)
}
// Keep keystrokes out of any document-level handlers; apply on Enter.
function onSizeKey(e) {
  e.stopPropagation()
  if (e.key === 'Enter') {
    e.preventDefault()
    applySizeInput(e)
  }
}
function currentColor() {
  return editor.value?.getAttributes('textStyle').color || '#0f172a'
}
function currentHighlight() {
  return editor.value?.getAttributes('highlight').color || '#fef08a'
}
function setHighlight(color) {
  chain().setHighlight({ color }).run()
}
function unsetHighlight() {
  chain().unsetHighlight().run()
}

// --- block layout: alignment · line-height · spacing -----------------------
// Schema node names (blockMath / listItem), matching the extension configs.
const SPACING_TYPES = ['heading', 'paragraph', 'image', 'table', 'blockMath']
const LINE_HEIGHT_TYPES = ['paragraph', 'heading', 'listItem']

function currentAlign() {
  const ed = editor.value
  if (!ed) return 'left'
  for (const a of ['center', 'right', 'justify']) if (ed.isActive({ textAlign: a })) return a
  return 'left'
}
function setAlign(align) {
  chain().setTextAlign(align).run()
}

function currentLineHeight() {
  const ed = editor.value
  if (!ed) return null
  for (const t of LINE_HEIGHT_TYPES) {
    const lh = ed.getAttributes(t).lineHeight
    if (lh) return lh
  }
  return null
}
function setLineHeight(value) {
  value ? chain().setLineHeight(value).run() : chain().unsetLineHeight().run()
}

// The block the spacing controls act on: the node-selected block if one is
// selected, else the nearest ancestor block whose type supports spacing.
function spacingTarget() {
  const ed = editor.value
  if (!ed) return null
  const sel = ed.state.selection
  if (sel.node && SPACING_TYPES.includes(sel.node.type.name)) {
    return { type: sel.node.type.name, node: sel.node }
  }
  const $from = sel.$from
  for (let d = $from.depth; d >= 0; d--) {
    const n = $from.node(d)
    if (SPACING_TYPES.includes(n.type.name)) return { type: n.type.name, node: n }
  }
  return null
}
const toPx = (v) => parseInt(v, 10) || 0
function currentSpacing() {
  const a = spacingTarget()?.node.attrs ?? {}
  return {
    marginTop: toPx(a.marginTop),
    marginBottom: toPx(a.marginBottom),
    paddingTop: toPx(a.paddingTop),
    paddingBottom: toPx(a.paddingBottom),
  }
}
// Apply a spacing patch (e.g. { marginTop: '12px' } | { marginTop: null }) to the
// detected node type — exactly `updateAttributes(nodeType, { … })`.
function setSpacing(patch) {
  const t = spacingTarget()
  if (!t) return
  // No .focus(): every keystroke in the SpacingMenu input would otherwise pull the
  // caret back into the editor. updateAttributes acts on the retained selection.
  editor.value.chain().updateAttributes(t.type, patch).run()
}
function onInsertTable({ rows, cols }) {
  // Plain grid (no forced header row) — Word-like; users add a header via the
  // right-click menu, and any cell/row can be styled or filled independently.
  chain().insertTable({ rows, cols, withHeaderRow: false }).run()
}
function openImagePicker() {
  fileInput.value?.click()
}
function onFilePicked(e) {
  Array.from(e.target.files || []).forEach(insertTempImageFile)
  e.target.value = '' // allow re-picking the same file
}
// Open the math modal for a NEW equation (default) or to EDIT an existing node.
function openMathEditor(latex = '', edit = null) {
  mathInitial.value = latex
  mathEdit.value = edit
  mathOpen.value = true
}
// Insert a new block equation, or update the clicked node in place when editing.
function onMathInsert(latex) {
  const ed = editor.value
  if (!ed) return
  if (mathEdit.value) {
    const { pos, type } = mathEdit.value
    if (type === 'inlineMath') ed.commands.updateInlineMath({ latex, pos })
    else ed.commands.updateBlockMath({ latex, pos })
  } else {
    ed.chain().focus().insertBlockMath({ latex }).run()
  }
  mathEdit.value = null
  mathInitial.value = ''
}

// --- markdown blocks: lists · quote · code · link · rule · diagram ----------
// List style (bulletList / orderedList): quick toggle + per-list-style-type.
function currentListStyle(kind) {
  const type = kind === 'bullet' ? 'bulletList' : 'orderedList'
  return editor.value?.getAttributes(type).listStyleType || null
}
function toggleList(kind) {
  if (kind === 'bullet') chain().toggleBulletList().run()
  else chain().toggleOrderedList().run()
}
function setListStyle(kind, val) {
  const type = kind === 'bullet' ? 'bulletList' : 'orderedList'
  editor.value?.chain().focus().setListStyleType(type, val).run()
}
function toggleTaskList() {
  chain().toggleTaskList().run()
}

// Blockquote + its accent color.
function currentQuoteColor() {
  return editor.value?.getAttributes('blockquote').color || null
}
function toggleQuote() {
  chain().toggleBlockquote().run()
}
function setQuoteColor(color) {
  editor.value?.chain().focus().setBlockquoteColor(color).run()
}

// Inline code / code block / horizontal rule.
function toggleCode() {
  chain().toggleCode().run()
}
// Inline-code tint: read + apply the code mark's text/background color. When the
// caret merely sits inside a snippet (empty selection), extend to the whole span so
// the entire snippet recolors, not just future typing.
function currentCodeColor() {
  return editor.value?.getAttributes('code').color || null
}
function currentCodeBg() {
  return editor.value?.getAttributes('code').backgroundColor || null
}
function applyCodeStyle(patch) {
  const ed = editor.value
  if (!ed) return
  const cur = ed.getAttributes('code')
  const c = ed.chain().focus()
  if (ed.isActive('code') && ed.state.selection.empty) c.extendMarkRange('code')
  c.setMark('code', { ...cur, ...patch }).run()
}
function toggleCodeBlock() {
  chain().toggleCodeBlock().run()
}
function insertHr() {
  chain().setHorizontalRule().run()
}

// --- links -----------------------------------------------------------------
// Prefix a bare host with https:// and reject dangerous schemes, so a typed URL is
// always a safe, navigable href (StarterKit's Link only guards its own commands).
function normalizeUrl(raw) {
  let url = (raw || '').trim()
  if (!url) return ''
  if (/^\s*(javascript|data|vbscript|file):/i.test(url)) return '' // unsafe → drop
  const hasScheme = /^[a-z][a-z0-9+.-]*:/i.test(url)
  if (!hasScheme && !url.startsWith('/') && !url.startsWith('#') && !url.startsWith('mailto:')) {
    url = `https://${url}`
  }
  return url
}
function currentLinkHref() {
  return editor.value?.getAttributes('link').href || ''
}
function openLinkEditor() {
  const ed = editor.value
  if (!ed) return
  linkInitial.value = currentLinkHref()
  linkEditing.value = ed.isActive('link')
  linkOpen.value = true
}
function applyLink(raw) {
  const ed = editor.value
  const href = normalizeUrl(raw)
  if (!ed || !href) return
  const { empty } = ed.state.selection
  if (empty && !ed.isActive('link')) {
    // No selection and not on a link → insert the URL as its own linked text.
    ed.chain()
      .focus()
      .insertContent({ type: 'text', text: href, marks: [{ type: 'link', attrs: { href } }] })
      .run()
  } else {
    ed.chain().focus().extendMarkRange('link').setLink({ href }).run()
  }
}
function removeLink() {
  editor.value?.chain().focus().extendMarkRange('link').unsetLink().run()
}

// --- mermaid diagrams ------------------------------------------------------
// Open the diagram editor for a NEW diagram (default) or to EDIT the node at `pos`.
function openMermaidEditor(code = '', layout = {}, edit = null) {
  mermaidInitial.value = code
  mermaidLayout.value = layout || {}
  mermaidEdit.value = edit
  mermaidOpen.value = true
}
function onMermaidInsert(code, layout) {
  const ed = editor.value
  if (!ed) return
  const lay = layout && Object.keys(layout).length ? layout : null
  if (mermaidEdit.value) ed.commands.updateMermaid(code, lay, mermaidEdit.value.pos)
  else ed.chain().focus().insertMermaid(code, lay).run()
  mermaidEdit.value = null
  mermaidInitial.value = ''
  mermaidLayout.value = {}
}

// --- ask Zinvest about the selection -----------------------------------------
// The editor has its own menu over a selection, so the app-wide "Ask Zinvest"
// pill stays out of the way here and the same action sits first in this menu.
const askAI = useAskAI()
function askAboutSelection() {
  const { from, to } = editor.value.state.selection
  const text = editor.value.state.doc.textBetween(from, to, ' ')
  let rect = null
  try {
    rect = window.getSelection()?.getRangeAt(0)?.getBoundingClientRect() || null
  } catch {
    rect = null
  }
  askAI.ask(text, rect)
}

// --- text bubble-menu visibility -------------------------------------------
function textShouldShow({ editor, state }) {
  const sel = state.selection
  if (sel.empty || sel.from === sel.to) return false
  if (sel.node) return false // node selection (e.g. an image) → no text menu
  return !editor.isActive('table')
}

// --- right-click context menu ----------------------------------------------
// Table controls (and text formatting) now live here instead of a bubble menu.
const ctx = ref({ open: false, x: 0, y: 0, items: [] })

// Text / highlight swatches for the context-menu color submenus.
const TEXT_COLORS = ['#0f172a', '#dc2626', '#ea580c', '#d97706', '#16a34a', '#2563eb', '#7c3aed', '#db2777', '#ffffff']
const HIGHLIGHT_COLORS = ['#fef08a', '#fde68a', '#fecaca', '#fbcfe8', '#bbf7d0', '#a7f3d0', '#bfdbfe', '#ddd6fe']
const QUOTE_COLORS = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#64748b']
const CODE_TEXT_COLORS = ['#db2777', '#dc2626', '#ea580c', '#d97706', '#16a34a', '#0891b2', '#2563eb', '#7c3aed', '#0f172a']
const CODE_BG_COLORS = ['#fee2e2', '#ffedd5', '#fef9c3', '#dcfce7', '#cffafe', '#dbeafe', '#f3e8ff', '#e2e8f0', '#1e293b']

// Drop leading / trailing / consecutive dividers, so conditionally-hidden groups
// never leave a stray separator behind.
function cleanDividers(items) {
  const out = []
  for (const it of items) {
    if (it?.type === 'divider' && (!out.length || out[out.length - 1]?.type === 'divider')) continue
    out.push(it)
  }
  while (out.length && out[out.length - 1]?.type === 'divider') out.pop()
  return out
}

// The formatting menu shown on right-click. Items adapt to the current selection so
// only actions that would actually do something are offered:
//   • inside inline code → no character formatting (bold/color/highlight have no
//     visible effect there), but keep the inline-code controls to recolor/remove it;
//   • with a text selection → hide the "Insert" block actions (you're styling text,
//     not inserting), but keep block-turning ones like blockquote / inline code;
//   • on a node selection (image, diagram…) → only node-relevant actions.
// Inside a table it also gains a "Table ▸" hover submenu.
function formattingItems() {
  const ed = editor.value
  const sel = ed?.state.selection
  const onNode = !!sel?.node
  const hasSelection = !!sel && !sel.empty && !onNode
  const inCode = ed?.isActive('code')
  const commentableNode = onNode && COMMENTABLE_NODES.includes(sel.node.type.name)
  const hl = ed?.isActive('highlight') ? currentHighlight() : ''
  const items = [
    { label: 'Undo', icon: 'undo', run: () => chain().undo().run(), disabled: !ed?.can().undo() },
    { label: 'Redo', icon: 'redo', run: () => chain().redo().run(), disabled: !ed?.can().redo() },
    { type: 'divider' },
  ]

  // Character formatting — pointless inside inline code or on a node selection.
  if (!inCode && !onNode) {
    items.push(
      { label: 'Bold', icon: 'bold', active: ed?.isActive('bold'), run: () => chain().toggleBold().run() },
      { label: 'Italic', icon: 'italic', active: ed?.isActive('italic'), run: () => chain().toggleItalic().run() },
      { label: 'Underline', icon: 'underline', active: ed?.isActive('underline'), run: () => chain().toggleUnderline().run() },
      { label: 'Strikethrough', icon: 'strike', active: ed?.isActive('strike'), run: () => chain().toggleStrike().run() },
      { type: 'divider' },
      {
        label: t('editor.textColor'),
        icon: 'type',
        dot: currentColor(),
        children: [
          { type: 'swatches', label: t('editor.textColor'), colors: TEXT_COLORS, current: currentColor(), onPick: (c) => chain().setColor(c).run(), onClear: () => chain().unsetColor().run() },
        ],
      },
      {
        label: 'Highlight',
        icon: 'highlighter',
        dot: hl || null,
        children: [
          { type: 'swatches', label: 'Highlight', colors: HIGHLIGHT_COLORS, current: hl, onPick: (c) => chain().setHighlight({ color: c }).run(), onClear: () => chain().unsetHighlight().run() },
        ],
      },
      { type: 'divider' },
    )
  }

  // Text-level structure — kept even on a normal selection (the user may want to
  // turn selected text into a link / code / quote). Hidden on a node selection.
  if (!onNode) {
    items.push(
      { label: 'Link', icon: 'link', active: ed?.isActive('link'), run: () => openLinkEditor() },
      {
        label: t('editor.inlineCode'),
        icon: 'code',
        active: inCode,
        dot: currentCodeColor(),
        children: [
          { label: inCode ? t('editor.removeCode') : t('editor.makeCode'), icon: 'code', run: () => toggleCode() },
          { type: 'divider' },
          { type: 'swatches', label: t('editor.textColor'), colors: CODE_TEXT_COLORS, current: currentCodeColor(), onPick: (c) => applyCodeStyle({ color: c }), onClear: () => applyCodeStyle({ color: null }) },
          { type: 'swatches', label: 'Background', colors: CODE_BG_COLORS, current: currentCodeBg(), onPick: (c) => applyCodeStyle({ backgroundColor: c }), onClear: () => applyCodeStyle({ backgroundColor: null }) },
        ],
      },
      {
        label: 'Blockquote',
        icon: 'quote',
        active: ed?.isActive('blockquote'),
        dot: currentQuoteColor(),
        children: [
          { type: 'swatches', label: t('editor.quoteColor'), colors: QUOTE_COLORS, current: currentQuoteColor(), onPick: (c) => setQuoteColor(c), onClear: () => (ed?.isActive('blockquote') ? toggleQuote() : null) },
          { type: 'divider' },
          { label: ed?.isActive('blockquote') ? t('editor.removeQuote') : t('editor.plainQuote'), icon: 'quote', run: () => toggleQuote() },
        ],
      },
    )
  }

  // Insert-only actions — hidden when text is selected (probably not inserting) or a
  // node is selected.
  if (!hasSelection && !onNode) {
    items.push({
      label: 'Insert',
      icon: 'plus',
      children: [
        { label: t('editor.codeBlock'), icon: 'braces', active: ed?.isActive('codeBlock'), run: () => toggleCodeBlock() },
        { label: t('editor.taskList'), icon: 'taskList', active: ed?.isActive('taskList'), run: () => toggleTaskList() },
        { label: 'Diagram', icon: 'diagram', run: () => openMermaidEditor() },
        { label: t('editor.divider'), icon: 'minus', run: () => insertHr() },
      ],
    })
  }

  items.push({ type: 'divider' })
  if (!onNode) items.push({ label: t('editor.clearFormatting'), icon: 'eraser', run: () => chain().unsetAllMarks().run() })
  items.push({ label: t('editor.addComment'), icon: 'comment', active: ed?.isActive('comment'), run: () => addComment(), disabled: !hasSelection && !commentableNode })

  // In a table, append the table controls as a hover submenu.
  if (ed?.isActive('table')) {
    items.push({ type: 'divider' }, { label: 'Table', icon: 'table', children: tableMenuItems() })
  }
  return cleanDividers(items)
}
// Light cell fills (readable with dark text) for the cell-color swatches.
const CELL_COLORS = ['#fee2e2', '#ffedd5', '#fef9c3', '#dcfce7', '#dbeafe', '#f3e8ff', '#e2e8f0']
function currentCellColor() {
  const ed = editor.value
  return ed?.getAttributes('tableCell').backgroundColor || ed?.getAttributes('tableHeader').backgroundColor || ''
}

function tableMenuItems() {
  return [
    {
      type: 'swatches',
      label: t('editor.table.cellColor'),
      colors: CELL_COLORS,
      current: currentCellColor(),
      onPick: (c) => chain().setCellAttribute('backgroundColor', c).run(),
      onClear: () => chain().setCellAttribute('backgroundColor', null).run(),
    },
    { type: 'divider' },
    { label: t('editor.table.rowAbove'), icon: 'rows', run: () => chain().addRowBefore().run() },
    { label: t('editor.table.rowBelow'), icon: 'rows', run: () => chain().addRowAfter().run() },
    { label: t('editor.table.deleteRow'), icon: 'rows', run: () => chain().deleteRow().run() },
    { type: 'divider' },
    { label: t('editor.table.colLeft'), icon: 'columns', run: () => chain().addColumnBefore().run() },
    { label: t('editor.table.colRight'), icon: 'columns', run: () => chain().addColumnAfter().run() },
    { label: t('editor.table.deleteColumn'), icon: 'columns', run: () => chain().deleteColumn().run() },
    { type: 'divider' },
    { label: t('editor.table.mergeCells'), icon: 'columns', run: () => chain().mergeCells().run() },
    { label: t('editor.table.splitCell'), icon: 'columns', run: () => chain().splitCell().run() },
    { label: t('editor.table.headerRow'), icon: 'rows', run: () => chain().toggleHeaderRow().run() },
    { type: 'divider' },
    { label: t('editor.table.deleteTable'), icon: 'trash', danger: true, run: () => chain().deleteTable().run() },
  ]
}

function onContextMenu(e) {
  // The template's `.prevent` modifier already suppressed the native menu. Show our
  // formatting menu everywhere (Word-like); inside a table it also carries a Table
  // submenu (see formattingItems).
  const ed = editor.value
  if (!ed) return
  ctx.value = { open: true, x: e.clientX, y: e.clientY, items: formattingItems() }
}
function closeContext() {
  ctx.value.open = false
}

// --- class helpers ---------------------------------------------------------
function btn(active) {
  return [
    'inline-flex items-center justify-center rounded-lg p-2 transition-all duration-200 ease-in-out',
    active
      ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300'
      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2',
  ]
}
const TRIGGER =
  'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-slate-700 transition-all duration-200 ease-in-out hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-surface-2'
const ITEM =
  'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-slate-700 transition-all duration-200 ease-in-out hover:bg-slate-100 disabled:pointer-events-none disabled:opacity-40 dark:text-slate-200 dark:hover:bg-surface-2'
</script>

<template>
  <div class="flex h-full flex-col bg-white dark:bg-surface">
    <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFilePicked" />

    <!-- Static toolbar: structural controls only (text/table controls are in bubbles) -->
    <div
      v-if="editor && toolbar"
      class="flex shrink-0 flex-wrap items-center gap-1 border-b border-slate-200 px-3 py-2 dark:border-hairline"
    >
      <!-- Undo / redo -->
      <button
        type="button"
        :class="[btn(false), 'disabled:pointer-events-none disabled:opacity-40']"
        :title="$t('editor.undo')"
        :disabled="!editor.can().undo()"
        @click="chain().undo().run()"
      >
        <Icon name="undo" class="h-4 w-4" />
      </button>
      <button
        type="button"
        :class="[btn(false), 'disabled:pointer-events-none disabled:opacity-40']"
        :title="$t('editor.redo')"
        :disabled="!editor.can().redo()"
        @click="chain().redo().run()"
      >
        <Icon name="redo" class="h-4 w-4" />
      </button>

      <span class="mx-1 h-6 w-px bg-slate-200 dark:bg-hairline" />

      <!-- Block type -->
      <ToolbarDropdown panel-class="min-w-[11rem]">
        <template #trigger="{ toggle, open }">
          <button type="button" :class="[TRIGGER, open ? 'bg-slate-100 dark:bg-surface-2' : '']" @click="toggle">
            {{ blockLabel() }}
            <Icon name="chevronDown" class="h-3.5 w-3.5 opacity-60" />
          </button>
        </template>
        <template #panel="{ close }">
          <button
            v-for="b in BLOCKS"
            :key="b.val"
            type="button"
            :class="[ITEM, currentBlock() === b.val ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300' : '']"
            @click="setBlock(b.val), close()"
          >
            <span
              :class="{
                'text-lg font-extrabold': b.val === 'h1',
                'text-base font-bold': b.val === 'h2',
                'text-sm font-semibold': b.val === 'h3',
              }"
            >{{ $t(b.label) }}</span>
          </button>
        </template>
      </ToolbarDropdown>

      <!-- Font family -->
      <ToolbarDropdown panel-class="min-w-[10rem]">
        <template #trigger="{ toggle, open }">
          <button type="button" :class="[TRIGGER, open ? 'bg-slate-100 dark:bg-surface-2' : '']" :title="$t('editor.fontFamily')" @click="toggle">
            <Icon name="type" class="h-4 w-4 opacity-70" />
            <Icon name="chevronDown" class="h-3.5 w-3.5 opacity-60" />
          </button>
        </template>
        <template #panel="{ close }">
          <button
            v-for="f in FONTS"
            :key="f.label"
            type="button"
            :class="ITEM"
            :style="{ fontFamily: f.css || undefined }"
            @click="setFont(f.css), close()"
          >
            {{ f.label === 'Default' ? $t('editor.fontDefault') : f.label }}
          </button>
        </template>
      </ToolbarDropdown>

      <span class="mx-1 h-6 w-px bg-slate-200 dark:bg-hairline" />

      <!-- Font size -->
      <div class="flex items-center rounded-lg border border-slate-200 dark:border-hairline">
        <button
          type="button"
          class="px-2 py-1 text-slate-600 transition-all duration-200 ease-in-out hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2"
          :title="$t('editor.fontSmaller')"
          @click="setSize(currentSize() - 1)"
        >−</button>
        <input
          type="text"
          inputmode="numeric"
          class="w-9 bg-transparent text-center text-sm tabular-nums text-slate-700 focus:outline-none dark:text-slate-200"
          :value="currentSize()"
          :title="$t('editor.fontSize')"
          @focus="$event.target.select()"
          @keydown="onSizeKey($event)"
          @blur="applySizeInput($event)"
        />
        <button
          type="button"
          class="px-2 py-1 text-slate-600 transition-all duration-200 ease-in-out hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2"
          :title="$t('editor.fontBigger')"
          @click="setSize(currentSize() + 1)"
        >+</button>
      </div>

      <span class="mx-1 h-6 w-px bg-slate-200 dark:bg-hairline" />

      <!-- Character formatting: B / I / U / S + text & highlight color -->
      <button type="button" :class="btn(editor.isActive('bold'))" :title="$t('editor.bold')" @click="chain().toggleBold().run()">
        <Icon name="bold" class="h-4 w-4" />
      </button>
      <button type="button" :class="btn(editor.isActive('italic'))" :title="$t('editor.italic')" @click="chain().toggleItalic().run()">
        <Icon name="italic" class="h-4 w-4" />
      </button>
      <button type="button" :class="btn(editor.isActive('underline'))" :title="$t('editor.underline')" @click="chain().toggleUnderline().run()">
        <Icon name="underline" class="h-4 w-4" />
      </button>
      <button type="button" :class="btn(editor.isActive('strike'))" :title="$t('editor.strike')" @click="chain().toggleStrike().run()">
        <Icon name="strike" class="h-4 w-4" />
      </button>
      <ColorPickerMenu
        :color="currentColor()"
        @select="chain().setColor($event).run()"
        @reset="chain().unsetColor().run()"
      />
      <HighlightPickerMenu :color="currentHighlight()" @select="setHighlight" @reset="unsetHighlight" />

      <span class="mx-1 h-6 w-px bg-slate-200 dark:bg-hairline" />

      <!-- Lists (toggle + numbering/bullet style) + task list -->
      <ListMenu
        kind="bullet"
        :active="editor.isActive('bulletList')"
        :active-style="currentListStyle('bullet')"
        @toggle="toggleList('bullet')"
        @style="setListStyle('bullet', $event)"
      />
      <ListMenu
        kind="ordered"
        :active="editor.isActive('orderedList')"
        :active-style="currentListStyle('ordered')"
        @toggle="toggleList('ordered')"
        @style="setListStyle('ordered', $event)"
      />
      <button type="button" :class="btn(editor.isActive('taskList'))" :title="$t('editor.taskList')" @click="toggleTaskList()">
        <Icon name="taskList" class="h-4 w-4" />
      </button>

      <span class="mx-1 h-6 w-px bg-slate-200 dark:bg-hairline" />

      <!-- Blocks: quote · inline code · code block · link -->
      <QuoteMenu
        :active="editor.isActive('blockquote')"
        :active-color="currentQuoteColor()"
        @toggle="toggleQuote()"
        @color="setQuoteColor($event)"
      />
      <CodeStyleMenu
        :active="editor.isActive('code')"
        :active-color="currentCodeColor()"
        :active-bg="currentCodeBg()"
        @toggle="toggleCode()"
        @color="applyCodeStyle({ color: $event })"
        @background="applyCodeStyle({ backgroundColor: $event })"
        @reset="applyCodeStyle({ color: null, backgroundColor: null })"
      />
      <button type="button" :class="btn(editor.isActive('codeBlock'))" :title="$t('editor.codeBlock')" @click="toggleCodeBlock()">
        <Icon name="braces" class="h-4 w-4" />
      </button>
      <button type="button" :class="btn(editor.isActive('link'))" :title="$t('editor.link')" @click="openLinkEditor()">
        <Icon name="link" class="h-4 w-4" />
      </button>

      <span class="mx-1 h-6 w-px bg-slate-200 dark:bg-hairline" />

      <!-- Block layout: alignment · line spacing · margins & padding -->
      <AlignmentMenu :active="currentAlign()" @select="setAlign" />
      <LineSpacingMenu :active="currentLineHeight()" @select="setLineHeight" />
      <SpacingMenu :values="currentSpacing()" :disabled="!spacingTarget()" @update="setSpacing" />

      <span class="mx-1 h-6 w-px bg-slate-200 dark:bg-hairline" />

      <!-- Table: visual size picker -->
      <ToolbarDropdown panel-class="w-auto">
        <template #trigger="{ toggle, open }">
          <button
            type="button"
            :class="[btn(editor.isActive('table')), open ? 'bg-slate-100 dark:bg-surface-2' : '']"
            :title="$t('editor.insertTable')"
            @click="toggle"
          >
            <Icon name="table" class="h-4 w-4" />
          </button>
        </template>
        <template #panel="{ close }">
          <TableGridMenu @select="onInsertTable($event), close()" />
        </template>
      </ToolbarDropdown>

      <!-- Image (opens the local file picker) -->
      <button type="button" :class="btn(false)" :title="$t('editor.insertImage')" @click="openImagePicker">
        <Icon name="image" class="h-4 w-4" />
      </button>

      <!-- Math (opens the visual editor for a new equation) -->
      <button type="button" :class="btn(false)" :title="$t('editor.insertEquation')" @click="openMathEditor()">
        <Icon name="sigma" class="h-4 w-4" />
      </button>

      <!-- Horizontal rule -->
      <button type="button" :class="btn(false)" :title="$t('editor.divider')" @click="insertHr()">
        <Icon name="minus" class="h-4 w-4" />
      </button>

      <!-- Diagram (Mermaid) -->
      <button type="button" :class="btn(false)" :title="$t('editor.insertDiagram')" @click="openMermaidEditor()">
        <Icon name="diagram" class="h-4 w-4" />
      </button>

      <span class="mx-1 h-6 w-px bg-slate-200 dark:bg-hairline" />

      <!-- Comments: toggle the highlights + right-margin cards on/off -->
      <button type="button" :class="btn(commentsOn)" :title="$t('editor.showComments')" @click="commentsOn = !commentsOn">
        <Icon name="comment" class="h-4 w-4" />
      </button>
    </div>

    <!-- Text bubble menu: shown only for a text selection outside tables -->
    <BubbleMenu
      v-if="editor"
      :editor="editor"
      plugin-key="textMenu"
      :should-show="textShouldShow"
      :options="{ placement: 'top', offset: 8 }"
    >
      <div class="flex items-center gap-0.5 rounded-xl border border-slate-200 bg-white p-1 shadow-float dark:border-hairline dark:bg-surface">
        <button
          type="button"
          class="flex h-8 items-center gap-1.5 rounded-lg pl-1 pr-2 text-xs font-bold text-brand-700 transition hover:bg-brand-50 dark:text-brand-300 dark:hover:bg-brand-500/10"
          :title="$t('askAI.button')"
          @click="askAboutSelection()"
        >
          <img src="/mascot/ai-avatar-96.webp" alt="" class="h-6 w-6 rounded-[28%]" draggable="false" />
          <span class="hidden sm:inline">{{ $t('askAI.short') }}</span>
        </button>
        <span class="mx-0.5 h-6 w-px bg-slate-200 dark:bg-hairline" />
        <button type="button" :class="btn(editor.isActive('bold'))" :title="$t('editor.bold')" @click="chain().toggleBold().run()">
          <Icon name="bold" class="h-4 w-4" />
        </button>
        <button type="button" :class="btn(editor.isActive('italic'))" :title="$t('editor.italic')" @click="chain().toggleItalic().run()">
          <Icon name="italic" class="h-4 w-4" />
        </button>
        <button type="button" :class="btn(editor.isActive('underline'))" :title="$t('editor.underline')" @click="chain().toggleUnderline().run()">
          <Icon name="underline" class="h-4 w-4" />
        </button>
        <button type="button" :class="btn(editor.isActive('strike'))" :title="$t('editor.strike')" @click="chain().toggleStrike().run()">
          <Icon name="strike" class="h-4 w-4" />
        </button>
        <button type="button" :class="btn(editor.isActive('code'))" :title="$t('editor.inlineCode')" @click="toggleCode()">
          <Icon name="code" class="h-4 w-4" />
        </button>
        <button type="button" :class="btn(editor.isActive('highlight'))" :title="$t('editor.highlight')" @click="chain().toggleHighlight().run()">
          <Icon name="highlighter" class="h-4 w-4" />
        </button>
        <span class="mx-0.5 h-6 w-px bg-slate-200 dark:bg-hairline" />
        <ColorPickerMenu
          :color="currentColor()"
          @select="chain().setColor($event).run()"
          @reset="chain().unsetColor().run()"
        />
        <button type="button" :class="btn(editor.isActive('link'))" :title="$t('editor.link')" @click="openLinkEditor()">
          <Icon name="link" class="h-4 w-4" />
        </button>
        <span class="mx-0.5 h-6 w-px bg-slate-200 dark:bg-hairline" />
        <button type="button" :class="btn(editor.isActive('comment'))" :title="$t('editor.addComment')" @click="addComment()">
          <Icon name="comment" class="h-4 w-4" />
        </button>
      </div>
    </BubbleMenu>

    <!-- Document body: full-pane, fluid width. Right-click opens a contextual
         menu (table controls in a table, text formatting on a selection). -->
    <div
      class="min-h-0 flex-1 overflow-y-auto"
      :class="paper ? 'bg-slate-100 px-4 py-8 dark:bg-slate-950/40' : ''"
      v-os
      @contextmenu.prevent="onContextMenu"
    >
      <!-- Positioning context for the rail. On the paper editor it is wider than
           the sheet when there's room, so the cards sit *beside* the paper
           instead of on top of it; the sheet itself is the inner .zx-paper. -->
      <div
        ref="commentsWrap"
        class="relative"
        :class="[
          commentsOn ? 'comments-on' : 'comments-off',
          // Reserving margin inside the text is only needed when the cards
          // overlay the document rather than sitting outside it.
          railShown && !(paper && railOutside) ? 'reserve-comments' : '',
          paper ? 'mx-auto' : '',
        ]"
        :style="paper ? { width: stageWidth + 'px', maxWidth: '100%' } : null"
      >
        <div
          :class="paper ? 'zx-paper rounded-xl bg-white shadow-float dark:bg-surface' : ''"
          :style="
            paper
              ? {
                  width: paperWidth + 'px',
                  maxWidth: '100%',
                  minHeight: PAGE_MIN_HEIGHT + 'px',
                }
              : null
          "
        >
          <EditorContent v-if="editor" :editor="editor" :class="paper ? '' : 'h-full'" />
        </div>
        <!-- Rail: shown while the comments comfortably fit. Past that we collapse to
             the hover popover below so cards never drift far from their text. -->
        <CommentsRail
          v-if="railShown"
          :comments="comments"
          :tops="commentTops"
          :editing-id="editingCommentId"
          :hovered-id="hoveredCommentId"
          @edit="editingCommentId = $event"
          @save="saveComment"
          @cancel="cancelComment"
          @delete="deleteComment"
          @recolor="recolorComment"
          @hover="setHovered"
        />
      </div>
    </div>

    <!-- Right-click context menu -->
    <ContextMenu :open="ctx.open" :x="ctx.x" :y="ctx.y" :items="ctx.items" @close="closeContext" />

    <!-- Collapsed-comments popover: when too many comments to lay out, the hovered
         (or actively composed) one appears here, pinned beside its highlight/image. -->
    <Teleport to="body">
      <div v-if="commentsOn && commentsCollapsed && activeComment && hoverPopStyle" class="fixed z-[90] w-72" :style="hoverPopStyle">
        <CommentCard
          :comment="activeComment"
          :editing="editingCommentId === activeComment.id"
          :active="true"
          @edit="editingCommentId = $event"
          @save="saveComment"
          @cancel="cancelComment"
          @delete="deleteComment"
          @recolor="recolorComment"
          @hover="setHovered"
        />
      </div>
    </Teleport>

    <!-- Visual math builder (prefilled with the clicked node's LaTeX when editing) -->
    <MathEditorModal v-if="mathMounted" v-model="mathOpen" :initial-latex="mathInitial" @insert="onMathInsert" />

    <!-- Link editor (add / edit / remove a hyperlink) -->
    <LinkModal
      v-model="linkOpen"
      :initial-url="linkInitial"
      :editing="linkEditing"
      @apply="applyLink"
      @remove="removeLink"
    />

    <!-- Diagram editor (visual flowchart canvas + mermaid source + live preview) -->
    <MermaidEditorModal
      v-if="mermaidMounted"
      v-model="mermaidOpen"
      :initial-code="mermaidInitial"
      :initial-layout="mermaidLayout"
      @insert="onMermaidInsert"
    />
  </div>
</template>

<style scoped>
/* Tables ------------------------------------------------------------------ */
:deep(.ProseMirror table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1rem 0;
  table-layout: fixed;
  overflow: hidden;
}
:deep(.ProseMirror td),
:deep(.ProseMirror th) {
  position: relative;
  min-width: 6rem;
  border: 1px solid var(--border);
  padding: 0.5rem 0.75rem;
  vertical-align: top;
}
/* Header cells aren't force-styled — a table starts as a plain grid and any cell
   can be filled/bolded on its own (Word-like). Neutralize prose's th defaults, so
   toggling a header row just re-tags cells without locking in bold/fill. */
:deep(.ProseMirror th) {
  background: transparent;
  font-weight: 400;
  text-align: left;
}
:deep(.ProseMirror td > *),
:deep(.ProseMirror th > *) {
  margin: 0;
}
:deep(.ProseMirror .selectedCell::after) {
  content: '';
  position: absolute;
  inset: 0;
  background: color-mix(in srgb, var(--brand-500), transparent 84%);
  pointer-events: none;
}

/* Headings ---------------------------------------------------------------- */
/* Heading weight is NOT hard-coded bold; the Bold mark (<strong>) drives it, so
   bold is fully toggleable on a heading. A new heading is auto-bolded on insert
   (see setBlock), but the user can turn it off — down to normal weight. */
:deep(.ProseMirror h1),
:deep(.ProseMirror h2),
:deep(.ProseMirror h3),
:deep(.ProseMirror h4) {
  font-weight: 400;
}
:deep(.ProseMirror strong) {
  font-weight: 700;
}

/* Math -------------------------------------------------------------------- */
:deep(.tiptap-mathematics-render) {
  padding: 0 0.15rem;
  cursor: pointer;
  border-radius: 0.25rem;
  transition: background 0.2s ease-in-out;
  /* Respect the FontSize extension: KaTeX sizes relative to its container, so
     inheriting the surrounding font-size lets a highlighted equation scale when
     the user bumps the text size in the toolbar. */
  font-size: inherit;
}
:deep(.tiptap-mathematics-render:hover) {
  background: color-mix(in srgb, var(--brand-500), transparent 88%);
}
/* Block math is wrapped in an outer block that owns the vertical rhythm (plus any
   custom Spacing margins/padding) and the text-align that positions the hug box.
   This default margin is overridden by the inline styles Spacing sets. */
:deep(.tiptap-math-block) {
  margin: 1rem 0;
}
/* Block math: hug the equation (fit-content) instead of stretching full-width,
   so the highlight/rounded box wraps the formula, not the whole editor. Being
   inline-flex (inline-level) lets the outer block's text-align align it. */
:deep(.tiptap-mathematics-render[data-type='block-math']) {
  display: inline-flex;
  width: fit-content;
  max-width: 100%;
  padding: 0.3rem 0.6rem;
  background: var(--surface-2);
  border-radius: 0.6rem;
}
:deep(.tiptap-mathematics-render[data-type='block-math']:hover) {
  background: color-mix(in srgb, var(--brand-500), transparent 84%);
}
/* Node-selected (arrow onto it) → resizable from the toolbar size stepper. The
   selection class lands on the outer block, so target the inner hug box. */
:deep(.tiptap-math-block.ProseMirror-selectednode .tiptap-mathematics-render) {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
  background: color-mix(in srgb, var(--brand-500), transparent 88%);
}

/* Comments ---------------------------------------------------------------- */
/* Highlighted commented text, tinted with the comment's own color (set inline as
   --comment-color). Hovering the text — or its card (.comment-hover) — deepens it. */
:deep(.comment-mark) {
  --c: var(--comment-color, #8b5cf6);
  background: color-mix(in srgb, var(--c), transparent 82%);
  border-radius: 0.15rem;
  box-shadow: inset 0 -0.14em 0 color-mix(in srgb, var(--c), transparent 55%);
  cursor: pointer;
  transition: background 0.15s ease;
}
/* Cross-highlight from a card is applied by a generated rule (see paintHover),
   not a class — the marks are ProseMirror's DOM and we don't write to it. */
:deep(.comment-mark:hover) {
  background: color-mix(in srgb, var(--c), transparent 60%);
}
:deep(.comments-off .comment-mark) {
  background: transparent;
  box-shadow: none;
  cursor: text;
}
/* A commented image / node: a colored ring in the comment's color (deeper when it
   or its card is hovered). Hidden when comments are toggled off. */
:deep(.image-comment) {
  outline: 2px solid color-mix(in srgb, var(--comment-color, #8b5cf6), transparent 35%);
  outline-offset: 3px;
  border-radius: 0.5rem;
  cursor: pointer;
}
:deep(.image-comment:hover) {
  outline-color: var(--comment-color, #8b5cf6);
}
:deep(.comments-off .image-comment) {
  outline: none;
  cursor: default;
}
/* Reserve the right margin for the comment cards while comments are shown. */
:deep(.reserve-comments .ProseMirror) {
  padding-right: 19rem;
}
</style>
