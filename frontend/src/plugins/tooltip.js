/**
 * App-wide styled tooltips.
 *
 * Instead of wrapping every control in a component, this upgrades the native
 * `title` attribute: on hover/focus the title is moved to `data-tip` (so the
 * browser's own slow, unstyled bubble never appears) and rendered in a styled
 * one. Everything that already carries a title — the whole editor toolbar, icon
 * buttons, nav items — gets a proper tooltip for free, and new markup does too
 * just by adding `title`.
 *
 * Accessibility: when a title is the element's only accessible name, it is
 * copied to `aria-label` before being removed, so screen readers keep it.
 */
const SHOW_DELAY = 320
const HIDE_DELAY = 60
const GAP = 8 // px between the control and the bubble
const EDGE = 6 // min distance from the viewport edge

let bubble = null
let current = null
let showTimer = null
let hideTimer = null

function ensureBubble() {
  if (bubble) return bubble
  bubble = document.createElement('div')
  bubble.className = 'zx-tooltip'
  bubble.setAttribute('role', 'tooltip')
  document.body.appendChild(bubble)
  return bubble
}

/**
 * Read the tip text, migrating `title` → `data-tip` on the way. Re-reads every
 * time because Vue re-applies a bound :title whenever the label changes.
 */
function tipText(el) {
  const native = el.getAttribute('title')
  if (native) {
    el.dataset.tip = native
    el.removeAttribute('title')
    if (!el.getAttribute('aria-label') && !el.textContent.trim()) {
      el.setAttribute('aria-label', native)
    }
  }
  // Icon-only controls often carry only an aria-label; that is the tooltip too.
  return el.dataset.tip || el.getAttribute('aria-label') || ''
}

function position(target) {
  const t = target.getBoundingClientRect()
  const b = bubble.getBoundingClientRect()

  // Prefer below; flip above when there isn't room.
  let top = t.bottom + GAP
  if (top + b.height > window.innerHeight - EDGE) top = t.top - b.height - GAP
  top = Math.max(EDGE, top)

  // Centre on the target, then clamp inside the viewport.
  let left = t.left + t.width / 2 - b.width / 2
  left = Math.max(EDGE, Math.min(left, window.innerWidth - b.width - EDGE))

  bubble.style.transform = `translate3d(${Math.round(left)}px, ${Math.round(top)}px, 0)`
}

function show(target) {
  const text = tipText(target)
  if (!text) return hide()
  ensureBubble()
  bubble.textContent = text
  // Measured while still transparent, so there's no flash at the wrong spot.
  position(target)
  bubble.classList.add('is-open')
  current = target
}

function hide() {
  clearTimeout(showTimer)
  clearTimeout(hideTimer)
  showTimer = hideTimer = null
  current = null
  bubble?.classList.remove('is-open')
}

const SELECTOR =
  '[title], [data-tip], button[aria-label], a[aria-label], [role="button"][aria-label]'

function candidate(node) {
  if (!(node instanceof Element)) return null
  const el = node.closest(SELECTOR)
  // Skip elements that opt out (e.g. a control with its own richer popover).
  if (!el || el.closest('[data-no-tip]')) return null
  // An aria-label only stands in for a tooltip on icon-only controls — a button
  // with visible text doesn't need one repeating the text back.
  if (!el.hasAttribute('title') && !el.dataset.tip && el.textContent.trim()) return null
  return el
}

function onOver(e) {
  const el = candidate(e.target)
  if (!el) {
    if (current) {
      clearTimeout(showTimer)
      hideTimer = setTimeout(hide, HIDE_DELAY)
    }
    return
  }
  if (el === current) {
    clearTimeout(hideTimer)
    return
  }
  clearTimeout(showTimer)
  clearTimeout(hideTimer)
  // Already showing one? Swap straight away rather than re-waiting.
  showTimer = setTimeout(() => show(el), current ? 0 : SHOW_DELAY)
}

function onFocus(e) {
  const el = candidate(e.target)
  // Keyboard focus shows immediately — there's no "hovering by accident".
  if (el) show(el)
  else hide()
}

function onKey(e) {
  if (e.key === 'Escape') hide()
}

/**
 * A tooltip already on screen would float away from its anchor, so drop it.
 * A *pending* one is left alone: it positions itself when it fires, and
 * cancelling it here would swallow tooltips whenever a hover scrolls the
 * control into view.
 */
function onScroll() {
  if (bubble?.classList.contains('is-open')) hide()
}

export function installTooltips() {
  document.addEventListener('pointerover', onOver, { passive: true })
  document.addEventListener('pointerdown', hide, { passive: true, capture: true })
  document.addEventListener('focusin', onFocus)
  document.addEventListener('focusout', hide)
  document.addEventListener('keydown', onKey)
  document.addEventListener('scroll', onScroll, { passive: true, capture: true })
  window.addEventListener('resize', hide, { passive: true })
  window.addEventListener('blur', hide)
}
