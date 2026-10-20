<script setup>
// Visual pie-chart builder: a title + label/value rows, with a live mermaid preview.
// Emits the serialized `pie` source on every change.
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import Icon from '@/components/ui/Icon.vue'
import MermaidPreview from './MermaidPreview.vue'
import { parsePie, serializePie } from './mermaidDiagrams'

const props = defineProps({ code: { type: String, default: '' } })
const emit = defineEmits(['change'])

const parsed = parsePie(props.code)
const { t: tr } = useI18n()
const state = reactive({
  title: parsed.title || tr('editor.builders.untitled'),
  slices: parsed.slices.length ? parsed.slices : [{ label: tr('editor.builders.sliceA'), value: 40 }, { label: tr('editor.builders.sliceB'), value: 60 }],
})

const out = computed(() => serializePie(state))
watch(out, (c) => emit('change', c), { immediate: true })

function addSlice() {
  state.slices.push({ label: 'New', value: 10 })
}
function removeSlice(i) {
  state.slices.splice(i, 1)
}

const INPUT =
  'rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none dark:border-hairline dark:bg-surface-2 dark:text-slate-100'
</script>

<template>
  <div class="grid h-full grid-cols-1 md:grid-cols-2">
    <div class="min-h-0 overflow-y-auto p-4">
      <label class="mb-3 block">
        <span class="mb-1 block text-xs font-semibold text-slate-500 dark:text-slate-400">{{ $t('editor.builders.title') }}</span>
        <input v-model="state.title" :class="[INPUT, 'w-full']" :placeholder="$t('editor.builders.chartTitle')" />
      </label>

      <p class="mb-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400">{{ $t('editor.builders.slices') }}</p>
      <div class="space-y-2">
        <div v-for="(s, i) in state.slices" :key="i" class="flex items-center gap-2">
          <input v-model="s.label" :class="[INPUT, 'min-w-0 flex-1']" :placeholder="$t('editor.builders.sliceLabel')" />
          <input v-model.number="s.value" type="number" min="0" step="1" :class="[INPUT, 'w-20']" />
          <button
            type="button"
            class="shrink-0 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-500/10"
            :title="$t('editor.builders.remove')"
            @click="removeSlice(i)"
          >
            <Icon name="trash" class="h-4 w-4" />
          </button>
        </div>
      </div>

      <button
        type="button"
        class="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:border-brand-400 hover:text-brand-600 dark:border-hairline dark:text-slate-300"
        @click="addSlice"
      >
        <Icon name="plus" class="h-4 w-4" /> {{ $t('editor.builders.addSlice') }}
      </button>
    </div>

    <div class="min-h-0 border-t border-slate-200 bg-slate-50 dark:border-hairline dark:bg-surface-2/40 md:border-l md:border-t-0">
      <MermaidPreview :code="out" />
    </div>
  </div>
</template>
