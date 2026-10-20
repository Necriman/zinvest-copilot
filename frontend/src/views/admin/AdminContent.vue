<script setup>
// Course content: units, their lessons and the unit test. Small edits happen in
// place; whole units come in as JSON through a checked import (dry run first).
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminModal from '@/components/admin/AdminModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'

const { t } = useI18n()
const admin = useAdmin()

const units = ref([])
const loading = ref(true)
const error = ref('')
const notice = ref('')
const open = ref('') // expanded unit id
const canEdit = computed(() => admin.can('content.manage'))

async function load() {
  loading.value = true
  error.value = ''
  try {
    units.value = (await admin.act(() => adminApi.content())).units
  } catch (e) {
    error.value = admin.errorText(e, t)
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ---- Unit and lesson edits -------------------------------------------------
const drafts = reactive({}) // unit id → { title, subtitle, pass }; lesson id → { title, estimated_minutes, coin_reward }
const saving = ref('')
const rowError = reactive({})

function toggle(unit) {
  open.value = open.value === unit.id ? '' : unit.id
  if (open.value && !drafts[unit.id]) {
    drafts[unit.id] = { title: unit.title, subtitle: unit.subtitle, pass: Math.round(unit.test_pass_threshold * 100) }
    for (const lesson of unit.lessons) {
      drafts[lesson.id] = { title: lesson.title, estimated_minutes: lesson.estimated_minutes, coin_reward: lesson.coin_reward }
    }
  }
}

const unitDirty = (unit) => {
  const d = drafts[unit.id]
  return !!d && (d.title !== unit.title || d.subtitle !== unit.subtitle || d.pass !== Math.round(unit.test_pass_threshold * 100))
}
const lessonDirty = (lesson) => {
  const d = drafts[lesson.id]
  return !!d && (d.title !== lesson.title || Number(d.estimated_minutes) !== lesson.estimated_minutes || Number(d.coin_reward) !== lesson.coin_reward)
}

async function save(id, fn, apply) {
  saving.value = id
  rowError[id] = ''
  notice.value = ''
  try {
    apply(await admin.act(fn))
    notice.value = t('admin.common.saved')
  } catch (e) {
    rowError[id] = admin.errorText(e, t)
  } finally {
    saving.value = ''
  }
}

function saveUnit(unit) {
  const d = drafts[unit.id]
  return save(
    unit.id,
    () => adminApi.updateUnit(unit.id, { title: d.title, subtitle: d.subtitle, test_pass_threshold: Number(d.pass) / 100 }),
    (fresh) => Object.assign(unit, fresh),
  )
}

function saveLesson(lesson) {
  const d = drafts[lesson.id]
  const data = { title: d.title, estimated_minutes: Number(d.estimated_minutes), coin_reward: Number(d.coin_reward) }
  return save(lesson.id, () => adminApi.updateLesson(lesson.id, data), () => Object.assign(lesson, data))
}

// ---- Test questions --------------------------------------------------------
const questions = reactive({ unit: null, text: '', error: '', errors: [] })

function editQuestions(unit) {
  questions.unit = unit
  questions.text = JSON.stringify(unit.test_questions || [], null, 2)
  questions.error = ''
  questions.errors = []
}

async function saveQuestions() {
  let parsed
  try {
    parsed = JSON.parse(questions.text)
  } catch {
    questions.error = t('admin.content.badJson')
    return
  }
  const unit = questions.unit
  saving.value = 'questions'
  questions.error = ''
  questions.errors = []
  try {
    Object.assign(unit, await admin.act(() => adminApi.updateUnit(unit.id, { test_questions: parsed })))
    questions.unit = null
    notice.value = t('admin.common.saved')
  } catch (e) {
    const data = e?.response?.data
    questions.errors = data?.errors || []
    questions.error = e?.cancelled ? '' : data?.detail || t('admin.common.error')
  } finally {
    saving.value = ''
  }
}

// ---- Import ----------------------------------------------------------------
const importer = reactive({ open: false, text: '', checked: '', busy: false, result: null, error: '' })

function openImport() {
  Object.assign(importer, { open: true, text: '', checked: '', result: null, error: '' })
}

async function readFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    importer.error = t('admin.content.badJson')
    return
  }
  importer.text = await file.text()
  importer.result = null
  importer.checked = ''
}

async function runImport(dryRun) {
  let document
  try {
    document = JSON.parse(importer.text)
  } catch {
    importer.error = t('admin.content.badJson')
    importer.result = null
    return
  }
  importer.busy = true
  importer.error = ''
  try {
    importer.result = await admin.act(() => adminApi.importContent(document, dryRun))
    importer.checked = dryRun ? importer.text : ''
    if (!dryRun) {
      notice.value = t('admin.content.imported')
      importer.open = false
      Object.keys(drafts).forEach((key) => delete drafts[key])
      await load()
    }
  } catch (e) {
    // A failed check still returns the plan with its errors (HTTP 400).
    const data = e?.response?.data
    if (data?.plan) importer.result = data
    else importer.error = admin.errorText(e, t)
    importer.checked = ''
  } finally {
    importer.busy = false
  }
}

const canApply = computed(() => importer.result?.ok && importer.checked === importer.text && !importer.busy)
</script>

<template>
  <div>
    <AdminHeader :title="$t('admin.content.title')" :intro="$t('admin.content.intro')">
      <AppButton v-if="canEdit" size="sm" icon="upload" @click="openImport">{{ $t('admin.content.import') }}</AppButton>
    </AdminHeader>

    <p v-if="error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>
    <p v-if="notice" class="mb-4 rounded-2xl bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-500/10 dark:text-green-300" role="status">{{ notice }}</p>

    <div v-if="loading && !units.length" class="space-y-3">
      <LoadingSkeleton v-for="i in 5" :key="i" height="h-16" rounded="rounded-3xl" />
    </div>

    <ul v-else class="space-y-3">
      <li v-for="unit in units" :key="unit.id" class="card overflow-hidden">
        <button
          type="button"
          class="flex w-full items-center gap-4 px-4 py-3.5 text-left transition hover:bg-slate-50 sm:px-5 dark:hover:bg-surface-2/50"
          :aria-expanded="open === unit.id"
          @click="toggle(unit)"
        >
          <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-sm font-extrabold text-brand-700 dark:bg-brand-500/15 dark:text-brand-300">
            {{ unit.code }}
          </span>
          <span class="min-w-0 flex-1">
            <span class="block truncate font-semibold text-slate-800 dark:text-slate-100">{{ unit.title }}</span>
            <span class="block truncate text-xs text-slate-400">
              {{ $t('admin.content.lessonsCount', { n: unit.lessons.length }) }} ·
              {{ $t('admin.content.questions', { n: unit.test_questions.length }) }} ·
              {{ $t('admin.content.passed', { n: unit.passed }) }}
            </span>
          </span>
          <Icon name="chevronDown" class="h-4 w-4 shrink-0 text-slate-400 transition-transform" :class="open === unit.id ? 'rotate-180' : ''" />
        </button>

        <div v-if="open === unit.id && drafts[unit.id]" class="border-t border-slate-100 px-4 py-4 sm:px-5 dark:border-hairline">
          <!-- Unit -->
          <form class="grid gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,2fr)_7rem_auto] sm:items-end" @submit.prevent="saveUnit(unit)">
            <label class="block">
              <span class="mb-1 block text-xs font-semibold text-slate-500">{{ $t('admin.content.name') }}</span>
              <input v-model="drafts[unit.id].title" class="zx-input" maxlength="120" :readonly="!canEdit" />
            </label>
            <label class="block">
              <span class="mb-1 block text-xs font-semibold text-slate-500">{{ $t('admin.content.subtitle') }}</span>
              <input v-model="drafts[unit.id].subtitle" class="zx-input" maxlength="200" :readonly="!canEdit" />
            </label>
            <label class="block">
              <span class="mb-1 block text-xs font-semibold text-slate-500">{{ $t('admin.content.passMark') }}</span>
              <input v-model.number="drafts[unit.id].pass" type="number" min="10" max="100" class="zx-input" :readonly="!canEdit" />
            </label>
            <AppButton v-if="canEdit" size="sm" type="submit" :disabled="!unitDirty(unit) || saving === unit.id">{{ $t('admin.common.save') }}</AppButton>
          </form>
          <p v-if="rowError[unit.id]" class="mt-2 text-sm text-red-600 dark:text-red-400">{{ rowError[unit.id] }}</p>

          <!-- Lessons -->
          <div class="mt-5 overflow-x-auto">
            <table class="w-full min-w-[620px] text-sm">
              <thead>
                <tr class="text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <th class="w-10 pb-2">#</th>
                  <th class="pb-2">{{ $t('admin.content.name') }}</th>
                  <th class="w-24 pb-2">{{ $t('admin.content.minutes') }}</th>
                  <th class="w-24 pb-2">{{ $t('admin.content.reward') }}</th>
                  <th class="w-28 pb-2 text-right">{{ $t('admin.content.finished') }}</th>
                  <th class="w-28 pb-2" />
                </tr>
              </thead>
              <tbody>
                <tr v-for="lesson in unit.lessons" :key="lesson.id" class="border-t border-slate-100 align-top dark:border-hairline/60">
                  <td class="py-2 pr-2 tabular-nums text-slate-400">{{ lesson.order }}</td>
                  <td class="py-2 pr-2">
                    <input v-model="drafts[lesson.id].title" class="zx-input py-1.5" maxlength="140" :readonly="!canEdit" :aria-label="$t('admin.content.name')" />
                    <p v-if="rowError[lesson.id]" class="mt-1 text-xs text-red-600 dark:text-red-400">{{ rowError[lesson.id] }}</p>
                  </td>
                  <td class="py-2 pr-2">
                    <input v-model.number="drafts[lesson.id].estimated_minutes" type="number" min="1" max="240" class="zx-input py-1.5" :readonly="!canEdit" :aria-label="$t('admin.content.minutes')" />
                  </td>
                  <td class="py-2 pr-2">
                    <input v-model.number="drafts[lesson.id].coin_reward" type="number" min="0" max="1000" class="zx-input py-1.5" :readonly="!canEdit" :aria-label="$t('admin.content.reward')" />
                  </td>
                  <td class="py-2 pr-2 text-right tabular-nums text-slate-500">{{ lesson.completions }}</td>
                  <td class="py-2 text-right">
                    <div class="flex items-center justify-end gap-1">
                      <button
                        v-if="canEdit && lessonDirty(lesson)"
                        type="button"
                        class="rounded-full bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
                        :disabled="saving === lesson.id"
                        @click="saveLesson(lesson)"
                      >
                        {{ $t('admin.common.save') }}
                      </button>
                      <RouterLink
                        :to="{ name: 'lesson', params: { lessonId: lesson.id } }"
                        class="flex h-8 w-8 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-surface-2"
                        :title="$t('admin.content.open')"
                        :aria-label="$t('admin.content.open')"
                        target="_blank"
                        rel="noopener"
                      >
                        <Icon name="eye" class="h-4 w-4" />
                      </RouterLink>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="mt-4 flex flex-wrap items-center justify-between gap-2">
            <p class="text-xs text-slate-400">slug: {{ unit.slug }}</p>
            <AppButton variant="outline" size="sm" icon="braces" @click="editQuestions(unit)">
              {{ $t('admin.content.editTest') }}
            </AppButton>
          </div>
        </div>
      </li>
    </ul>

    <!-- Test questions -->
    <AdminModal :open="!!questions.unit" wide :title="$t('admin.content.editTest')" :text="questions.unit?.title" @close="questions.unit = null">
      <textarea
        v-model="questions.text"
        rows="16"
        spellcheck="false"
        class="zx-input font-mono text-xs leading-relaxed"
        :readonly="!canEdit"
        :aria-label="$t('admin.content.editTest')"
      />
      <p v-if="questions.error" class="mt-2 text-sm font-semibold text-red-600 dark:text-red-400">{{ questions.error }}</p>
      <ul v-if="questions.errors.length" class="mt-1 list-disc space-y-0.5 pl-5 text-xs text-red-600 dark:text-red-400">
        <li v-for="(line, i) in questions.errors" :key="i">{{ line }}</li>
      </ul>
      <div v-if="canEdit" class="mt-4 flex justify-end gap-2">
        <AppButton variant="ghost" size="sm" @click="questions.unit = null">{{ $t('admin.common.cancel') }}</AppButton>
        <AppButton size="sm" :disabled="saving === 'questions'" @click="saveQuestions">{{ $t('admin.common.save') }}</AppButton>
      </div>
    </AdminModal>

    <!-- Import -->
    <AdminModal :open="importer.open" wide :title="$t('admin.content.import')" :text="$t('admin.content.importHint')" @close="importer.open = false">
      <div class="mb-2 flex justify-end">
        <label class="pill cursor-pointer border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-hairline dark:bg-surface dark:text-slate-200 dark:hover:bg-surface-2">
          <Icon name="upload" class="h-3.5 w-3.5" /> {{ $t('admin.content.chooseFile') }}
          <input type="file" accept=".json,application/json" class="sr-only" @change="readFile" />
        </label>
      </div>
      <textarea
        v-model="importer.text"
        rows="12"
        spellcheck="false"
        class="zx-input font-mono text-xs leading-relaxed"
        placeholder='{ "code": "09", "slug": "…", "title": "…", "order": 9, "lessons": [ … ] }'
        :aria-label="$t('admin.content.import')"
      />
      <p v-if="importer.error" class="mt-2 text-sm text-red-600 dark:text-red-400">{{ importer.error }}</p>

      <div v-if="importer.result" class="mt-4 space-y-3 text-sm">
        <div v-if="importer.result.errors?.length" class="rounded-2xl bg-red-50 px-4 py-3 dark:bg-red-500/10">
          <p class="font-semibold text-red-700 dark:text-red-300">{{ $t('admin.content.errors') }}</p>
          <ul class="mt-1 list-disc space-y-0.5 pl-5 text-xs text-red-700 dark:text-red-300">
            <li v-for="(line, i) in importer.result.errors" :key="i">{{ line }}</li>
          </ul>
        </div>
        <div v-if="importer.result.warnings?.length" class="rounded-2xl bg-amber-50 px-4 py-3 dark:bg-amber-500/10">
          <p class="font-semibold text-amber-800 dark:text-amber-200">{{ $t('admin.content.warnings') }}</p>
          <ul class="mt-1 list-disc space-y-0.5 pl-5 text-xs text-amber-800 dark:text-amber-200">
            <li v-for="(line, i) in importer.result.warnings" :key="i">{{ line }}</li>
          </ul>
        </div>
        <div v-if="importer.result.plan?.length">
          <p class="mb-2 font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.content.plan') }}</p>
          <ul class="space-y-2">
            <li v-for="unit in importer.result.plan" :key="unit.slug" class="rounded-2xl border border-slate-200 px-4 py-3 dark:border-hairline">
              <p class="flex flex-wrap items-center gap-2 font-semibold text-slate-800 dark:text-slate-100">
                {{ unit.unit }}
                <PillBadge :color="unit.action === 'create' ? 'cash' : 'invest'" size="sm">{{ $t(`admin.content.${unit.action}`) }}</PillBadge>
                <span class="text-xs font-normal text-slate-400">{{ $t('admin.content.questions', { n: unit.questions }) }}</span>
              </p>
              <ul class="mt-2 grid gap-1 text-xs sm:grid-cols-2">
                <li v-for="lesson in unit.lessons" :key="lesson.slug" class="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                  <span class="h-1.5 w-1.5 shrink-0 rounded-full" :class="lesson.action === 'create' ? 'bg-green-500' : 'bg-blue-500'" />
                  <span class="truncate">{{ lesson.title }}</span>
                </li>
              </ul>
            </li>
          </ul>
        </div>
      </div>

      <div class="mt-4 flex justify-end gap-2">
        <AppButton variant="outline" size="sm" icon="check" :disabled="importer.busy || !importer.text.trim()" @click="runImport(true)">
          {{ $t('admin.content.check') }}
        </AppButton>
        <AppButton size="sm" icon="upload" :disabled="!canApply" @click="runImport(false)">{{ $t('admin.content.apply') }}</AppButton>
      </div>
    </AdminModal>
  </div>
</template>
