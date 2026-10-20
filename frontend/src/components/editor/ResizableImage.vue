<script setup>
// Custom Tiptap NodeView giving images native-feeling drag-to-resize. When the
// node is selected it shows an outline + four corner handles; dragging a handle
// translates the horizontal mouse delta into the node's `width` attribute.
import { computed, ref } from 'vue'
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'

const props = defineProps(nodeViewProps)

const wrapper = ref(null)
const img = ref(null)
const dragging = ref(false)

const MIN_W = 80

// Each corner: which way a rightward mouse move pushes the width. Right-side
// handles grow with +x, left-side handles grow with −x.
const HANDLES = [
  { key: 'nw', dir: -1, pos: 'left-0 top-0 -translate-x-1/2 -translate-y-1/2 cursor-nwse-resize' },
  { key: 'ne', dir: 1, pos: 'right-0 top-0 translate-x-1/2 -translate-y-1/2 cursor-nesw-resize' },
  { key: 'sw', dir: -1, pos: 'left-0 bottom-0 -translate-x-1/2 translate-y-1/2 cursor-nesw-resize' },
  { key: 'se', dir: 1, pos: 'right-0 bottom-0 translate-x-1/2 translate-y-1/2 cursor-nwse-resize' },
]

const widthStyle = computed(() =>
  props.node.attrs.width ? { width: `${props.node.attrs.width}px` } : { width: 'auto' },
)

// Alignment + spacing come from the TextAlign / Spacing global attributes. A
// custom NodeView doesn't auto-apply their renderHTML, so we paint them on the
// outer block ourselves: text-align positions the inline-block image frame, and
// the margin/padding attrs override the default `my-4` rhythm when set.
const blockStyle = computed(() => ({
  textAlign: props.node.attrs.textAlign || undefined,
  marginTop: props.node.attrs.marginTop || undefined,
  marginBottom: props.node.attrs.marginBottom || undefined,
  paddingTop: props.node.attrs.paddingTop || undefined,
  paddingBottom: props.node.attrs.paddingBottom || undefined,
}))

// Largest width the image may grow to — the editor's content column.
// `wrapper` is a ref on the NodeViewWrapper *component*, so the DOM node is $el.
function maxWidth() {
  const col = wrapper.value?.$el?.closest?.('.ProseMirror')
  return col ? col.clientWidth : 1200
}

function selectSelf() {
  if (typeof props.getPos === 'function') {
    props.editor.commands.setNodeSelection(props.getPos())
  }
}

// While a resize is in progress, cancel any native drag the `data-drag-handle`
// would otherwise start (grabbing a corner handle must resize, not move the node).
function onDragStart(e) {
  if (dragging.value) {
    e.preventDefault()
    e.stopPropagation()
  }
}

function startResize(handle, e) {
  e.preventDefault()
  e.stopPropagation()
  selectSelf()
  dragging.value = true
  const startX = e.clientX
  const startW = img.value?.offsetWidth || props.node.attrs.width || MIN_W
  const cap = maxWidth()

  function onMove(ev) {
    const delta = (ev.clientX - startX) * handle.dir
    const next = Math.round(Math.min(cap, Math.max(MIN_W, startW + delta)))
    props.updateAttributes({ width: next })
  }
  function onUp() {
    dragging.value = false
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}
</script>

<template>
  <NodeViewWrapper
    ref="wrapper"
    as="div"
    class="tiptap-image-block my-4 block w-full leading-none"
    :style="blockStyle"
  >
    <!-- Inner frame hugs the image (inline-block) so the corner handles sit on the
         image corners and the outer block's text-align can position it. Carries the
         comment id + color when the image has a comment (see Commentable). -->
    <div
      class="group relative inline-block max-w-full align-top leading-none"
      :class="[dragging ? 'select-none' : '', node.attrs.commentId ? 'image-comment' : '']"
      :data-comment-id="node.attrs.commentId || undefined"
      :style="node.attrs.commentColor ? { '--comment-color': node.attrs.commentColor } : {}"
      data-drag-handle
      @dragstart="onDragStart"
    >
      <img
        ref="img"
        :src="node.attrs.src"
        :alt="node.attrs.alt || ''"
        :title="node.attrs.title || undefined"
        :style="widthStyle"
        draggable="false"
        class="block h-auto max-w-full rounded-lg transition-shadow duration-200"
        :class="[
          selected ? 'ring-2 ring-brand-500 ring-offset-2 dark:ring-offset-surface' : 'ring-0 group-hover:ring-1 group-hover:ring-brand-300',
          node.attrs.temp ? 'opacity-70' : '',
        ]"
        @mousedown="selectSelf"
      />

      <!-- Pending-upload badge (image inserted from a local file, not yet saved) -->
      <div
        v-if="node.attrs.temp"
        class="pointer-events-none absolute left-2 top-2 flex items-center gap-1.5 rounded-full bg-slate-900/70 px-2.5 py-1 text-[11px] font-medium text-white"
      >
        <span class="h-1.5 w-1.5 animate-pulse rounded-full bg-brand-400" /> {{ $t('editor.image.uploading') }}
      </div>

      <!-- Corner handles (only while the node is selected). pointer-events-auto so
           they stay grabbable even if the selected node view suppresses events. -->
      <template v-if="selected">
        <span
          v-for="h in HANDLES"
          :key="h.key"
          :class="[
            'pointer-events-auto absolute z-10 h-3.5 w-3.5 touch-none rounded-sm border-2 border-white bg-brand-500 shadow-sm transition-transform duration-150 hover:scale-125',
            h.pos,
          ]"
          @pointerdown="startResize(h, $event)"
        />
      </template>
    </div>
  </NodeViewWrapper>
</template>
