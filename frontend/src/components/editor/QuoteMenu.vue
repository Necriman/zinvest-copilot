<script setup>
// Blockquote control: the trigger toggles a quote (active while the caret is in
// one); the panel picks an accent color (→ `color` event, which wraps-in-quote +
// recolors) or removes the quote. Colors map to the QuoteColor extension's
// `--quote-color` var (left rule + soft tint drawn in the stylesheet).
import Icon from '@/components/ui/Icon.vue'
import ToolbarDropdown from './ToolbarDropdown.vue'

defineProps({
  active: { type: Boolean, default: false }, // in a blockquote
  activeColor: { type: String, default: null },
})
const emit = defineEmits(['toggle', 'color', 'remove'])

// Accent colors (blue default, then green/amber/red/purple/cyan/slate).
const COLORS = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#64748b']

const TRIGGER =
  'inline-flex items-center gap-1 rounded-lg p-2 transition-all duration-200 ease-in-out'
</script>

<template>
  <ToolbarDropdown panel-class="w-max">
    <template #trigger="{ toggle, open }">
      <button
        type="button"
        :class="[
          TRIGGER,
          active
            ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300'
            : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2',
          open ? 'bg-slate-100 dark:bg-surface-2' : '',
        ]"
        :title="$t('editor.blockquote')"
        @click="toggle"
      >
        <Icon name="quote" class="h-4 w-4" />
        <Icon name="chevronDown" class="h-3.5 w-3.5 opacity-60" />
      </button>
    </template>
    <template #panel="{ close }">
      <p class="px-2 pb-1.5 pt-1 text-[11px] font-medium text-slate-400">{{ $t('editor.quoteColor') }}</p>
      <div class="flex items-center gap-1.5 px-2">
        <button
          v-for="c in COLORS"
          :key="c"
          type="button"
          class="h-6 w-6 rounded-md ring-1 ring-inset ring-black/10 transition-transform duration-150 hover:scale-110 dark:ring-white/15"
          :class="(activeColor || '').toLowerCase() === c.toLowerCase() ? 'ring-2 ring-brand-500 ring-offset-1 dark:ring-offset-surface' : ''"
          :style="{ background: c }"
          :title="c"
          @click="emit('color', c), close()"
        />
      </div>
      <div class="my-1.5 h-px bg-slate-100 dark:bg-hairline" />
      <button
        type="button"
        class="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-sm text-slate-700 transition-colors hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-surface-2"
        @click="emit('toggle'), close()"
      >
        <Icon name="quote" class="h-4 w-4 opacity-70" />
        {{ active ? $t('editor.removeQuote') : $t('editor.plainQuote') }}
      </button>
    </template>
  </ToolbarDropdown>
</template>
