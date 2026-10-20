<script setup>
/**
 * Today's tasks — add, tick and delete, backed by /api/learning/tasks.
 *
 * The list is seeded from the shared stats payload (so first paint costs no
 * extra request) and then owned locally. Every mutation is applied optimistically
 * and rolled back if the server rejects it, which keeps ticking a box instant.
 */
import { computed, ref, watch } from 'vue'
import i18n from '@/i18n'

import CheckBox from '@/components/ui/CheckBox.vue'
import Icon from '@/components/ui/Icon.vue'
import { createTask, deleteTask, updateTask } from '@/api/tasks'

const props = defineProps({ tasks: { type: Array, default: () => [] } })
const emit = defineEmits(['changed'])

const items = ref([...props.tasks])
// Re-seed when the shared stats payload refreshes, but never clobber pending
// local edits with a stale snapshot.
watch(
  () => props.tasks,
  (next) => {
    if (!pending.value) items.value = [...next]
  },
)

const pending = ref(0)
const draft = ref('')
const error = ref('')
const doneCount = computed(() => items.value.filter((t) => t.done).length)

async function run(fn, rollback) {
  pending.value++
  error.value = ''
  try {
    await fn()
    emit('changed')
  } catch (e) {
    rollback?.()
    error.value = e?.response?.data?.detail || i18n.global.t('misc.saveFailedRetry')
  } finally {
    pending.value--
  }
}

async function add() {
  const title = draft.value.trim()
  if (!title) return
  draft.value = ''
  // Optimistic row; swapped for the server's once it lands (we need the real id).
  const temp = { id: `temp-${Date.now()}`, title, done: false, optimistic: true }
  items.value = [...items.value, temp]
  await run(
    async () => {
      const saved = await createTask(title)
      items.value = items.value.map((t) => (t.id === temp.id ? saved : t))
    },
    () => {
      items.value = items.value.filter((t) => t.id !== temp.id)
      draft.value = title // hand the text back rather than losing it
    },
  )
}

function toggle(task, next) {
  if (task.optimistic) return
  const before = task.done
  task.done = next
  run(
    () => updateTask(task.id, { done: next }),
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
    () => deleteTask(task.id),
    () => {
      items.value = before
    },
  )
}
</script>

<template>
  <div class="card p-5">
    <div class="flex items-center justify-between">
      <span class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
        <Icon name="checkCircle" class="h-4 w-4 text-brand-600" />
        {{ $t('dashboard.todaysTasks') }}
      </span>
      <span v-if="items.length" class="text-xs font-medium tabular-nums text-slate-400">
        {{ doneCount }}/{{ items.length }}
      </span>
    </div>

    <ul v-if="items.length" class="mt-4 space-y-2.5">
      <li v-for="task in items" :key="task.id" class="group flex items-center gap-2">
        <CheckBox
          :model-value="task.done"
          :label="task.title"
          :disabled="task.optimistic"
          strike-when-checked
          class="min-w-0 flex-1 [&>span:last-child]:truncate"
          @update:model-value="toggle(task, $event)"
        />
        <button
          type="button"
          class="shrink-0 rounded-lg p-1 text-slate-300 opacity-0 transition hover:bg-slate-100 hover:text-red-500 focus-visible:opacity-100 group-hover:opacity-100 dark:hover:bg-surface-2"
          :title="$t('common.delete')"
          @click="remove(task)"
        >
          <Icon name="trash" class="h-3.5 w-3.5" />
        </button>
      </li>
    </ul>
    <p v-else class="mt-4 text-sm text-slate-400">{{ $t('dashboard.noTasks') }}</p>

    <form class="mt-4 flex items-center gap-2" @submit.prevent="add">
      <input
        v-model="draft"
        type="text"
        maxlength="200"
        :placeholder="$t('dashboard.addTaskPlaceholder')"
        class="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none dark:border-hairline dark:bg-surface-2 dark:text-slate-100"
      />
      <button
        type="submit"
        :disabled="!draft.trim()"
        class="shrink-0 rounded-xl bg-brand-600 p-2 text-white transition hover:bg-brand-700 disabled:opacity-40"
        :title="$t('dashboard.addTask')"
      >
        <Icon name="plus" class="h-4 w-4" />
      </button>
    </form>

    <p v-if="error" class="mt-2 text-xs text-red-500">{{ error }}</p>
  </div>
</template>
