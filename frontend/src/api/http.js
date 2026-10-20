// Axios instance + interceptors — the client-side heart of the hybrid-token flow.
//
//   * Request interceptor attaches the in-memory access token as a Bearer header.
//   * Response interceptor turns a 401 into a SINGLE silent refresh, parking any
//     concurrent 401s behind one in-flight refresh (single-flight mutex) and
//     replaying them with the new token. Hard guards prevent infinite loops.
//
// The access token is read from Pinia (memory) at call-time and NEVER persisted.
import axios from 'axios'

import i18n from '@/i18n'
import { loadingBar } from '@/composables/useLoadingBar'
import router from '@/router'
import { useAuthStore } from '@/store/auth'
import { getDeviceId } from '@/api/device'

// Answers the server marks with a `code` get their message in the interface
// language, so every screen that shows `detail` shows it translated.
const LOCALIZED_CODES = new Set(['rate_limited', 'ip_banned', 'account_blocked', 'posting_paused', 'ai_paused', 'registration_closed'])

function localize(error) {
  const data = error.response?.data
  if (data && typeof data === 'object' && LOCALIZED_CODES.has(data.code)) {
    data.detail = i18n.global.t(`admin.errors.${data.code}`)
  }
}

const http = axios.create({
  baseURL: '/api',
  withCredentials: true, // REQUIRED so the HttpOnly refresh cookie is sent to /api/auth/refresh
  headers: { 'Content-Type': 'application/json' },
})

// ---- Request interceptor -------------------------------------------------
http.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`
  }
  config.headers['X-Device-Id'] = getDeviceId()
  // The switcher's language, not the browser's: the course, the Drills and
  // the server's messages come back in it (an explicit ?lang= still wins).
  config.headers['Accept-Language'] = i18n.global.locale.value

  // File uploads: drop the instance's JSON default so the browser sets
  // multipart/form-data *with its boundary*. Without the boundary the server
  // can't parse the parts and sees no files at all.
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    if (typeof config.headers.delete === 'function') config.headers.delete('Content-Type')
    else delete config.headers['Content-Type']
  }
  return config
})

// ---- Single-flight refresh state -----------------------------------------
let isRefreshing = false
let failedQueue = [] // [{ resolve, reject }] — requests parked during a refresh

function processQueue(error, token = null) {
  failedQueue.forEach(({ resolve, reject }) => (error ? reject(error) : resolve(token)))
  failedQueue = []
}

// ---- Response interceptor ------------------------------------------------
http.interceptors.response.use(
  (response) => response,
  (error) => {
    const originalRequest = error.config
    const status = error.response?.status
    const url = originalRequest?.url || ''

    // 1. Only 401s are our concern.
    if (status !== 401) {
      localize(error)
      return Promise.reject(error)
    }

    // 2. Never attempt refresh for the auth endpoints themselves — a 401 from
    //    /refresh means the session is truly dead; from /login means bad creds.
    //    This is the primary infinite-loop guard.
    if (url.includes('/auth/refresh') || url.includes('/auth/login') || url.includes('/auth/code/')) {
      return Promise.reject(error)
    }

    // 3. Each request is retried at most once.
    if (originalRequest._retry) return Promise.reject(error)

    // 4. A refresh is already in flight -> park this request.
    if (isRefreshing) {
      return new Promise((resolve, reject) => failedQueue.push({ resolve, reject })).then((token) => {
        originalRequest._retry = true
        originalRequest.headers.Authorization = `Bearer ${token}`
        return http(originalRequest)
      })
    }

    // 5. We are the first 401 -> own the single refresh.
    originalRequest._retry = true
    isRefreshing = true
    const auth = useAuthStore()

    return new Promise((resolve, reject) => {
      auth
        .refresh()
        .then((newToken) => {
          processQueue(null, newToken)
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          resolve(http(originalRequest))
        })
        .catch((refreshErr) => {
          processQueue(refreshErr, null)
          // Only a refused refresh ends the session. A rate limit (429), a
          // server hiccup or no network leaves it alone: the next request
          // tries again instead of sending the person to the sign-in page.
          const refused = [400, 401, 403].includes(refreshErr.response?.status)
          if (refused) {
            auth.clearSession()
            router.push({ name: 'login', query: { session: 'expired' } })
          } else {
            localize(refreshErr)
          }
          reject(refreshErr)
        })
        .finally(() => {
          isRefreshing = false
        })
    })
  },
)

// The top loading bar counts every request until it settles. Registered after
// the refresh interceptor, so a request replayed after a refresh is counted as
// its own request and the original settles once the replay does.
http.interceptors.request.use((config) => {
  loadingBar.requestStart()
  return config
})
http.interceptors.response.use(
  (response) => {
    loadingBar.requestDone()
    return response
  },
  (error) => {
    loadingBar.requestDone()
    return Promise.reject(error)
  },
)

export default http
