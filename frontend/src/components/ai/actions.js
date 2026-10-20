// The four things a learner actually asks a tutor for, and how each becomes a
// question. The question is sent as the learner's own message, visible in the
// thread — the AI is not being prompted behind their back — and the lesson or
// the mistake goes along as context so the answer is about them.
export const ACTIONS = [
  { key: 'explain', icon: 'sparkles' },
  { key: 'quiz', icon: 'target' },
  { key: 'mistake', icon: 'undo' },
  { key: 'example', icon: 'chart' },
]

/**
 * `{ text, context }` to send, `{ draft }` to put in the box for the learner to
 * finish, or null when the action has nothing to work with.
 */
export function buildAsk(key, ctx, t) {
  if (key === 'mistake') {
    const m = ctx?.mistake
    if (!m) return null
    return {
      text: t('aiHome.ask.mistake', { question: m.question, chosen: m.chosen, correct: m.correct }),
      context: { mode: 'mistake', where: m.where, explanation: m.explain },
    }
  }
  const topic = ctx?.learning?.title
  if (!topic) {
    // Without a lesson to anchor to, "explain" needs the learner's own words.
    if (key === 'explain') return { draft: t('aiHome.ask.explainAny') }
    return { text: t(`aiHome.ask.${key}Any`), context: { mode: key } }
  }
  return {
    text: t(`aiHome.ask.${key}`, { topic }),
    context: { mode: key, lesson: topic, unit: ctx.learning.unit_title },
  }
}
