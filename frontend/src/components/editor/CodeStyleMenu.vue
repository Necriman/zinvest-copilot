<script setup>
// Inline-code control: the trigger toggles the `code` mark (active while the caret
// is in a snippet); the caret opens a panel to tint the snippet's text + background
// (→ `color` / `background` events, which apply to the whole code span) or clear
// back to the default pill. Mirrors QuoteMenu's split-button shape.
import Icon from '@/components/ui/Icon.vue'
import ToolbarDropdown from './ToolbarDropdown.vue'

defineProps({
  active: { type: Boolean, default: false },
  activeColor: { type: String, default: null },
  activeBg: { type: String, default: null },
})
const emit = defineEmits(['toggle', 'color', 'background', 'reset'])

// Text tints (readable ink tones) + background tints (soft fills incl. a dark one).
const TEXT_COLORS = ['#db2777', '#dc2626', '#ea580c', '#d97706', '#16a34a', '#0891b2', '#2563eb', '#7c3aed', '#0f172a']
const BG_COLORS = ['#fee2e2', '#ffedd5', '#fef9c3', '#dcfce7', '#cffafe', '#dbeafe', '#f3e8ff', '#e2e8f0', '#1e293b']

const TRIGGER = 'inline-flex items-center gap-1 rounded-lg p-2 transition-all duration-200 ease-in-out'
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
        :title="$t('editor.inlineCode')"
        @click="toggle"
      >
        <Icon name="code" class="h-4 w-4" />
        <Icon name="chevronDown" class="h-3.5 w-3.5 opacity-60" />
      </button>
    </template>
    <template #panel="{ close }">
      <div class="min-w-[13rem] p-1">
        <button
          type="button"
          class="mb-1 flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-sm text-slate-700 transition-colors hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-surface-2"
          @click="emit('toggle'), close()"
        >
          <Icon name="code" class="h-4 w-4 opacity-70" />
          {{ active ? $t('editor.removeCode') : $t('editor.makeCode') }}
        </button>

        <p class="px-2 pb-1 pt-1.5 text-[11px] font-medium text-slate-400">{{ $t('editor.code.text') }}</p>
        <div class="flex flex-wrap items-center gap-1.5 px-2">
          <button
            v-for="c in TEXT_COLORS"
            :key="c"
            type="button"
            class="h-5 w-5 rounded-md ring-1 ring-inset ring-black/10 transition-transform duration-150 hover:scale-110 dark:ring-white/15"
            :class="(activeColor || '').toLowerCase() === c.toLowerCase() ? 'ring-2 ring-brand-500 ring-offset-1 dark:ring-offset-surface' : ''"
            :style="{ background: c }"
            :title="c"
            @click="emit('color', c)"
          />
        </div>

        <p class="px-2 pb-1 pt-2 text-[11px] font-medium text-slate-400">{{ $t('editor.code.background') }}</p>
        <div class="flex flex-wrap items-center gap-1.5 px-2">
          <button
            v-for="c in BG_COLORS"
            :key="c"
            type="button"
            class="h-5 w-5 rounded-md ring-1 ring-inset ring-black/10 transition-transform duration-150 hover:scale-110 dark:ring-white/15"
            :class="(activeBg || '').toLowerCase() === c.toLowerCase() ? 'ring-2 ring-brand-500 ring-offset-1 dark:ring-offset-surface' : ''"
            :style="{ background: c }"
            :title="c"
            @click="emit('background', c)"
          />
        </div>

        <div class="my-1.5 h-px bg-slate-100 dark:bg-hairline" />
        <button
          type="button"
          class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-sm text-slate-700 transition-colors hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-surface-2"
          @click="emit('reset'), close()"
        >
          <Icon name="eraser" class="h-4 w-4 opacity-70" />
          {{ $t('editor.code.defaultColors') }}
        </button>
      </div>
    </template>
  </ToolbarDropdown>
</template>
