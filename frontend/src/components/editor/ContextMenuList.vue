<script setup>
// Renders a context-menu item list. Supports four item shapes:
//   { type: 'divider' }
//   { type: 'swatches', label, colors, onPick, onClear }   — a color-swatch row
//   { label, icon, children: [...] }                       — a hover submenu (flyout)
//   { label, icon, run, danger, disabled, shortcut }       — a regular action
// Submenu children are rendered by this same component (recursively), and any leaf
// action bubbles `close` up to the root ContextMenu so the whole menu dismisses.
import { nextTick, ref } from 'vue'

import Icon from '@/components/ui/Icon.vue'

defineProps({
  items: { type: Array, default: () => [] },
})
const emit = defineEmits(['close'])

const openSub = ref(-1)
const subEl = ref(null)
const subStyle = ref({ visibility: 'hidden' })
let closeTimer = null

function onItem(item) {
  if (item.disabled) return
  item.run?.()
  emit('close')
}
function onSwatch(item, color) {
  if (color == null) item.onClear?.()
  else item.onPick?.(color)
  emit('close')
}
// Only track the element that mounted — ignore the null from a sibling flyout
// unmounting, which (since it fires after the new one mounts for an earlier list
// index) would otherwise clobber the ref and leave the new flyout hidden.
function setSubEl(el) {
  if (el) subEl.value = el
}
// Open a flyout, then measure it and clamp within the viewport (this menu is
// teleported + fixed): flip to the left of the item if it spills past the right
// edge, and shift up if it runs past the bottom. Hidden until measured so the
// correction never flashes.
async function openSubmenu(i) {
  clearTimeout(closeTimer)
  openSub.value = i
  subStyle.value = { visibility: 'hidden' }
  await nextTick()
  const el = subEl.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const pad = 8
  const style = {}
  if (r.right > window.innerWidth - pad) {
    style.left = 'auto'
    style.right = '100%'
    style.marginLeft = '0'
    style.marginRight = '2px'
  }
  if (r.bottom > window.innerHeight - pad) {
    style.top = `${Math.min(0, window.innerHeight - pad - r.bottom)}px`
  }
  subStyle.value = style
}
function scheduleClose() {
  clearTimeout(closeTimer)
  closeTimer = setTimeout(() => (openSub.value = -1), 140)
}
function keepOpen() {
  clearTimeout(closeTimer)
}

const REGULAR =
  'flex w-full items-center gap-2.5 rounded-lg px-3 py-1.5 text-left text-sm transition-colors duration-150 disabled:pointer-events-none disabled:opacity-40'
</script>

<template>
  <template v-for="(item, i) in items" :key="i">
    <!-- Divider -->
    <div v-if="item.type === 'divider'" class="my-1 h-px bg-slate-100 dark:bg-hairline" />

    <!-- Swatch row (text/highlight/cell color) -->
    <div v-else-if="item.type === 'swatches'" class="px-2 py-1.5">
      <p class="mb-1.5 text-[11px] font-medium text-slate-400">{{ item.label }}</p>
      <div class="flex flex-wrap items-center gap-1.5">
        <button
          v-for="c in item.colors"
          :key="c"
          type="button"
          class="h-5 w-5 rounded-md transition-transform duration-150 hover:scale-110"
          :class="(item.current || '').toLowerCase() === c.toLowerCase()
            ? 'ring-2 ring-brand-500 ring-offset-1 dark:ring-offset-surface'
            : 'ring-1 ring-inset ring-black/10 dark:ring-white/15'"
          :style="{ background: c }"
          :title="c"
          @click="onSwatch(item, c)"
        />
        <button
          type="button"
          class="flex h-5 w-5 items-center justify-center rounded-md text-slate-400 ring-1 ring-inset ring-slate-200 transition-colors hover:bg-slate-100 dark:ring-hairline dark:hover:bg-surface-2"
          :title="$t('editor.none')"
          @click="onSwatch(item, null)"
        >
          <Icon name="x" class="h-3 w-3" />
        </button>
      </div>
    </div>

    <!-- Submenu (opens a flyout on hover) -->
    <div
      v-else-if="item.children"
      class="relative"
      @mouseenter="openSubmenu(i)"
      @mouseleave="scheduleClose"
    >
      <button
        type="button"
        :class="[
          REGULAR,
          'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-surface-2',
          openSub === i ? 'bg-slate-100 dark:bg-surface-2' : '',
        ]"
      >
        <Icon v-if="item.icon" :name="item.icon" class="h-4 w-4 shrink-0 opacity-70" />
        <span class="flex-1">{{ item.label }}</span>
        <span
          v-if="item.dot"
          class="h-3.5 w-3.5 shrink-0 rounded-full ring-1 ring-inset ring-black/10 dark:ring-white/15"
          :style="{ background: item.dot }"
        />
        <Icon name="chevronRight" class="h-3.5 w-3.5 opacity-50" />
      </button>
      <div
        v-if="openSub === i"
        :ref="setSubEl"
        class="absolute left-full top-0 z-10 ml-0.5 min-w-[12rem] rounded-xl border border-slate-200 bg-white p-1 shadow-float dark:border-hairline dark:bg-surface"
        :style="subStyle"
        @mouseenter="keepOpen"
        @mouseleave="scheduleClose"
      >
        <ContextMenuList :items="item.children" @close="emit('close')" />
      </div>
    </div>

    <!-- Regular action -->
    <button
      v-else
      type="button"
      role="menuitem"
      :disabled="item.disabled"
      :class="[
        REGULAR,
        item.danger
          ? 'text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10'
          : item.active
            ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300'
            : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-surface-2',
      ]"
      @click="onItem(item)"
    >
      <Icon v-if="item.icon" :name="item.icon" class="h-4 w-4 shrink-0 opacity-70" />
      <span class="flex-1">{{ item.label }}</span>
      <span v-if="item.shortcut" class="text-[11px] tabular-nums text-slate-400">{{ item.shortcut }}</span>
    </button>
  </template>
</template>
