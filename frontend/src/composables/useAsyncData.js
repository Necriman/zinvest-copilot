// Generic async-data wrapper: { data, loading, error, reload }. The single place
// loading/error/empty handling lives so every widget renders gracefully while the
// backend is stubbed or returns zeros.
import { ref, shallowRef } from 'vue'
import i18n from '@/i18n'

export function useAsyncData(fetcher, { immediate = true, initial = null } = {}) {
  const data = shallowRef(initial)
  const loading = ref(false)
  const error = ref(null)

  async function reload(...args) {
    loading.value = true
    error.value = null
    try {
      data.value = await fetcher(...args)
      return data.value
    } catch (e) {
      error.value = e?.response?.data?.detail || e?.message || i18n.global.t('errors.generic')
      throw e
    } finally {
      loading.value = false
    }
  }

  if (immediate) reload().catch(() => {})

  return { data, loading, error, reload }
}
