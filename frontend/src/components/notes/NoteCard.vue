<script setup>
/**
 * One note in the Notes grid, drawn as a small sheet of paper.
 *
 * Single click focuses (so you can skim without leaving the page); double click
 * — or Enter on a focused card — opens it in the editor.
 */
import Icon from '@/components/ui/Icon.vue'
import { relativeTime } from '@/utils/format'

defineProps({
  note: { type: Object, required: true },
  focused: { type: Boolean, default: false },
})
const emit = defineEmits(['focus', 'open', 'delete'])
</script>

<template>
  <div
    class="group relative flex h-56 cursor-pointer select-none flex-col overflow-hidden rounded-2xl border bg-white text-left shadow-card transition-all duration-150 hover:-translate-y-0.5 hover:shadow-float dark:bg-surface"
    :class="
      focused
        ? 'border-brand-500 ring-2 ring-brand-500/30'
        : 'border-slate-200 hover:border-brand-300 dark:border-hairline'
    "
    role="button"
    tabindex="0"
    :title="$t('notes.openHint')"
    @click="emit('focus', note.id)"
    @dblclick="emit('open', note.id)"
    @keydown.enter.prevent="emit('open', note.id)"
    @keydown.space.prevent="emit('focus', note.id)"
  >
    <!-- Hover actions. The pencil is a one-click way in, since the card itself
         needs a double click. -->
    <div class="absolute right-2 top-2 z-10 flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
      <button
        type="button"
        class="rounded-lg bg-white/90 p-1.5 text-slate-400 shadow-sm backdrop-blur transition hover:text-brand-600 dark:bg-surface-2/90"
        :title="$t('notes.openEditor')"
        @click.stop="emit('open', note.id)"
      >
        <Icon name="pencil" class="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        class="rounded-lg bg-white/90 p-1.5 text-slate-400 shadow-sm backdrop-blur transition hover:text-red-500 dark:bg-surface-2/90"
        :title="$t('common.delete')"
        @click.stop="emit('delete', note.id)"
      >
        <Icon name="trash" class="h-3.5 w-3.5" />
      </button>
    </div>

    <Icon
      v-if="note.is_pinned"
      name="target"
      class="absolute left-3 top-3 h-3.5 w-3.5 text-amber-500"
    />

    <!-- Paper body -->
    <div class="flex-1 overflow-hidden px-4 pb-3" :class="note.is_pinned ? 'pt-8' : 'pt-4'">
      <p class="line-clamp-2 pr-12 text-sm font-bold leading-snug text-slate-900 dark:text-white">
        {{ note.title }}
      </p>
      <p class="mt-2 line-clamp-5 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
        {{ note.excerpt || $t('notes.emptyBody') }}
      </p>
    </div>

    <div class="border-t border-slate-100 px-4 py-2.5 dark:border-hairline">
      <p class="text-[11px] text-slate-400">{{ relativeTime(note.updated_at) }}</p>
    </div>
  </div>
</template>
