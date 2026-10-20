<script setup>
// Visual class-diagram builder: classes (name + members) and relationships between
// them (from · type · to · label), with a live mermaid preview. Emits the
// serialized `classDiagram` source on every change.
import { computed, reactive, watch } from 'vue'

import Icon from '@/components/ui/Icon.vue'
import MermaidPreview from './MermaidPreview.vue'
import { CLASS_RELATIONS, parseClass, serializeClass } from './mermaidDiagrams'

const props = defineProps({ code: { type: String, default: '' } })
const emit = defineEmits(['change'])

const parsed = parseClass(props.code)
const state = reactive({
  classes: parsed.classes.length ? parsed.classes.map((c) => ({ name: c.name, membersText: (c.members || []).join('\n') })) : [{ name: 'Account', membersText: '+String owner\n+deposit(amount)' }],
  relations: parsed.relations || [],
})

// Rebuild the model (members text → array) for serialization.
const model = computed(() => ({
  classes: state.classes.map((c) => ({ name: c.name.trim() || 'Class', members: c.membersText.split('\n').map((m) => m.trim()).filter(Boolean) })),
  relations: state.relations,
}))
const out = computed(() => serializeClass(model.value))
watch(out, (c) => emit('change', c), { immediate: true })

const classNames = computed(() => state.classes.map((c) => c.name.trim()).filter(Boolean))

function addClass() {
  state.classes.push({ name: `Class${state.classes.length + 1}`, membersText: '' })
}
function removeClass(i) {
  state.classes.splice(i, 1)
}
function addRelation() {
  const names = classNames.value
  state.relations.push({ from: names[0] || '', to: names[1] || names[0] || '', type: 'association', label: '' })
}
function removeRelation(i) {
  state.relations.splice(i, 1)
}

const INPUT =
  'rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-sm text-slate-800 focus:border-brand-500 focus:outline-none dark:border-hairline dark:bg-surface-2 dark:text-slate-100'
</script>

<template>
  <div class="grid h-full grid-cols-1 md:grid-cols-2">
    <div class="min-h-0 space-y-4 overflow-y-auto p-4">
      <!-- Classes -->
      <div>
        <p class="mb-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400">{{ $t('editor.builders.classes') }}</p>
        <div class="space-y-2">
          <div v-for="(c, i) in state.classes" :key="i" class="rounded-xl border border-slate-200 p-2.5 dark:border-hairline">
            <div class="flex items-center gap-2">
              <input v-model="c.name" :class="[INPUT, 'min-w-0 flex-1 font-semibold']" :placeholder="$t('editor.builders.className')" />
              <button
                type="button"
                class="shrink-0 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-500/10"
                :title="$t('editor.builders.removeClass')"
                @click="removeClass(i)"
              >
                <Icon name="trash" class="h-4 w-4" />
              </button>
            </div>
            <textarea
              v-model="c.membersText"
              rows="2"
              :class="[INPUT, 'mt-2 w-full resize-y font-mono text-xs']"
              placeholder="+field: Type&#10;+method()"
            />
          </div>
        </div>
        <button
          type="button"
          class="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:border-brand-400 hover:text-brand-600 dark:border-hairline dark:text-slate-300"
          @click="addClass"
        >
          <Icon name="plus" class="h-4 w-4" /> {{ $t('editor.builders.addClass') }}
        </button>
      </div>

      <!-- Relationships -->
      <div>
        <p class="mb-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400">{{ $t('editor.builders.relationships') }}</p>
        <div class="space-y-2">
          <div v-for="(r, i) in state.relations" :key="i" class="flex flex-wrap items-center gap-1.5">
            <select v-model="r.from" :class="[INPUT, 'min-w-0 flex-1']">
              <option v-for="n in classNames" :key="n" :value="n">{{ n }}</option>
            </select>
            <select v-model="r.type" :class="[INPUT, 'min-w-0']">
              <option v-for="rel in CLASS_RELATIONS" :key="rel.type" :value="rel.type">{{ $t('editor.builders.rel.' + rel.type) }}</option>
            </select>
            <select v-model="r.to" :class="[INPUT, 'min-w-0 flex-1']">
              <option v-for="n in classNames" :key="n" :value="n">{{ n }}</option>
            </select>
            <input v-model="r.label" :class="[INPUT, 'w-24 min-w-0']" :placeholder="$t('editor.builders.label')" />
            <button
              type="button"
              class="shrink-0 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-500/10"
              :title="$t('editor.builders.remove')"
              @click="removeRelation(i)"
            >
              <Icon name="trash" class="h-4 w-4" />
            </button>
          </div>
        </div>
        <button
          type="button"
          class="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:border-brand-400 hover:text-brand-600 disabled:opacity-40 dark:border-hairline dark:text-slate-300"
          :disabled="classNames.length < 1"
          @click="addRelation"
        >
          <Icon name="plus" class="h-4 w-4" /> {{ $t('editor.builders.addRelation') }}
        </button>
      </div>
    </div>

    <div class="min-h-0 border-t border-slate-200 bg-slate-50 dark:border-hairline dark:bg-surface-2/40 md:border-l md:border-t-0">
      <MermaidPreview :code="out" />
    </div>
  </div>
</template>
