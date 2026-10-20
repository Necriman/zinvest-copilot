<script setup>
/**
 * Task Dashboard block (AI-gated / optional): the founder assigns a task with a
 * date range to a specific employee. Rows read like
 *   Nodir — Resolve the 2nd floor · 19.07.2026 – 21.07.2026
 * with a tick to close them out.
 */
import { computed, reactive, ref, watch } from 'vue'
import i18n from '@/i18n'

import Icon from '@/components/ui/Icon.vue'
import CheckBox from '@/components/ui/CheckBox.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import BlockCard from './BlockCard.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import {
  createAssignment,
  deleteAssignment,
  listAssignments,
  listEmployees,
  updateAssignment,
} from '@/api/startup'

const { data: assignData, reload } = useAsyncData(listAssignments)
const props=defineProps({rosterVersion:Number})
const { data: empData, reload:reloadEmployees } = useAsyncData(listEmployees)
watch(()=>props.rosterVersion,()=>Promise.all([reloadEmployees(),reload()]).catch(e=>error.value=e?.response?.data?.detail||e.message))
const assignments = computed(() => assignData.value?.assignments || [])
const employees = computed(() => empData.value?.employees || [])

const adding = ref(false)
const form = reactive({ employee: '', title: '', start_date: '', end_date: '' })
const busy = ref(false)
const error = ref('')

async function save() {
  if (!form.employee || !form.title.trim() || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await createAssignment({
      employee: form.employee,
      title: form.title,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
    })
    form.employee = ''
    form.title = ''
    form.start_date = ''
    form.end_date = ''
    adding.value = false
    await reload()
  } catch (e) {
    error.value = e?.response?.data?.detail || i18n.global.t('misc.saveFailed')
  } finally {
    busy.value = false
  }
}

async function toggle(a, done) {
  try{await updateAssignment(a.id, { done });await reload()}catch(e){error.value=e?.response?.data?.detail||e.message}
}

async function remove(id) {
  try{await deleteAssignment(id);await reload()}catch(e){error.value=e?.response?.data?.detail||e.message}
}

function fmtDate(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

function range(a) {
  if (a.start_date && a.end_date) return `${fmtDate(a.start_date)} – ${fmtDate(a.end_date)}`
  return fmtDate(a.start_date) || fmtDate(a.end_date) || ''
}
</script>

<template>
  <BlockCard
    icon="taskList"
    iconColor="text-violet-600"
    iconBg="bg-violet-50 dark:bg-violet-500/15"
    :title="$t('startup.tasks.title')"
    :subtitle="$t('startup.tasks.subtitle')"
  >
    <template #action>
      <button
        type="button"
        :disabled="!employees.length"
        class="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-sm font-semibold text-brand-600 transition hover:bg-brand-50 disabled:opacity-40 dark:hover:bg-brand-500/10"
        @click="adding = !adding"
      >
        <Icon :name="adding ? 'x' : 'plus'" class="h-4 w-4" />
        {{ adding ? $t('common.cancel') : $t('startup.tasks.assign') }}
      </button>
    </template>

    <p v-if="!employees.length" class="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500 dark:bg-surface-2">
      {{ $t('startup.tasks.needEmployees') }}
    </p>

    <form v-else-if="adding" class="mb-4 space-y-2 rounded-2xl bg-slate-50 p-3 dark:bg-surface-2" @submit.prevent="save">
      <select v-model="form.employee" class="zx-input w-full py-2">
        <option value="" disabled>{{ $t('startup.tasks.selectEmployee') }}</option>
        <option v-for="e in employees" :key="e.id" :value="e.id">{{ e.full_name }}</option>
      </select>
      <input v-model="form.title" :placeholder="$t('startup.tasks.titlePlaceholder')" class="zx-input w-full py-2" />
      <div class="flex items-center gap-2">
        <input v-model="form.start_date" type="date" class="zx-input w-full py-2" :aria-label="$t('startup.tasks.start')" />
        <span class="text-slate-400">–</span>
        <input v-model="form.end_date" type="date" class="zx-input w-full py-2" :aria-label="$t('startup.tasks.end')" />
      </div>
      <button type="submit" :disabled="busy || !form.employee || !form.title.trim()" class="pill w-full justify-center bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40">
        {{ $t('common.save') }}
      </button>
    </form>

    <EmptyState v-if="employees.length && !assignments.length" icon="taskList" :message="$t('startup.tasks.empty')" />

    <ul v-else-if="assignments.length" class="space-y-2.5">
      <li v-for="a in assignments" :key="a.id" class="group flex items-center gap-3">
        <CheckBox :model-value="a.done" shape="square" class="shrink-0" @update:model-value="toggle(a, $event)" />
        <div class="min-w-0 flex-1" :class="a.done ? 'opacity-50' : ''">
          <p class="truncate text-sm" :class="a.done ? 'text-slate-400 line-through' : 'text-slate-800 dark:text-ink'">
            <span class="font-semibold text-brand-600">{{ a.employee_name }}</span>
            <span class="text-slate-400"> — </span>{{ a.title }}
          </p>
          <p v-if="range(a)" class="text-xs tabular-nums text-slate-400">{{ range(a) }}</p>
        </div>
        <button type="button" class="shrink-0 rounded-lg p-1.5 text-slate-300 opacity-0 transition hover:bg-slate-100 hover:text-red-500 group-hover:opacity-100 dark:hover:bg-surface-2" :title="$t('common.delete')" @click="remove(a.id)">
          <Icon name="trash" class="h-3.5 w-3.5" />
        </button>
      </li>
    </ul>

    <p v-if="error" class="mt-2 text-xs text-red-500">{{ error }}</p>
  </BlockCard>
</template>
