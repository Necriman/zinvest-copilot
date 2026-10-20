// A single lesson (meta + Canvas payload) and completion.
import http from '@/api/http'

export function getLesson(lessonId) {
  return http.get(`/learning/lessons/${lessonId}`).then((r) => r.data)
}

export function saveLessonContent(lessonId, content) {
  return http.post(`/learning/lessons/${lessonId}/save`, { content }).then((r) => r.data)
}

export function completeLesson(lessonId, payload = {}) {
  return http.post(`/learning/lessons/${lessonId}/complete`, payload).then((r) => r.data)
}
