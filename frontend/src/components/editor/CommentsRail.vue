<script setup>
// The right-margin rail of comment cards, each anchored to its highlighted text
// (`tops[id]`) and pushed down so cards never overlap. Used only when the comments
// fit — past that, DocumentEditor collapses to a per-comment hover popover instead.
import { nextTick, onMounted, ref, watch } from 'vue'

import CommentCard from './CommentCard.vue'

const props = defineProps({
  comments: { type: Array, default: () => [] }, // { id, author, date, text, color }
  tops: { type: Object, default: () => ({}) }, // id -> anchor top (px)
  editingId: { default: null },
  hoveredId: { default: null },
})
const emit = defineEmits(['edit', 'save', 'cancel', 'delete', 'recolor', 'hover'])

const isActive = (c) => props.hoveredId === c.id || props.editingId === c.id

// A card whose ⋯ menu is open has to outrank its neighbours: the menu hangs
// below the card, and the next card's opaque background would otherwise paint
// straight over it (a z-index inside the card can't beat a sibling wrapper).
const menuId = ref(null)
const zOf = (c) => (menuId.value === c.id ? 'z-30' : isActive(c) ? 'z-20' : 'z-10')

// --- push-down layout ------------------------------------------------------
const cardEls = {}
function setCard(id, el) {
  if (el) cardEls[id] = el
  else delete cardEls[id]
}
const layout = ref({})
function relayout() {
  const gap = 12
  let cursor = -Infinity
  const next = {}
  for (const c of [...props.comments].sort((a, b) => (props.tops[a.id] ?? 0) - (props.tops[b.id] ?? 0))) {
    const top = Math.max(props.tops[c.id] ?? 0, cursor + gap)
    next[c.id] = top
    cursor = top + (cardEls[c.id]?.offsetHeight || 96)
  }
  layout.value = next
}
watch([() => props.comments, () => props.tops, () => props.editingId, () => props.hoveredId], () => nextTick(relayout), { deep: true })
onMounted(() => nextTick(relayout))
</script>

<template>
  <!-- Non-interactive layer; individual cards re-enable pointer events. -->
  <div data-comments-rail class="pointer-events-none absolute inset-y-0 right-0 w-72">
    <div
      v-for="c in comments"
      :key="c.id"
      :ref="(el) => setCard(c.id, el)"
      :data-comment-card="c.id"
      class="pointer-events-auto absolute right-0"
      :class="zOf(c)"
      :style="{ top: (layout[c.id] ?? tops[c.id] ?? 0) + 'px' }"
    >
      <CommentCard
        :comment="c"
        :editing="editingId === c.id"
        :active="isActive(c)"
        @edit="emit('edit', $event)"
        @save="(id, text) => emit('save', id, text)"
        @cancel="emit('cancel', $event)"
        @delete="emit('delete', $event)"
        @recolor="(id, color) => emit('recolor', id, color)"
        @hover="emit('hover', $event)"
        @menu="menuId = $event"
      />
    </div>
  </div>
</template>
