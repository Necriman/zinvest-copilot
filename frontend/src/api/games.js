// The practice trainer and "Up or down?". Both read their words from the
// server per language, so every call carries the switcher's language.
import http from './http'
import i18n from '@/i18n'

const lang = () => i18n.global.locale.value

/** One question (without its answer), the topics with their counts, and today's tally. */
export function nextPractice({ topic = '', after = '' } = {}) {
  const params = { lang: lang() }
  if (topic) params.topic = topic
  if (after) params.after = after
  return http.get('/learning/practice/next', { params }).then((r) => r.data)
}

/** Grade an answer, or — with `reveal` — just show the right one. */
export function answerPractice(id, { choice = null, reveal = false } = {}) {
  const body = reveal ? { id, reveal: true } : { id, choice }
  return http.post('/learning/practice/answer', body, { params: { lang: lang() } }).then((r) => r.data)
}

/** Today's round (if any is left), rounds left and the learner's record. */
export function getPredict() {
  return http.get('/learning/predict', { params: { lang: lang() } }).then((r) => r.data)
}

/** Make the call. 409: this round is already played; 429: no rounds left today. */
export function answerPredict(id, choice) {
  return http.post('/learning/predict/answer', { id, choice }, { params: { lang: lang() } }).then((r) => r.data)
}
