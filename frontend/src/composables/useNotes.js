// Shared notes state.
//
// The Notes page and the editor both read this, and an edit in the editor has
// to be reflected in the grid when you navigate back. A module-level singleton
// keeps them in sync without a Pinia store, matching useSharedStats.
import { ref, shallowRef } from 'vue'
import i18n from '@/i18n'

import { createNote, deleteNote, listNotes, updateNote } from '@/api/notes'

const LEGACY_KEY = 'zinvest.notes' // the old single-string localStorage drawer

const notes = shallowRef([])
const loading = ref(false)
const error = ref(null)
let loaded = false
let inFlight = null

function fail(e) {
  error.value = e?.response?.data?.detail || e?.message || i18n.global.t('errors.generic')
  throw e
}

async function refresh() {
  if (inFlight) return inFlight
  loading.value = true
  error.value = null
  inFlight = listNotes()
    .then((rows) => {
      notes.value = rows
      loaded = true
      return rows
    })
    .catch(fail)
    .finally(() => {
      loading.value = false
      inFlight = null
    })
  return inFlight
}

/**
 * One-time rescue of the pre-database drawer note so nobody loses what they
 * had typed. Runs only when the account has no notes yet, then clears the key.
 */
async function migrateLegacyNote() {
  const legacy = localStorage.getItem(LEGACY_KEY)
  if (!legacy || !legacy.trim() || notes.value.length) {
    if (legacy !== null && notes.value.length) localStorage.removeItem(LEGACY_KEY)
    return
  }
  const html = legacy
    .split(/\n{2,}/)
    .map((para) => `<p>${para.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]).replace(/\n/g, '<br>')}</p>`)
    .join('')
  await create({ title: i18n.global.t('misc.myNotes'), content: html })
  localStorage.removeItem(LEGACY_KEY)
}

async function ensureLoaded() {
  if (loaded) return notes.value
  const rows = await refresh()
  await migrateLegacyNote().catch(() => {})
  return rows
}

async function create(payload = {}) {
  const note = await createNote(payload).catch(fail)
  notes.value = [note, ...notes.value]
  return note
}

async function update(id, payload) {
  const note = await updateNote(id, payload).catch(fail)
  // Re-sort client-side the way the server does: pinned first, then most recent.
  notes.value = [note, ...notes.value.filter((n) => n.id !== id)].sort(
    (a, b) => Number(b.is_pinned) - Number(a.is_pinned) || b.updated_at.localeCompare(a.updated_at),
  )
  return note
}

async function remove(id) {
  await deleteNote(id).catch(fail)
  notes.value = notes.value.filter((n) => n.id !== id)
}

export function useNotes() {
  return { notes, loading, error, ensureLoaded, refresh, create, update, remove }
}
