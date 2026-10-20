<script setup>
/**
 * Bulk import for a workspace block: pick a CSV/JSON file, preview the parsed
 * rows, then send them in one request. The server saves all rows or none, so a
 * failed import can simply be fixed and retried without creating duplicates.
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import Icon from '@/components/ui/Icon.vue'
import { IMPORT_FIELDS, TEMPLATES, readImportFile } from '@/utils/tableImport'

const props = defineProps({
  kind: { type: String, required: true }, // 'employees' | 'products'
  importer: { type: Function, required: true },
})
const emit = defineEmits(['imported'])
const { t } = useI18n()

const input = ref(null)
const open = ref(false)
const rows = ref([])
const fileName = ref('')
const busy = ref(false)
const error = ref('')
const rowErrors = ref([])
const done = ref('')

const columns = computed(() => Object.keys(IMPORT_FIELDS[props.kind]))
const preview = computed(() => rows.value.slice(0, 5))

const templateUrl = URL.createObjectURL(new Blob([TEMPLATES[props.kind]], { type: 'text/csv' }))
onBeforeUnmount(() => URL.revokeObjectURL(templateUrl))

function reset() {
  rows.value = []
  fileName.value = ''
  error.value = ''
  rowErrors.value = []
}

function toggle() {
  open.value = !open.value
  done.value = ''
  if (!open.value) reset()
}

async function onFile(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  reset()
  done.value = ''
  fileName.value = file.name
  if (file.size > 2 * 1024 * 1024) {
    error.value = t('imports.tooBig')
    return
  }
  try {
    rows.value = await readImportFile(file, props.kind)
    if (!rows.value.length) error.value = t('imports.empty')
  } catch (err) {
    error.value = t(err.message === 'columns' ? `imports.columns_${props.kind}` : 'imports.format')
  }
}

async function confirm() {
  if (!rows.value.length || busy.value) return
  busy.value = true
  error.value = ''
  rowErrors.value = []
  try {
    const result = await props.importer(rows.value)
    done.value = t('imports.done', { n: result.imported })
    reset()
    emit('imported', result)
  } catch (err) {
    const data = err?.response?.data
    error.value = data?.detail || err.message
    rowErrors.value = data?.errors || []
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div>
    <button
      type="button"
      class="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-sm font-semibold text-slate-500 transition hover:bg-slate-100 dark:hover:bg-surface-2"
      :aria-expanded="open"
      @click="toggle"
    >
      <Icon name="upload" class="h-4 w-4" />
      {{ $t('imports.button') }}
    </button>

    <Teleport :to="`#import-slot-${kind}`" defer>
      <div v-if="open" class="mb-4 space-y-3 rounded-2xl bg-slate-50 p-3 text-sm dark:bg-surface-2">
        <p class="text-slate-600 dark:text-slate-300">{{ $t(`imports.hint_${kind}`) }}</p>
        <div class="flex flex-wrap items-center gap-2">
          <button type="button" class="pill bg-brand-600 px-4 py-2 font-semibold text-white hover:bg-brand-700" @click="input?.click()">
            {{ $t('imports.choose') }}
          </button>
          <a :href="templateUrl" :download="`zinvest-${kind}-template.csv`" class="px-2 py-2 font-semibold text-brand-600">
            {{ $t('imports.template') }}
          </a>
        </div>
        <input ref="input" type="file" accept=".csv,.json,.txt,.tsv,text/csv,application/json" class="hidden" @change="onFile" />

        <template v-if="rows.length">
          <p class="font-semibold">{{ $t('imports.found', { n: rows.length, file: fileName }) }}</p>
          <div class="overflow-x-auto rounded-xl border border-hairline bg-white dark:bg-surface">
            <table class="w-full text-left text-xs">
              <thead><tr><th v-for="c in columns" :key="c" class="px-2 py-1.5 font-semibold text-slate-500">{{ c }}</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in preview" :key="i" class="border-t border-hairline">
                  <td v-for="c in columns" :key="c" class="max-w-[10rem] truncate px-2 py-1.5">{{ r[c] }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="rows.length > preview.length" class="text-xs text-slate-500">{{ $t('imports.more', { n: rows.length - preview.length }) }}</p>
          <div class="flex gap-2">
            <button type="button" :disabled="busy" class="pill bg-brand-600 px-4 py-2 font-semibold text-white hover:bg-brand-700 disabled:opacity-40" @click="confirm">
              {{ busy ? '…' : $t('imports.confirm', { n: rows.length }) }}
            </button>
            <button type="button" class="px-3 py-2 text-slate-500" @click="reset">{{ $t('common.cancel') }}</button>
          </div>
        </template>

        <div v-if="error" role="alert" class="text-red-600">
          <p>{{ error }}</p>
          <ul v-if="rowErrors.length" class="mt-1 list-disc pl-5 text-xs">
            <li v-for="e in rowErrors" :key="e.row">{{ $t('imports.row', { n: e.row }) }}: {{ e.detail }}</li>
          </ul>
        </div>
        <p v-if="done" role="status" class="font-semibold text-emerald-700">{{ done }}</p>
      </div>
    </Teleport>
  </div>
</template>
