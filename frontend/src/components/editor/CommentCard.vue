<script setup>
// One comment card: avatar · author · time · ⋯ menu, and either the saved text or
// an editing composer (textarea + color swatches). Self-contained and position-less
// — used both by the right-margin rail (many placed down the page) and by the
// single hover popover shown when there are too many comments to lay out.
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import Icon from '@/components/ui/Icon.vue'

const props = defineProps({
  comment: { type: Object, required: true }, // { id, author, date, text, color }
  editing: { type: Boolean, default: false },
  active: { type: Boolean, default: false }, // hovered pair / being composed → lift + outline
})
const emit = defineEmits(['edit', 'save', 'cancel', 'delete', 'recolor', 'hover', 'menu'])

const DEFAULT_COLOR = '#8b5cf6'
const COMMENT_COLORS = ['#8b5cf6', '#eab308', '#22c55e', '#3b82f6', '#ec4899', '#f97316', '#ef4444']
const colorOf = (c) => c.color || DEFAULT_COLOR
const tint = (hex) => (hex || DEFAULT_COLOR) + '22' // ~13% alpha for the avatar fill

// --- composer --------------------------------------------------------------
const draft = ref('')
const textareaRef = ref(null)
watch(
  () => props.editing,
  (on) => {
    if (!on) return
    draft.value = props.comment.text || ''
    // Focus the composer once it's in the DOM. Double up (nextTick + a frame) so it
    // wins over any late editor focus and works whether we're in the rail or the
    // just-positioned hover popover — so typing writes the comment, not the document.
    nextTick(() => {
      textareaRef.value?.focus?.()
      requestAnimationFrame(() => textareaRef.value?.focus?.())
    })
  },
  { immediate: true },
)
function onSave() {
  emit('save', props.comment.id, draft.value)
}

// --- ⋯ menu ----------------------------------------------------------------
// The open state is reported upward: the menu overflows the card, and the rail
// has to lift this card above its neighbours or the next card paints over it.
const menuOpen = ref(false)
watch(menuOpen, (open) => emit('menu', open ? props.comment.id : null))
function onDocClick() {
  menuOpen.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))

// --- formatting ------------------------------------------------------------
function relativeTime(iso) {
  if (!iso) return ''
  const secs = Math.round((Date.now() - new Date(iso).getTime()) / 1000)
  if (secs < 60) return 'less than a minute ago'
  const m = Math.round(secs / 60)
  if (m < 60) return `${m} minute${m > 1 ? 's' : ''} ago`
  const h = Math.round(m / 60)
  if (h < 24) return `${h} hour${h > 1 ? 's' : ''} ago`
  const d = Math.round(h / 24)
  return `${d} day${d > 1 ? 's' : ''} ago`
}
function initial(name) {
  return (name || '?').trim().charAt(0).toUpperCase() || '?'
}
</script>

<template>
  <div
    class="w-72 rounded-2xl border border-l-4 border-slate-200 bg-white p-3 transition-shadow duration-150 dark:border-hairline dark:bg-surface"
    :class="active ? 'shadow-float' : 'shadow-card hover:shadow-float'"
    :style="{ borderLeftColor: colorOf(comment), ...(active ? { outline: `2px solid ${colorOf(comment)}`, outlineOffset: '1px' } : {}) }"
    @mouseenter="emit('hover', comment.id)"
    @mouseleave="emit('hover', null)"
  >
    <!-- Header -->
    <div class="flex items-center gap-2.5">
      <span
        class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold"
        :style="{ background: tint(colorOf(comment)), color: colorOf(comment) }"
      >
        {{ initial(comment.author) }}
      </span>
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-bold text-slate-900 dark:text-white">{{ comment.author || 'You' }}</p>
        <p class="text-xs text-slate-400">{{ relativeTime(comment.date) }}</p>
      </div>
      <div class="relative">
        <button
          type="button"
          class="rounded-lg p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-surface-2"
          :title="$t('editor.comment.more')"
          @click.stop="menuOpen = !menuOpen"
        >
          <Icon name="moreHorizontal" class="h-4 w-4" />
        </button>
        <!-- `pop` is the same transition every other menu in the app uses
             (language switcher, account menu, colour pickers). -->
        <Transition name="pop">
          <div
            v-if="menuOpen"
            class="absolute right-0 top-full z-30 mt-1 w-32 origin-top-right overflow-hidden rounded-xl border border-slate-200 bg-white p-1 shadow-float dark:border-hairline dark:bg-surface"
            @click.stop
          >
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-surface-2"
              @click="menuOpen = false; emit('edit', comment.id)"
            >
              <Icon name="pencil" class="h-4 w-4 opacity-70" /> {{ $t('editor.comment.edit') }}
            </button>
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10"
              @click="menuOpen = false; emit('delete', comment.id)"
            >
              <Icon name="trash" class="h-4 w-4 opacity-70" /> {{ $t('editor.comment.delete') }}
            </button>
          </div>
        </Transition>
      </div>
    </div>

    <!-- Composer (new / editing) or the saved comment text -->
    <div v-if="editing" class="mt-2">
      <textarea
        ref="textareaRef"
        v-model="draft"
        rows="2"
        :placeholder="$t('editor.comment.placeholder')"
        class="w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500 focus:outline-none dark:border-hairline dark:bg-surface-2 dark:text-slate-100"
        @keydown.enter.exact.prevent="onSave"
        @keydown.esc.prevent="emit('cancel', comment.id)"
        @click.stop
      />
      <div class="mt-2 flex items-center gap-1.5">
        <button
          v-for="col in COMMENT_COLORS"
          :key="col"
          type="button"
          class="h-5 w-5 rounded-full transition-transform hover:scale-110"
          :class="colorOf(comment).toLowerCase() === col.toLowerCase() ? 'ring-2 ring-offset-1 dark:ring-offset-surface' : 'ring-1 ring-inset ring-black/10 dark:ring-white/15'"
          :style="{ background: col, '--tw-ring-color': col }"
          :title="col"
          @click.stop="emit('recolor', comment.id, col)"
        />
      </div>
      <div class="mt-2 flex justify-end gap-2">
        <button
          type="button"
          class="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-surface-2"
          @click.stop="emit('cancel', comment.id)"
        >
          {{ $t('editor.comment.cancel') }}
        </button>
        <button
          type="button"
          class="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          :disabled="!draft.trim()"
          @click.stop="onSave"
        >
          {{ $t('editor.comment.send') }}
        </button>
      </div>
    </div>
    <p v-else class="mt-2 whitespace-pre-wrap break-words text-sm text-slate-700 dark:text-slate-200">{{ comment.text }}</p>
  </div>
</template>
