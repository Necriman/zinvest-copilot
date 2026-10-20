// Sign-up assessment → personalised study plan.
// GET returns the questionnaire (quiz answers are stripped server-side) plus
// the learner's current state; POST grades it and rebuilds the plan.
import http from '@/api/http'

export function getOnboarding() {
  return http.get('/learning/onboarding').then((r) => r.data)
}

export function submitOnboarding(profile, quiz) {
  return http.post('/learning/onboarding', { profile, quiz }).then((r) => r.data)
}

export function regenerateStudyPlan() {
  return http.post('/learning/study-plan/regenerate', {}).then((r) => r.data)
}
