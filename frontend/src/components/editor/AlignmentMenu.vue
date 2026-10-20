<script setup>
// Toolbar dropdown for block text-alignment (left / center / right / justify).
// Reads the active alignment via the `active` prop and emits `select` with the
// chosen value; the parent runs editor.chain().setTextAlign(value).
import Icon from '@/components/ui/Icon.vue'
import ToolbarDropdown from './ToolbarDropdown.vue'

defineProps({
  active: { type: String, default: 'left' }, // left | center | right | justify
})
const emit = defineEmits(['select'])

const OPTIONS = [
  { val: 'left', label: 'editor.align.left', icon: 'alignLeft' },
  { val: 'center', label: 'editor.align.center', icon: 'alignCenter' },
  { val: 'right', label: 'editor.align.right', icon: 'alignRight' },
  { val: 'justify', label: 'editor.align.justify', icon: 'alignJustify' },
]
function iconFor(val) {
  return OPTIONS.find((o) => o.val === val)?.icon || 'alignLeft'
}

const TRIGGER =
  'inline-flex items-center gap-1 rounded-lg p-2 text-slate-600 transition-all duration-200 ease-in-out hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2'
const ITEM =
  'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-slate-700 transition-all duration-200 ease-in-out hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-surface-2'
const ACTIVE = 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300'
</script>

<template>
  <ToolbarDropdown panel-class="min-w-[11rem]">
    <template #trigger="{ toggle, open }">
      <button
        type="button"
        :class="[TRIGGER, open ? 'bg-slate-100 dark:bg-surface-2' : '']"
        :title="$t('editor.align.title')"
        @click="toggle"
      >
        <Icon :name="iconFor(active)" class="h-4 w-4" />
        <Icon name="chevronDown" class="h-3.5 w-3.5 opacity-60" />
      </button>
    </template>
    <template #panel="{ close }">
      <button
        v-for="o in OPTIONS"
        :key="o.val"
        type="button"
        :class="[ITEM, active === o.val ? ACTIVE : '']"
        @click="emit('select', o.val), close()"
      >
        <Icon :name="o.icon" class="h-4 w-4 opacity-80" />
        {{ $t(o.label) }}
      </button>
    </template>
  </ToolbarDropdown>
</template>
