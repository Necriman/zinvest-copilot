/**
 * Browser tab titles, in the interface language. Every tab used to read just
 * "Zinvest". Most pages reuse their own sidebar label (nav.*); a page not
 * listed here keeps the plain brand name.
 */
import i18n from '@/i18n'

const KEYS = {
  login: 'nav.login',
  register: 'nav.register',
  dashboard: 'nav.today',
  studyPlan: 'nav.studyPlan',
  lessons: 'nav.lessons',
  notes: 'nav.notes',
  units: 'nav.units',
  drills: 'nav.drills',
  practice: 'nav.practice',
  zinvestAI: 'nav.zinvestAI',
  myStartup: 'nav.myStartup',
  cashFlow: 'nav.cashFlow',
  leaderboard: 'nav.leaderboard',
  plans: 'nav.plans',
  settings: 'nav.settings',
  notFound: 'notFound.title',
}

export function applyTitle(route) {
  const { t, te } = i18n.global
  if (route?.name === 'landing') {
    document.title = `Zinvest — ${t('titles.tagline')}`
    return
  }
  const key = KEYS[route?.name]
  document.title = key && te(key) ? `${t(key)} · Zinvest` : 'Zinvest'
}
