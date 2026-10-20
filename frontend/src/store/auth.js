// Pinia auth store. The access token lives here in memory ONLY — never in
// localStorage, sessionStorage, cookies, or the URL. On a full reload it is gone
// and rebuilt from the HttpOnly refresh cookie via the silent refresh.
import { defineStore } from 'pinia'
import axios from 'axios'

import http from '@/api/http'
import { getDeviceId } from '@/api/device'
import i18n from '@/i18n'
import { useTheme } from '@/composables/useTheme'
import { clearViewCache } from '@/utils/viewCache'

// Bare client for the refresh handshake ONLY — no interceptors, so a refresh
// 401 can never re-enter the response interceptor and loop. withCredentials
// sends the HttpOnly refresh cookie (path-scoped to /api/auth/refresh).
const bareClient = axios.create({ baseURL: '/api', withCredentials: true })

// Cross-tab guard (defense-in-depth for the server-side grace window): the Web
// Locks API serializes refreshes across browser tabs so two tabs don't fire a
// refresh with the same cookie at once. Falls back to running directly where
// navigator.locks is unavailable.
function withRefreshLock(fn) {
  if (navigator.locks?.request) {
    return navigator.locks.request('auth-refresh', fn)
  }
  return fn()
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: null, // in-memory ONLY
    user: null, // { id, email, first_name, last_name }
    isAuthenticated: false,
  }),

  actions: {
    setAccessToken(token) {
      this.accessToken = token
      this.isAuthenticated = !!token
    },

    clearSession() {
      this.accessToken = null
      this.user = null
      this.isAuthenticated = false
      clearViewCache() // no account may inherit another's cached lists
    },

    // Sign-in and sign-up both end with a code from the letter: these return
    // `{ code_required, challenge, email, resend_in }` and open no session;
    // verifyCode() with the challenge and the code does.
    async login(email, password) {
      const { data } = await http.post('/auth/login', {
        email,
        password,
        unique_device_id: getDeviceId(),
        lang: i18n.global.locale.value,
      })
      if (!data.code_required) await this.adoptSession(data)
      return data
    },

    async register(details) {
      const { data } = await http.post('/auth/register', {
        ...details,
        unique_device_id: getDeviceId(),
        lang: i18n.global.locale.value,
      })
      return data
    },

    async verifyCode(challenge, code) {
      const { data } = await http.post('/auth/code/verify', {
        challenge,
        code,
        unique_device_id: getDeviceId(),
      })
      await this.adoptSession(data)
      return data
    },

    async resendCode(challenge) {
      const { data } = await http.post('/auth/code/resend', { challenge, lang: i18n.global.locale.value })
      return data
    },

    async adoptSession(data) {
      this.setAccessToken(data.access_token)
      if (data.user) this.setUser(data.user)
      else await this.fetchMe()
    },

    async refresh() {
      return withRefreshLock(async () => {
        const { data } = await bareClient.post('/auth/refresh', {
          unique_device_id: getDeviceId(),
        })
        this.setAccessToken(data.access_token)
        return data.access_token
      })
    },

    async fetchMe() {
      const { data } = await http.get('/auth/me')
      this.setUser(data)
      return data
    },

    /** Adopt a fresh user object and re-apply the appearance it carries. */
    setUser(user) {
      this.user = user
      useTheme().syncFromUser(user)
    },

    async logout() {
      try {
        await http.post('/auth/logout', {})
      } catch {
        // Clear locally even if the network call fails.
      } finally {
        this.clearSession()
      }
    },
  },
})
