<script setup>
// Split-button list control (one per kind). The left half toggles the list on/off;
// the caret opens a style picker — bullet: disc/circle/square, ordered: decimal /
// a·b·c / A·B·C / i·ii·iii / I·II·III (raw CSS list-style-type values). Emits
// `toggle` and `style` (the chosen list-style-type).
import Icon from '@/components/ui/Icon.vue'
import ToolbarDropdown from './ToolbarDropdown.vue'

const props = defineProps({
  kind: { type: String, required: true }, // 'bullet' | 'ordered'
  active: { type: Boolean, default: false },
  activeStyle: { type: String, default: null }, // current list-style-type
})
const emit = defineEmits(['toggle', 'style'])

const BULLET = [
  { val: 'disc', label: 'editor.list.disc', preview: '●' },
  { val: 'circle', label: 'editor.list.circle', preview: '○' },
  { val: 'square', label: 'editor.list.square', preview: '■' },
]
const ORDERED = [
  { val: 'decimal', label: 'editor.list.decimal', preview: '1.' },
  { val: 'lower-alpha', label: 'editor.list.lowerAlpha', preview: 'a.' },
  { val: 'upper-alpha', label: 'editor.list.upperAlpha', preview: 'A.' },
  { val: 'lower-roman', label: 'editor.list.lowerRoman', preview: 'i.' },
  { val: 'upper-roman', label: 'editor.list.upperRoman', preview: 'I.' },
]

const options = props.kind === 'bullet' ? BULLET : ORDERED
const icon = props.kind === 'bullet' ? 'listBullet' : 'listOrdered'
const title = props.kind === 'bullet' ? 'editor.list.bullet' : 'editor.list.numbered'

const ITEM =
  'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-slate-700 transition-all duration-200 ease-in-out hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-surface-2'
const ACTIVE = 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300'
</script>

<template>
  <div
    class="inline-flex items-center rounded-lg"
    :class="active ? 'bg-brand-50 dark:bg-brand-500/15' : ''"
  >
    <!-- Toggle -->
    <button
      type="button"
      class="inline-flex items-center justify-center rounded-l-lg p-2 transition-all duration-200 ease-in-out"
      :class="active
        ? 'text-brand-700 dark:text-brand-300'
        : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2'"
      :title="$t(title)"
      @click="emit('toggle')"
    >
      <Icon :name="icon" class="h-4 w-4" />
    </button>

    <!-- Style picker -->
    <ToolbarDropdown panel-class="min-w-[11rem]">
      <template #trigger="{ toggle, open }">
        <button
          type="button"
          class="inline-flex items-center justify-center rounded-r-lg py-2 pr-1 pl-0.5 transition-all duration-200 ease-in-out"
          :class="[
            active ? 'text-brand-700 dark:text-brand-300' : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-surface-2',
            open ? 'bg-slate-100 dark:bg-surface-2' : '',
          ]"
          :title="$t('editor.list.style', { list: $t(title) })"
          @click="toggle"
        >
          <Icon name="chevronDown" class="h-3 w-3 opacity-70" />
        </button>
      </template>
      <template #panel="{ close }">
        <button
          v-for="o in options"
          :key="o.val"
          type="button"
          :class="[ITEM, active && activeStyle === o.val ? ACTIVE : '']"
          @click="emit('style', o.val), close()"
        >
          <span class="w-6 shrink-0 text-center font-mono text-sm tabular-nums">{{ o.preview }}</span>
          {{ $t(o.label) }}
        </button>
      </template>
    </ToolbarDropdown>
  </div>
</template>
