// Busy / error / saved bookkeeping for a single form action.
//
// Every settings card owns one of these, so a failure in one card shows its own
// message and never blanks the rest of the page.
import { onBeforeUnmount, reactive } from 'vue'
import i18n from '@/i18n'

const SAVED_MS = 2500

export function useTask() {
  const state = reactive({ busy: false, error: '', saved: false })
  let timer = null

  /** Run `fn`, recording the outcome. Returns true only when it succeeded. */
  async function run(fn) {
    state.busy = true
    state.error = ''
    state.saved = false
    try {
      await fn()
      state.saved = true
      clearTimeout(timer)
      timer = setTimeout(() => {
        state.saved = false
      }, SAVED_MS)
      return true
    } catch (e) {
      const data = e?.response?.data
      // Django replies with {detail} and sometimes {errors: {field: [...]}}.
      state.error =
        [data?.detail, ...Object.values(data?.errors || {}).flat()].filter(Boolean).join(' ') ||
        e?.message ||
        i18n.global.t('errors.generic')
      return false
    } finally {
      state.busy = false
    }
  }

  onBeforeUnmount(() => clearTimeout(timer))
  return { state, run }
}
