/**
 * Last-payload cache for the long list views.
 *
 * The lesson editor lives outside the dashboard shell, so coming back from one
 * remounts the list from scratch. Without the previous payload the page mounts
 * only a few hundred pixels tall, the restored scroll offset gets clamped to the
 * top, and everything lurches downward once the request finally lands. Holding
 * the last response means the list paints at its real height on the first frame
 * and the refresh happens underneath, invisibly.
 *
 * In-memory only, and dropped with the session (see the auth store) so one
 * account never sees another's data.
 */
const store = new Map()

export function readCache(key) {
  return store.get(key) ?? null
}

export function writeCache(key, value) {
  store.set(key, value)
}

export function clearViewCache() {
  store.clear()
}
