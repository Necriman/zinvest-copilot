<script setup>
// Visual gantt builder: a title + task rows (section · name · start · duration),
// with a live mermaid preview. Emits the serialized `gantt` source on every change.
// Advanced features (dependencies, tags) stay available in the Code tab.
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import Icon from '@/components/ui/Icon.vue'
import MermaidPreview from './MermaidPreview.vue'
import { parseGantt, serializeGantt } from './mermaidDiagrams'

const props = defineProps({ code: { type: String, default: '' } })
const emit = defineEmits(['change'])

const parsed = parseGantt(props.code)
const state = reactive({
  title: parsed.title || 'Plan',
  tasks: parsed.tasks.length ? parsed.tasks : [{ section: 'Phase 1', name: 'Research', start: '2024-01-01', duration: '10d' }],
})

const out = computed(() => serializeGantt(state))
watch(out, (c) => emit('change', c), { immediate: true })

const { t: tr } = useI18n()

function addTask() {
  const last = state.tasks[state.tasks.length - 1]
  state.tasks.push({ section: last?.section || '', name: tr('editor.builders.newTask'), start: '', duration: '5d' })
}
function removeTask(i) {
  state.tasks.splice(i, 1)
}

const INPUT =
  'rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none dark:border-hairline dark:bg-surface-2 dark:text-slate-100'
</script>

<template>
  <div class="grid h-full grid-cols-1 md:grid-cols-2">
    <div class="min-h-0 overflow-y-auto p-4">
      <label class="mb-3 block">
        <span class="mb-1 block text-xs font-semibold text-slate-500 dark:text-slate-400">{{ $t('editor.builders.title') }}</span>
        <input v-model="state.title" :class="[INPUT, 'w-full']" :placeholder="$t('editor.builders.projectTitle')" />
      </label>

      <div class="mb-1.5 grid grid-cols-[1fr_1.2fr_1fr_4.5rem_auto] gap-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        <span>{{ $t('editor.builders.section') }}</span>
        <span>{{ $t('editor.builders.task') }}</span>
        <span>{{ $t('editor.builders.start') }}</span>
        <span>{{ $t('editor.builders.days') }}</span>
        <span />
      </div>
      <div class="space-y-2">
        <div v-for="(t, i) in state.tasks" :key="i" class="grid grid-cols-[1fr_1.2fr_1fr_4.5rem_auto] items-center gap-2">
          <input v-model="t.section" :class="[INPUT, 'min-w-0']" :placeholder="$t('editor.builders.section')" />
          <input v-model="t.name" :class="[INPUT, 'min-w-0']" :placeholder="$t('editor.builders.taskName')" />
          <input v-model="t.start" :class="[INPUT, 'min-w-0']" placeholder="2024-01-01" />
          <input v-model="t.duration" :class="[INPUT, 'min-w-0']" placeholder="5d" />
          <button
            type="button"
            class="shrink-0 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-500/10"
            :title="$t('editor.builders.remove')"
            @click="removeTask(i)"
          >
            <Icon name="trash" class="h-4 w-4" />
          </button>
        </div>
      </div>

      <button
        type="button"
        class="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:border-brand-400 hover:text-brand-600 dark:border-hairline dark:text-slate-300"
        @click="addTask"
      >
        <Icon name="plus" class="h-4 w-4" /> {{ $t('editor.builders.addTask') }}
      </button>
    </div>

    <div class="min-h-0 border-t border-slate-200 bg-slate-50 dark:border-hairline dark:bg-surface-2/40 md:border-l md:border-t-0">
      <MermaidPreview :code="out" />
    </div>
  </div>
</template>
