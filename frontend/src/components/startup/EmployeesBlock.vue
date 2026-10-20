<script setup>
/**
 * Employees block: the team as small cards (photo, role, full name), with a
 * "+" tile to add someone and the total payroll underneath.
 *
 * Adding and editing share one form: photo on the left, then name, role (the
 * short title on the card) and what they do; team and salary below. A picked
 * photo previews right away and uploads after the person is saved, so a new
 * employee gets their photo in the same step. List mutations reload the
 * payload so the payroll total (a server aggregate) stays correct.
 */
import { computed, nextTick, onBeforeUnmount, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import Avatar from '@/components/ui/Avatar.vue'
import Icon from '@/components/ui/Icon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import BlockCard from './BlockCard.vue'
import BulkImport from './BulkImport.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import {
  createEmployee,
  importEmployees,
  deleteEmployee,
  listEmployees,
  updateEmployee,
  uploadEmployeePhoto,
} from '@/api/startup'
import { money } from '@/utils/format'

const emit = defineEmits(['changed'])
const { t } = useI18n()

const { data, reload } = useAsyncData(listEmployees)
const employees = computed(() => data.value?.employees || [])
const teamFilter = ref('')
const teams = computed(() => [...new Set(employees.value.map((e) => e.team).filter(Boolean))])
const filtered = computed(() => (teamFilter.value ? employees.value.filter((e) => e.team === teamFilter.value) : employees.value))
const totalSalary = computed(() => data.value?.total_salary || '0')

// --- the form ---------------------------------------------------------------
const open = ref(false)
const form = reactive({ id: null, full_name: '', position: '', role: '', team: '', salary: '', photo_url: '' })
const photo = reactive({ file: null, preview: '' })
const busy = ref(false)
const error = ref('')
const confirmingDelete = ref(false)
const nameInput = ref(null)
const fileInput = ref(null)

function clearPhoto() {
  if (photo.preview) URL.revokeObjectURL(photo.preview)
  photo.file = null
  photo.preview = ''
}
onBeforeUnmount(clearPhoto)

async function startForm(emp = null) {
  clearPhoto()
  Object.assign(form, emp
    ? { id: emp.id, full_name: emp.full_name, position: emp.position || '', role: emp.role || '', team: emp.team || '', salary: emp.salary, photo_url: emp.photo_url || '' }
    : { id: null, full_name: '', position: '', role: '', team: '', salary: '', photo_url: '' })
  error.value = ''
  confirmingDelete.value = false
  open.value = true
  await nextTick()
  nameInput.value?.focus()
}

function closeForm() {
  open.value = false
  clearPhoto()
}

function onFile(e) {
  const file = e.target.files?.[0]
  e.target.value = '' // allow re-picking the same file
  if (!file) return
  clearPhoto()
  photo.file = file
  photo.preview = URL.createObjectURL(file)
}

const shownPhoto = computed(() => photo.preview || form.photo_url)

async function save() {
  if (!form.full_name.trim() || busy.value) return
  busy.value = true
  error.value = ''
  const payload = { full_name: form.full_name, position: form.position, role: form.role, team: form.team, salary: form.salary || 0 }
  try {
    const saved = form.id ? await updateEmployee(form.id, payload) : await createEmployee(payload)
    if (photo.file) {
      try {
        await uploadEmployeePhoto(saved.employee.id, photo.file)
      } catch (e) {
        error.value = t('employeeCard.photoFailed', { error: e?.response?.data?.detail || t('misc.uploadFailed') })
      }
    }
    if (!error.value) closeForm()
    else form.id = saved.employee.id // keep the form so the photo can be picked again
    await reload()
    emit('changed')
  } catch (e) {
    error.value = e?.response?.data?.detail || t('misc.saveFailed')
  } finally {
    busy.value = false
  }
}

async function remove() {
  if (!form.id || busy.value) return
  if (!confirmingDelete.value) {
    confirmingDelete.value = true
    return
  }
  busy.value = true
  try {
    await deleteEmployee(form.id)
    closeForm()
    await reload()
    emit('changed')
  } catch (e) {
    error.value = e?.response?.data?.detail || e.message
  } finally {
    busy.value = false
  }
}

async function onImported() {
  await reload()
  emit('changed')
}
</script>

<template>
  <BlockCard
    icon="user"
    :title="$t('startup.employees.title')"
    :subtitle="$t('startup.employees.subtitle')"
  >
    <template #action>
      <div class="flex items-center gap-1">
        <BulkImport kind="employees" :importer="importEmployees" @imported="onImported" />
        <button
          type="button"
          class="flex min-h-9 items-center gap-1 rounded-lg px-2.5 text-sm font-semibold text-brand-600 transition hover:bg-brand-50 dark:hover:bg-brand-500/10"
          @click="open ? closeForm() : startForm()"
        >
          <Icon :name="open ? 'x' : 'plus'" class="h-4 w-4" />
          {{ open ? $t('common.cancel') : $t('startup.employees.add') }}
        </button>
      </div>
    </template>

    <div id="import-slot-employees" />

    <!-- Add / edit form -->
    <form v-if="open" class="mb-4 rounded-2xl bg-slate-50 p-3 dark:bg-surface-2" @submit.prevent="save">
      <p class="mb-3 text-sm font-bold text-slate-800 dark:text-ink">
        {{ form.id ? form.full_name : $t('employeeCard.newTitle') }}
      </p>
      <div class="flex gap-3">
        <div class="shrink-0 text-center">
          <button
            type="button"
            class="group relative flex h-[7.5rem] w-24 flex-col items-center justify-center gap-1 overflow-hidden rounded-2xl border-2 border-dashed text-slate-400 transition hover:border-brand-400 hover:text-brand-600 focus-visible:border-brand-500"
            :class="shownPhoto ? 'border-transparent' : 'border-slate-300 dark:border-hairline'"
            :aria-label="shownPhoto ? $t('employeeCard.changePhoto') : $t('employeeCard.addPhoto')"
            @click="fileInput?.click()"
          >
            <template v-if="shownPhoto">
              <img :src="shownPhoto" alt="" class="absolute inset-0 h-full w-full object-cover" />
              <span class="absolute inset-x-0 bottom-0 bg-slate-900/60 py-1 text-[11px] font-semibold text-white opacity-0 transition group-hover:opacity-100 group-focus-visible:opacity-100">
                {{ $t('employeeCard.changePhoto') }}
              </span>
            </template>
            <template v-else>
              <Icon name="upload" class="h-5 w-5" />
              <span class="px-1 text-[11px] font-semibold leading-tight">{{ $t('employeeCard.addPhoto') }}</span>
            </template>
          </button>
          <p class="mt-1 w-24 text-[10px] leading-tight text-slate-400">{{ $t('employeeCard.photoHint') }}</p>
          <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp,image/gif" class="hidden" @change="onFile" />
        </div>
        <div class="min-w-0 flex-1 space-y-2">
          <input
            ref="nameInput"
            v-model="form.full_name"
            maxlength="120"
            required
            :aria-label="$t('employeeCard.name')"
            :placeholder="$t('employeeCard.name')"
            class="zx-input w-full py-2"
          />
          <input
            v-model="form.position"
            maxlength="80"
            :aria-label="$t('employeeCard.position')"
            :placeholder="$t('employeeCard.positionPlaceholder')"
            class="zx-input w-full py-2"
          />
          <textarea
            v-model="form.role"
            rows="2"
            maxlength="2000"
            :aria-label="$t('employeeCard.duties')"
            :placeholder="$t('employeeCard.dutiesPlaceholder')"
            class="zx-input w-full resize-y py-2"
          />
        </div>
      </div>
      <div class="mt-2 grid gap-2 sm:grid-cols-2">
        <label class="block text-xs font-semibold text-slate-500">
          {{ $t('business.team') }}
          <input v-model="form.team" maxlength="80" class="zx-input mt-1 w-full py-2 text-sm font-normal" />
        </label>
        <label class="block text-xs font-semibold text-slate-500">
          {{ $t('employeeCard.salary') }}
          <input v-model="form.salary" type="number" min="0" step="0.01" class="zx-input mt-1 w-full py-2 text-sm font-normal" />
        </label>
      </div>
      <div class="mt-3 flex flex-wrap items-center justify-between gap-2">
        <button
          v-if="form.id"
          type="button"
          :disabled="busy"
          class="flex min-h-10 items-center gap-1.5 rounded-xl px-3 text-sm font-semibold transition disabled:opacity-40"
          :class="confirmingDelete ? 'bg-red-600 text-white hover:bg-red-700' : 'text-red-600 hover:bg-red-50 dark:hover:bg-red-500/10'"
          @click="remove"
        >
          <Icon name="trash" class="h-4 w-4" />
          {{ confirmingDelete ? $t('employeeCard.confirmDelete', { name: form.full_name }) : $t('common.delete') }}
        </button>
        <span v-else />
        <div class="flex gap-2">
          <button type="button" class="min-h-10 rounded-xl px-3 text-sm font-semibold text-slate-500 hover:bg-slate-100 dark:hover:bg-surface" @click="closeForm">
            {{ $t('common.cancel') }}
          </button>
          <button type="submit" :disabled="busy || !form.full_name.trim()" class="pill min-h-10 bg-brand-600 px-5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40">
            {{ $t('common.save') }}
          </button>
        </div>
      </div>
      <p v-if="error" role="alert" class="mt-2 text-xs text-red-500">{{ error }}</p>
    </form>

    <EmptyState v-if="!employees.length && !open" bear="tablet" :message="$t('startup.employees.empty')" />

    <!-- Team filter -->
    <div v-if="teams.length" class="mb-3 flex flex-wrap gap-1.5" role="group" :aria-label="$t('business.team')">
      <button
        v-for="team in ['', ...teams]"
        :key="team || 'all'"
        type="button"
        class="min-h-8 rounded-full border px-3 text-xs font-semibold transition"
        :class="teamFilter === team ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-200 text-slate-600 hover:border-brand-300 dark:border-hairline dark:text-slate-300'"
        :aria-pressed="teamFilter === team"
        @click="teamFilter = team"
      >
        {{ team || `${$t('business.allTeams')} · ${employees.length}` }}
      </button>
    </div>

    <!-- Cards -->
    <ul class="grid gap-2.5 [grid-template-columns:repeat(auto-fill,minmax(12rem,1fr))]">
      <li v-for="emp in filtered" :key="emp.id">
        <button
          type="button"
          class="flex w-full items-center gap-3 rounded-2xl border bg-white p-2.5 text-left transition hover:border-brand-300 hover:shadow-sm dark:bg-surface"
          :class="open && form.id === emp.id ? 'border-brand-500 ring-2 ring-brand-500/20' : 'border-slate-200 dark:border-hairline'"
          :aria-label="$t('employeeCard.open', { name: emp.full_name })"
          @click="startForm(emp)"
        >
          <Avatar :name="emp.full_name" :src="emp.photo_url || ''" size="h-14 w-14 text-base" rounded="rounded-xl" />
          <span class="min-w-0 flex-1">
            <span
              class="block truncate text-xs font-semibold"
              :class="emp.position ? 'text-brand-600 dark:text-brand-300' : 'text-slate-400'"
            >{{ emp.position || $t('employeeCard.noRole') }}</span>
            <span class="mt-0.5 block border-t border-slate-100 pt-0.5 text-sm font-bold leading-snug text-slate-900 [overflow-wrap:anywhere] dark:border-hairline dark:text-ink">{{ emp.full_name }}</span>
          </span>
        </button>
      </li>
      <li v-if="!open">
        <button
          type="button"
          class="flex h-full min-h-[4.75rem] w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-slate-200 text-sm font-semibold text-slate-400 transition hover:border-brand-400 hover:text-brand-600 dark:border-hairline"
          @click="startForm()"
        >
          <Icon name="plus" class="h-5 w-5" />
          {{ $t('employeeCard.add') }}
        </button>
      </li>
    </ul>

    <div class="mt-4 flex items-center justify-between border-t border-slate-100 pt-4 dark:border-hairline">
      <span class="text-sm font-medium text-slate-500">{{ $t('startup.employees.totalPayroll') }}</span>
      <span class="text-lg font-extrabold text-slate-900 dark:text-white">{{ money(totalSalary) }}</span>
    </div>
  </BlockCard>
</template>
