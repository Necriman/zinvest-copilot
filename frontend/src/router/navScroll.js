/**
 * Where the window should be once a route change finishes.
 *
 * Two jobs, both forced by the same thing: the view transitions run out-in, so
 * at the moment the router wants to scroll, the page being *left* is still the
 * only one on screen and the page being opened has not been built yet. Scrolling
 * then moves the wrong page, in full view of whoever is watching.
 *
 *   · **The return note** — `/learn/:lessonId` sits outside the dashboard shell,
 *     so its Back button has to name a destination itself. Always naming the
 *     study map is wrong for anyone who arrived from the lessons catalogue, and
 *     dropping them at the top of a list they had scrolled halfway down means
 *     the page lurches once the data lands. So we remember both halves — the
 *     route they left and the offset they left it at — and the dashboard shell
 *     replays it as it mounts.
 *
 *   · **The pending scroll** — every ordinary navigation starts at the top, but
 *     applying that straight away yanks the outgoing page up before it has
 *     finished fading out. The position is parked here instead and flushed by
 *     the transition itself, in the gap after the old view has gone and before
 *     the new one has been painted.
 *
 * One slot each, rather than a map: only the most recent navigation is
 * interesting, and a map would quietly replay stale offsets on pages the learner
 * later reached some other way.
 */
let slot = null

/** Called as a full-screen view opens, while the old page is still on screen. */
export function rememberReturn(fullPath) {
  slot = { fullPath, top: Math.round(window.scrollY) }
}

/** The route a full-screen view should send its Back button to, or null. */
export function returnPath() {
  return slot?.fullPath ?? null
}

/**
 * Non-consuming — for views that need to know they are being restored and so
 * should skip whatever scrolling they normally do on arrival. Read it during
 * setup: `scrollBehavior` consumes the slot a tick later.
 */
export function isReturning(fullPath) {
  return !!slot && slot.fullPath === fullPath
}

/** Consuming — whoever restores the offset takes the note as it does so. */
export function takeReturn(fullPath) {
  if (!isReturning(fullPath)) return null
  const found = slot
  slot = null
  return found
}

/**
 * Forget the note when a navigation lands anywhere other than the page it points
 * at — a lesson bounced to sign-in by an expired session being the case that
 * actually reaches this. A note left lying around would suppress the
 * scroll-to-top on some later, ordinary visit to that same page.
 */
export function clearReturn() {
  slot = null
}

// --- the pending scroll ------------------------------------------------------

let pending = null

/** Park a position for the incoming transition to apply. */
export function deferScroll(position) {
  pending = position
}

/** Drop anything parked — a new navigation makes the last one's position stale. */
export function clearPendingScroll() {
  pending = null
}

/**
 * Apply the parked position. Called from the transition's before-enter hook: the
 * outgoing view has been removed and the incoming one has not been painted, so
 * the move never shows.
 */
export function flushPendingScroll() {
  if (!pending) return
  const { top = 0, left = 0 } = pending
  pending = null
  window.scrollTo(left, top)
}
