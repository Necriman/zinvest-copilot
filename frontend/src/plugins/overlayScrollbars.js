// Overlay-scrollbar system (OverlayScrollbars).
//
// One themed, auto-hiding overlay scrollbar used EVERYWHERE:
//   • the page (see initBodyOverlayScrollbars, called from main.js)
//   • any scroll container, via the global `v-os` directive:
//         <div class="overflow-y-auto" v-os> … </div>
//
// Overlay = it paints on top of the content, so it reserves no space (no layout
// jitter, no permanent gutter) and fades out when idle. New components just add
// `v-os` to their scroll container to get the identical scrollbar for free.
import { OverlayScrollbars } from 'overlayscrollbars'
import 'overlayscrollbars/styles/overlayscrollbars.css'

// The single source of truth for how our scrollbars look/behave. The visual
// theme (os-theme-zinvest) lives in style.scss so it can react to dark mode.
export const OS_OPTIONS = {
  scrollbars: { theme: 'os-theme-zinvest', autoHide: 'scroll', autoHideDelay: 700 },
}

// Page (document) scroll. Body-mode leaves position:fixed chrome and Teleported
// modals intact; cancel.nativeScrollbarsOverlaid:false → use it on every platform.
export function initBodyOverlayScrollbars() {
  return OverlayScrollbars(
    { target: document.body, cancel: { nativeScrollbarsOverlaid: false } },
    OS_OPTIONS,
  )
}

// The element that actually scrolls for a `v-os` host: the OS viewport if OS is
// active, otherwise the host itself. Use it when you must scroll programmatically
// (e.g. scroll-to-bottom), since the host element is no longer the scroller.
export function osScrollElement(el) {
  return el?.__osInstance?.elements?.().viewport || el || null
}

// Merge per-use overrides (v-os="{ scrollbars: { autoHide: 'leave' } }") over the
// shared defaults, keeping the nested `scrollbars` object intact.
function mergeOptions(override) {
  if (!override || typeof override !== 'object') return OS_OPTIONS
  return {
    ...OS_OPTIONS,
    ...override,
    scrollbars: { ...OS_OPTIONS.scrollbars, ...(override.scrollbars || {}) },
  }
}

export const OverlayScrollbarsPlugin = {
  install(app) {
    app.directive('os', {
      mounted(el, binding) {
        el.__osInstance = OverlayScrollbars(el, mergeOptions(binding.value))
      },
      beforeUnmount(el) {
        el.__osInstance?.destroy?.()
        el.__osInstance = null
      },
    })
  },
}
