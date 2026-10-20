// What the sign-in, sign-up and password screens say when a request fails.
//
// They used to show the server's `detail` or fall back to "wrong email or
// password" / "check your details" — so when the API was simply not running,
// a correct password was reported as a wrong one, and people went looking for
// a password they had never forgotten. These helpers keep the three cases
// apart: no answer at all, a password the rules rejected, and a real refusal.
import i18n from '@/i18n'

const t = (key) => i18n.global.t(key)

// No answer from the API: the network is down, the dev proxy could not reach
// Django, or a gateway error in production. A 5xx that carries our own JSON
// `detail` is a real answer (sign-ups paused, for one) and is not "down".
export function serverDown(error) {
  const response = error?.response
  if (!response) return true
  const ours = response.data && typeof response.data === 'object' && response.data.detail
  return response.status >= 500 && !ours
}

// Django's validator codes, as the backend now sends them alongside the
// English sentences.
const PASSWORD_RULES = {
  password_too_short: 'auth.password.tooShort',
  password_too_common: 'auth.password.tooCommon',
  password_entirely_numeric: 'auth.password.numeric',
  password_too_similar: 'auth.password.similar',
}

// A password the server turned down, in the reader's language and naming the
// rule it broke. Empty when the failure was about something else.
export function passwordProblem(error) {
  const data = error?.response?.data
  if (!data?.errors?.length) return ''
  const named = (data.codes || []).map((code) => PASSWORD_RULES[code]).filter(Boolean)
  return named.length ? named.map(t).join(' ') : t('auth.password.rules')
}
