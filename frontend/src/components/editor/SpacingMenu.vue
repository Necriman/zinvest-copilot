<script setup>
// Toolbar popover for per-block vertical spacing. Shows four px number inputs
// seeded from the currently selected block's margin/padding attributes (`values`,
// numbers) and emits `update` with a single-key patch — e.g. { marginTop: '12px' }
// or { marginTop: null } to clear. `disabled` when the selection has no block that
// supports spacing.
import Icon from '@/components/ui/Icon.vue'
import ToolbarDropdown from './ToolbarDropdown.vue'

defineProps({
  values: {
    type: Object,
    default: () => ({ marginTop: 0, marginBottom: 0, paddingTop: 0, paddingBottom: 0 }),
  },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update'])

const FIELDS = [
  { key: 'marginTop', label: 'editor.spacing.marginTop' },
  { key: 'marginBottom', label: 'editor.spacing.marginBottom' },
  { key: 'paddingTop', label: 'editor.spacing.paddingTop' },
  { key: 'paddingBottom', label: 'editor.spacing.paddingBottom' },
]

function onInput(key, e) {
  const raw = String(e.target.value).trim()
  if (raw === '') {
    emit('update', { [key]: null }) // cleared field → drop the inline style
    return
  }
  const n = Math.max(0, Math.min(400, parseInt(raw, 10) || 0))
  emit('update', { [key]: `${n}px` })
}

const TRIGGER =
  'inline-flex items-center justify-center rounded-lg p-2 text-slate-600 transition-all duration-200 ease-in-out hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2'
</script>

<template>
  <ToolbarDropdown panel-class="w-64">
    <template #trigger="{ toggle, open }">
      <button
        type="button"
        :class="[TRIGGER, open ? 'bg-slate-100 dark:bg-surface-2' : '']"
        :title="$t('editor.spacing.title')"
        @click="toggle"
      >
        <Icon name="spacing" class="h-4 w-4" />
      </button>
    </template>
    <template #panel>
      <p class="px-1.5 pt-1 pb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{{ $t('editor.spacing.label') }}</p>
      <div v-if="disabled" class="px-1.5 pb-1.5 text-sm text-slate-400">{{ $t('editor.spacing.hint') }}</div>
      <div v-else class="grid grid-cols-2 gap-2 px-1 pb-1">
        <label v-for="f in FIELDS" :key="f.key" class="flex flex-col gap-1">
          <span class="text-xs font-medium text-slate-500 dark:text-slate-400">{{ $t(f.label) }}</span>
          <span class="relative">
            <input
              type="number"
              min="0"
              step="1"
              inputmode="numeric"
              :value="values[f.key]"
              class="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-2.5 pr-7 text-sm tabular-nums text-slate-800 focus:border-brand-500 focus:outline-none dark:border-hairline dark:bg-surface-2 dark:text-slate-100"
              @input="onInput(f.key, $event)"
            />
            <span class="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-400">px</span>
          </span>
        </label>
      </div>
    </template>
  </ToolbarDropdown>
</template>
