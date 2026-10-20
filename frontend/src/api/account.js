// Account settings: profile, avatar, credentials, appearance preferences.
// Every one of these returns the refreshed user object (except the password
// change, which returns how many other sessions were cut loose).
import http from '@/api/http'

export function updateProfile(payload) {
  return http.patch('/auth/me', payload).then((r) => r.data)
}

export function uploadAvatar(file) {
  const form = new FormData()
  form.append('avatar', file)
  // http.js strips the JSON Content-Type default for FormData so the browser
  // can set multipart/form-data with its boundary.
  return http.post('/auth/me/avatar', form).then((r) => r.data)
}

export function removeAvatar() {
  return http.delete('/auth/me/avatar').then((r) => r.data)
}

export function changePassword(currentPassword, newPassword) {
  return http
    .post('/auth/me/password', { current_password: currentPassword, new_password: newPassword })
    .then((r) => r.data)
}

// Nothing changes yet: the server mails a link to the new address, and the
// account moves there once it is opened (the answer carries `pending_email`).
export function changeEmail(password, newEmail, lang) {
  return http.post('/auth/me/email', { password, new_email: newEmail, lang }).then((r) => r.data)
}

// --- privacy ---------------------------------------------------------------
export function listSessions() {
  return http.get('/auth/sessions').then((r) => r.data.sessions)
}

export function revokeSession(familyId) {
  return http.delete(`/auth/sessions/${familyId}`).then((r) => r.data)
}

export function revokeOtherSessions() {
  return http.post('/auth/sessions/revoke-others', {}).then((r) => r.data)
}

// { password } for an account with one; { confirm: email } for a Google-only account.
export function deleteAccount(proof) {
  return http.delete('/auth/me/delete', { data: proof }).then((r) => r.data)
}

/**
 * "Download my data": fetches the JSON file with the bearer token (a plain link
 * could not send it) and hands it to the browser as a download.
 */
export async function downloadMyData() {
  let response
  try {
    response = await http.get('/auth/me/export', { responseType: 'blob' })
  } catch (err) {
    // An error body arrives as a Blob too; turn it back into JSON so the usual
    // `detail` message reaches the screen.
    const data = err.response?.data
    if (data instanceof Blob) {
      try {
        err.response.data = JSON.parse(await data.text())
      } catch {
        /* not JSON: leave it */
      }
    }
    throw err
  }
  const name = /filename="([^"]+)"/.exec(response.headers['content-disposition'] || '')?.[1] || 'zinvest-my-data.json'
  const url = URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

// --- password reset --------------------------------------------------------
/** Set a new password with a one-time link made by the team (no session needed). */
export function resetPassword(token, newPassword) {
  return http.post('/auth/password-reset', { token, new_password: newPassword }).then((r) => r.data)
}

/** Ask for a password link by email. The answer never says whether it exists. */
export function forgotPassword(email, lang) {
  return http.post('/auth/forgot-password', { email, lang }).then((r) => r.data)
}

/** Confirm an address from the mailed link (no session needed). */
export function verifyEmail(token, lang) {
  return http.post('/auth/verify-email', { token, lang }).then((r) => r.data)
}

export function resendVerification(lang) {
  return http.post('/auth/verify-email/resend', { lang }).then((r) => r.data)
}
