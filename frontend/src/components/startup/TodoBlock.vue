<script setup>
/**
 * Startup To-Do block — business tasks, kept separate from the learner's daily
 * study tasks. Add / tick / delete with optimistic updates + rollback, the same
 * pattern as the dashboard's TasksChecklist, backed by /api/startup/todos.
 */
import { computed, ref, watch } from 'vue'
import i18n from '@/i18n'

import CheckBox from '@/components/ui/CheckBox.vue'
import Icon from '@/components/ui/Icon.vue'
import BlockCard from './BlockCard.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import {
  createStartupTodo,
  deleteStartupTodo,
  listStartupTodos,
  updateStartupTodo,
} from '@/api/startup'

const { data, reload } = useAsyncData(listStartupTodos)
const items = ref([])
const pending = ref(0)
const draft = ref('')
const error = ref('')

// Seed the local list from the fetched payload, but never clobber pending edits.
const fetched = computed(() => data.value?.todos || [])
function sync() {
  if (!pending.value) items.value = [...fetched.value]
}
// useAsyncData fetches immediately; mirror it into the owned list once it lands.
watch(fetched, sync, { immediate: true })

const doneCount = computed(() => items.value.filter((t) => t.done).length)

async function run(fn, rollback) {
  pending.value++
  error.value = ''
  try {
    await fn()
  } catch (e) {
    rollback?.()
    error.value = e?.response?.data?.detail || i18n.global.t('misc.saveFailed')
  } finally {
    pending.value--
    if (!pending.value) await reload()
  }
}

async function add() {
  const title = draft.value.trim()
  if (!title) return
  draft.value = ''
  const temp = { id: `temp-${items.value.length}-${title}`, title, done: false, optimistic: true }
  items.value = [...items.value, temp]
  await run(
    async () => {
      const saved = await createStartupTodo(title)
      items.value = items.value.map((t) => (t.id === temp.id ? saved : t))
    },
    () => {
      items.value = items.value.filter((t) => t.id !== temp.id)
      draft.value = title
    },
  )
}

function toggle(task, next) {
  if (task.optimistic) return
  const before = task.done
  task.done = next
  run(
    () => updateStartupTodo(task.id, { done: next }),
    () => {
      task.done = before
    },
  )
}

function remove(task) {
  if (task.optimistic) return
  const before = items.value
  items.value = items.value.filter((t) => t.id !== task.id)
  run(
    () => deleteStartupTodo(task.id),
    () => {
      items.value = before
    },
  )
}
</script>

<template>
  <BlockCard
    icon="checkCircle"
    iconColor="text-sky-600"
    iconBg="bg-sky-50 dark:bg-sky-500/15"
    :title="$t('startup.todo.title')"
    :subtitle="$t('startup.todo.subtitle')"
  >
    <template #action>
      <span v-if="items.length" class="text-xs font-medium tabular-nums text-slate-400">{{ doneCount }}/{{ items.length }}</span>
    </template>

    <ul v-if="items.length" class="space-y-2.5">
      <li v-for="task in items" :key="task.id" class="group flex items-center gap-2">
        <CheckBox
          :model-value="task.done"
          :label="task.title"
          :disabled="task.optimistic"
          shape="square"
          strike-when-checked
          class="min-w-0 flex-1 [&>span:last-child]:truncate"
          @update:model-value="toggle(task, $event)"
        />
        <button type="button" class="shrink-0 rounded-lg p-1 text-slate-300 opacity-0 transition hover:bg-slate-100 hover:text-red-500 group-hover:opacity-100 dark:hover:bg-surface-2" :title="$t('common.delete')" @click="remove(task)">
          <Icon name="trash" class="h-3.5 w-3.5" />
        </button>
      </li>
    </ul>
    <p v-else class="text-sm text-slate-400">{{ $t('startup.todo.empty') }}</p>

    <form class="mt-4 flex items-center gap-2" @submit.prevent="add">
      <input v-model="draft" type="text" maxlength="200" :placeholder="$t('startup.todo.placeholder')" class="zx-input min-w-0 flex-1 py-2" />
      <button type="submit" :disabled="!draft.trim()" class="pill shrink-0 bg-brand-600 p-2 text-white hover:bg-brand-700 disabled:opacity-40" :title="$t('common.add')">
        <Icon name="plus" class="h-4 w-4" />
      </button>
    </form>

    <p v-if="error" class="mt-2 text-xs text-red-500">{{ error }}</p>
  </BlockCard>
</template>
