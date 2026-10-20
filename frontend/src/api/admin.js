// Admin panel API (/api/admin/*). Every call needs a staff role; most also need
// the panel unlocked on this device (see composables/useAdmin).
import http from '@/api/http'

const get = (url, params) => http.get(`/admin/${url}`, { params }).then((r) => r.data)
const post = (url, data) => http.post(`/admin/${url}`, data).then((r) => r.data)
const patch = (url, data) => http.patch(`/admin/${url}`, data).then((r) => r.data)
const del = (url, data) => http.delete(`/admin/${url}`, { data }).then((r) => r.data)

// File downloads. An error still arrives as a Blob, so read the JSON inside it
// back out: useAdmin().act needs its `code` to ask for a confirmation.
async function file(url) {
  try {
    const r = await http.get(`/admin/${url}`, { responseType: 'blob' })
    return r.data
  } catch (e) {
    const data = e?.response?.data
    if (data instanceof Blob && data.type.includes('json')) {
      try {
        e.response.data = JSON.parse(await data.text())
      } catch {
        /* leave the Blob as it is */
      }
    }
    throw e
  }
}

export const adminApi = {
  me: () => get('me'),
  unlock: (password, code) => post('unlock', { password, code }),
  lock: () => post('lock'),
  totpSetup: (password) => post('totp/setup', { password }),
  totpEnable: (code) => post('totp/enable', { code }),

  overview: () => get('overview'),
  system: () => get('system'),
  startups: (params) => get('startups', params),
  startup: (id) => get(`startups/${id}`),

  users: (params) => get('users', params),
  user: (id) => get(`users/${id}`),
  setStatus: (id, active, reason) => post(`users/${id}/status`, { active, reason }),
  revokeSessions: (id) => post(`users/${id}/sessions/revoke`),
  resetLink: (id) => post(`users/${id}/reset-link`),
  setQuota: (id, data) => post(`users/${id}/quota`, data),
  addCoins: (id, delta, reason) => post(`users/${id}/coins`, { delta, reason }),
  setRole: (id, role) => post(`users/${id}/role`, { role }),
  resetTotp: (id) => post(`users/${id}/totp-reset`),
  deleteUser: (id, confirm) => del(`users/${id}`, { confirm }),
  exportUser: (id) => file(`users/${id}/export`),
  exportUsersCsv: () => file('users.csv'),
  staff: () => get('staff'),

  content: () => get('content'),
  // The lesson text in one language, as every learner sees it: { lang, html, title }.
  saveLessonBody: (id, data) => post(`content/lessons/${id}/body`, data),
  updateUnit: (id, data) => patch(`content/units/${id}`, data),
  updateLesson: (id, data) => patch(`content/lessons/${id}`, data),
  importContent: (document, dryRun) => http.post('/admin/content/import', { document, dry_run: dryRun }).then((r) => r.data),

  reports: (params) => get('moderation/reports', params),
  resolveReport: (id, data) => post(`moderation/reports/${id}`, data),
  posts: (params) => get('moderation/posts', params),
  setPostHidden: (id, hidden, reason) => post(`moderation/posts/${id}`, { hidden, reason }),

  ai: (days) => get('ai', { days }),

  announcements: () => get('announcements'),
  createAnnouncement: (data) => post('announcements', data),
  updateAnnouncement: (id, data) => patch(`announcements/${id}`, data),
  deleteAnnouncement: (id) => del(`announcements/${id}`),

  settings: () => get('settings'),
  updateSettings: (data) => patch('settings', data),
  audit: (params) => get('audit', params),
  security: (params) => get('security', params),
  bans: (params) => get('security/bans', params),
  liftBan: (id) => post(`security/bans/${id}/lift`),
}

/** Save a Blob as a file. */
export function download(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
