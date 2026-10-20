// Shared learning-stats source. The dashboard mounts three consumers at once
// (DashboardTopBar, RightRail, Dashboard); a module-level singleton + in-flight
// dedupe collapses their simultaneous GET /learning/stats into ONE request,
// while remounting on a later navigation still triggers a fresh fetch.
import { ref, shallowRef } from 'vue'
import i18n from '@/i18n'

import { getStats } from '@/api/stats'

const data = shallowRef(null)
const loading = ref(false)
const error = ref(null)
let inFlight = null

function fetchOnce() {
  if (inFlight) return inFlight // concurrent callers share the same request
  loading.value = true
  error.value = null
  inFlight = getStats()
    .then((d) => {
      data.value = d
      return d
    })
    .catch((e) => {
      error.value = e?.response?.data?.detail || e?.message || i18n.global.t('errors.generic')
      throw e
    })
    .finally(() => {
      loading.value = false
      inFlight = null
    })
  return inFlight
}

export function useSharedStats() {
  fetchOnce().catch(() => {})
  return {
    data,
    loading,
    error,
    reload: () => fetchOnce().catch(() => {}),
  }
}
