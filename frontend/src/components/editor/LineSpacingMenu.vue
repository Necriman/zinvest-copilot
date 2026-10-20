<script setup>
// Toolbar dropdown for line spacing. `active` is the current lineHeight string
// (or null → "Default"). Emits `select` with the chosen value; null clears it so
// the .prose line-height takes back over.
import Icon from '@/components/ui/Icon.vue'
import ToolbarDropdown from './ToolbarDropdown.vue'

// `active` may legitimately be null (no explicit line-height) — leaving the type
// unconstrained avoids a dev-mode prop-type warning on null.
defineProps({
  active: { default: null },
})
const emit = defineEmits(['select'])

const OPTIONS = [
  { val: null, label: 'Default', key: 'editor.lineDefault' },
  { val: '1', label: 'Single', key: 'editor.lineSingle' },
  { val: '1.15', label: '1.15' },
  { val: '1.5', label: '1.5' },
  { val: '2', label: 'Double', key: 'editor.lineDouble' },
]

const TRIGGER =
  'inline-flex items-center gap-1 rounded-lg p-2 text-slate-600 transition-all duration-200 ease-in-out hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2'
const ITEM =
  'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-slate-700 transition-all duration-200 ease-in-out hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-surface-2'
const ACTIVE = 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300'
</script>

<template>
  <ToolbarDropdown panel-class="min-w-[10rem]">
    <template #trigger="{ toggle, open }">
      <button
        type="button"
        :class="[TRIGGER, open ? 'bg-slate-100 dark:bg-surface-2' : '']"
        :title="$t('editor.lineSpacing')"
        @click="toggle"
      >
        <Icon name="lineSpacing" class="h-4 w-4" />
        <Icon name="chevronDown" class="h-3.5 w-3.5 opacity-60" />
      </button>
    </template>
    <template #panel="{ close }">
      <button
        v-for="o in OPTIONS"
        :key="o.label"
        type="button"
        :class="[ITEM, (active ?? null) === o.val ? ACTIVE : '']"
        @click="emit('select', o.val), close()"
      >
        <span class="flex-1">{{ o.key ? $t(o.key) : o.label }}</span>
        <Icon v-if="(active ?? null) === o.val" name="check" class="h-4 w-4 text-brand-600 dark:text-brand-300" />
      </button>
    </template>
  </ToolbarDropdown>
</template>
