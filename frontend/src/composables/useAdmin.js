/**
 * Admin panel state shared by the layout and every admin page: who I am on the
 * team, what I may do, and whether the panel is unlocked on this device.
 *
 *   const admin = useAdmin()
 *   admin.can('users.manage')
 *   await admin.act(() => adminApi.setStatus(id, false, reason))
 *
 * `act` runs a change; if the server says a fresh confirmation is needed, it
 * opens the confirm dialog and, once confirmed, runs the change again.
 */
import { computed, reactive } from 'vue'

import { adminApi } from '@/api/admin'

const state = reactive({
  me: null,
  loading: false,
  error: '',
  prompt: null, // { reason: 'unlock' | 'sudo', resolve } while the confirm dialog is open
})

async function load() {
  state.loading = true
  state.error = ''
  try {
    state.me = await adminApi.me()
  } catch (e) {
    state.me = null
    state.error = e?.response?.data?.code || 'error'
  } finally {
    state.loading = false
  }
  return state.me
}

function setMe(me) {
  state.me = me
}

const can = (perm) => !!state.me?.permissions?.includes(perm)

function askToConfirm(reason) {
  return new Promise((resolve) => {
    state.prompt = { reason, resolve }
  })
}

function closePrompt(ok) {
  const prompt = state.prompt
  state.prompt = null
  prompt?.resolve(ok)
}

const NEEDS_CONFIRM = new Set(['unlock_required', 'sudo_required'])

/** Run an admin change, asking to confirm first if the server wants it. */
async function act(fn) {
  try {
    return await fn()
  } catch (e) {
    const code = e?.response?.data?.code
    if (!NEEDS_CONFIRM.has(code)) throw e
    const ok = await askToConfirm(code === 'sudo_required' ? 'sudo' : 'unlock')
    if (!ok) throw Object.assign(new Error('cancelled'), { cancelled: true })
    return fn()
  }
}

/** Error text for a failed admin call (server detail, or a generic message). */
function errorText(e, t) {
  if (e?.cancelled) return ''
  const data = e?.response?.data
  if (data?.errors?.length) return `${data.detail} ${data.errors.slice(0, 3).join(' · ')}`
  return data?.detail || t('admin.common.error')
}

export function useAdmin() {
  return {
    state,
    me: computed(() => state.me),
    unlocked: computed(() => !!state.me?.unlocked),
    load,
    setMe,
    can,
    act,
    askToConfirm,
    closePrompt,
    errorText,
  }
}
