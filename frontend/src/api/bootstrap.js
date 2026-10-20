// Silent refresh on app load. On a cold start there is no in-memory access
// token, but there may be a valid HttpOnly refresh cookie from a prior session.
// We attempt one silent refresh BEFORE the first protected navigation is decided
// (the router guard awaits `authReady`).
import { useAuthStore } from '@/store/auth'

let markReady
export const authReady = new Promise((resolve) => {
  markReady = resolve
})

export async function bootstrapAuth() {
  const auth = useAuthStore()
  try {
    await auth.refresh() // sends the cookie; rejects (401) if there is no valid session
    await auth.fetchMe() // hydrate the user
  } catch {
    // A cold visitor with no session is the normal case, not an error.
    auth.clearSession()
  } finally {
    markReady() // unblock the router guard no matter what
  }
}
