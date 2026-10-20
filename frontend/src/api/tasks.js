// Today's tasks — user-authored to-dos shown in the dashboard rail.
// The list is scoped server-side to "open + completed today".
import http from '@/api/http'

export function listTasks() {
  return http.get('/learning/tasks').then((r) => r.data.tasks)
}

export function createTask(title) {
  return http.post('/learning/tasks', { title }).then((r) => r.data)
}

export function updateTask(id, payload) {
  return http.patch(`/learning/tasks/${id}`, payload).then((r) => r.data)
}

export function deleteTask(id) {
  return http.delete(`/learning/tasks/${id}`).then((r) => r.data)
}
