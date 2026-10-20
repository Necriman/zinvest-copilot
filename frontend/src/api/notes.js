// User notes — free-standing rich documents, same editor as lesson content.
// The list endpoint returns metadata + a plain-text excerpt only; `getNote`
// is what carries the HTML body.
import http from '@/api/http'

export function listNotes() {
  return http.get('/notes').then((r) => r.data.notes)
}

export function getNote(id) {
  return http.get(`/notes/${id}`).then((r) => r.data)
}

export function createNote(payload = {}) {
  return http.post('/notes', payload).then((r) => r.data)
}

export function updateNote(id, payload) {
  return http.patch(`/notes/${id}`, payload).then((r) => r.data)
}

export function deleteNote(id) {
  return http.delete(`/notes/${id}`).then((r) => r.data)
}
