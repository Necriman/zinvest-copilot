// Learning stats (coins, streak, weekly calendar, goal, tasks).
import http from '@/api/http'

export function getStats() {
  return http.get('/learning/stats').then((r) => r.data)
}

export function updateGoal(payload) {
  return http.patch('/learning/stats/goal', payload).then((r) => r.data)
}

/** The next node on the learner's study map: { kind: 'lesson' | 'test' | 'done', id, title, unit_title }. */
export function getNextStep() {
  return http.get('/learning/next-step').then((r) => r.data)
}

/** Today's deck: { cards: [{ key, done, minutes, ... }], done, total, minutes_left }. */
export function getTodayPlan() {
  return http.get('/learning/today').then((r) => r.data)
}
