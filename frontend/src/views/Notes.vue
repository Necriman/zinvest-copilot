<script setup>
/** Notes — a grid of note "sheets". Clicking one opens it in the editor. */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import NoteCard from '@/components/notes/NoteCard.vue'
import AlertModal from '@/components/ui/AlertModal.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import SearchField from '@/components/ui/SearchField.vue'
import { useNotes } from '@/composables/useNotes'

const router = useRouter()
const { notes, loading, error, ensureLoaded, create, remove } = useNotes()

const query = ref('')
const creating = ref(false)
const pendingDelete = ref(null)
const focusedId = ref(null) // single-clicked card; double-click is what opens

onMounted(() => ensureLoaded().catch(() => {}))

const visible = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return notes.value
  return notes.value.filter(
    (n) => n.title.toLowerCase().includes(q) || (n.excerpt || '').toLowerCase().includes(q),
  )
})

async function newNote() {
  creating.value = true
  try {
    const note = await create({ title: '', content: '' })
    router.push({ name: 'noteEditor', params: { noteId: note.id } })
  } catch {
    /* surfaced via `error` */
  } finally {
    creating.value = false
  }
}

function open(id) {
  router.push({ name: 'noteEditor', params: { noteId: id } })
}

async function confirmDelete() {
  const id = pendingDelete.value?.id
  pendingDelete.value = null
  if (id) await remove(id).catch(() => {})
}
</script>

<template>
  <div>
    <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
        {{ $t('nav.notes') }}
      </h1>
      <div class="flex items-center gap-2">
        <SearchField
          v-model="query"
          class="w-44 sm:w-56"
          :placeholder="$t('notes.search')"
          :clear-label="$t('common.clearSearch')"
        />
        <button
          type="button"
          :disabled="creating"
          class="flex items-center gap-1.5 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
          :title="$t('notes.newNoteTip')"
          @click="newNote"
        >
          <Icon name="plus" class="h-4 w-4" />
          {{ $t('notes.newNote') }}
        </button>
      </div>
    </div>

    <p v-if="error" class="mb-4 rounded-xl bg-red-50 px-4 py-2 text-sm text-red-600 dark:bg-red-500/10">
      {{ error }}
    </p>

    <div v-if="loading && !notes.length" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <LoadingSkeleton v-for="n in 6" :key="n" height="h-56" rounded="rounded-2xl" />
    </div>

    <EmptyState
      v-else-if="!notes.length"
      bear="book"
      :title="$t('notes.emptyTitle')"
      :message="$t('notes.emptyMessage')"
    >
      <button
        type="button"
        class="mt-1 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        @click="newNote"
      >
        {{ $t('notes.newNote') }}
      </button>
    </EmptyState>

    <EmptyState
      v-else-if="!visible.length"
      bear="confused"
      :title="$t('notes.noMatches')"
      :message="$t('notes.noMatchesHint')"
    />

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <NoteCard
        v-for="note in visible"
        :key="note.id"
        :note="note"
        :focused="focusedId === note.id"
        @focus="focusedId = $event"
        @open="open"
        @delete="pendingDelete = notes.find((n) => n.id === $event)"
      />
    </div>

    <AlertModal
      :model-value="!!pendingDelete"
      :title="$t('notes.deleteTitle')"
      :message="$t('notes.deleteMessage', { title: pendingDelete?.title || '' })"
      :confirm-text="$t('common.delete')"
      :cancel-text="$t('common.cancel')"
      tone="danger"
      @confirm="confirmDelete"
      @cancel="pendingDelete = null"
      @update:model-value="!$event && (pendingDelete = null)"
    />
  </div>
</template>
