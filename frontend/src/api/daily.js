import http from './http'
import i18n from '@/i18n'

// The question bank is stored per language, so every call carries whichever
// language the switcher is on right now.
const lang = () => i18n.global.locale.value

export function getDaily() {
  return http.get('/learning/daily', { params: { lang: lang() } }).then((r) => r.data)
}

export function answerDaily(choice) {
  return http.post('/learning/daily/answer', { choice }, { params: { lang: lang() } }).then((r) => r.data)
}
