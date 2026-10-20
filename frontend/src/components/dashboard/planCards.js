// Where each card of today's deck leads, and how it looks.
export const CARD_ICON = {
  lesson: 'book',
  test: 'trophy',
  challenges: 'zap',
  ai: 'bot',
  startup: 'store',
}

export function cardRoute(card) {
  switch (card?.key) {
    case 'lesson':
      return { name: 'lesson', params: { lessonId: card.id } }
    case 'test':
      return { name: 'unitTest', params: { unitId: card.id } }
    case 'challenges':
      return { name: 'drills' }
    case 'ai':
      return { name: 'zinvestAI' }
    case 'startup':
      return { name: 'myStartup' }
    default:
      return { name: 'studyPlan' }
  }
}

/** Kicker and title for a card, already translated. */
export function cardText(card, t) {
  switch (card?.key) {
    case 'lesson':
      return { kicker: t('deck.lessonKicker'), title: card.done ? t('deck.lessonDone') : card.title }
    case 'test':
      return { kicker: t('deck.testKicker'), title: card.done ? t('deck.lessonDone') : card.title }
    case 'challenges':
      return { kicker: t('deck.challengesKicker'), title: t('deck.challengesTitle') }
    case 'ai':
      return { kicker: t('deck.aiKicker'), title: t('deck.aiTitle') }
    case 'startup':
      return { kicker: t('deck.startupKicker'), title: t('deck.startupTitle') }
    default:
      return { kicker: '', title: '' }
  }
}
