// Zinvest AI — advisor (deep reasoning), quota status, and the learner context
// the AI screen opens with.
import http from '@/api/http'
import i18n from '@/i18n'

// The answer comes in the interface language, whatever language the question
// or the quoted text is written in.
export function askAdvisor(question, context = {}) {
  return http.post('/ai/advisor', { question, context, lang: i18n.global.locale.value }).then((r) => r.data)
}

export function getAIQuota() {
  return http.get('/ai/quota').then((r) => r.data)
}

/** What the learner is on and the last question they got wrong. No model call. */
export function getAIContext(lessonId) {
  const params = { lang: i18n.global.locale.value }
  if (lessonId) params.lesson = lessonId
  return http.get('/ai/context', { params }).then((r) => r.data)
}
