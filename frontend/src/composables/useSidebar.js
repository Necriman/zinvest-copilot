/**
 * Dashboard sidebar state — shared across the layout, the top bar and the
 * sidebar itself (module-level refs, so every importer sees the same state).
 *
 * Three shapes, driven by viewport width:
 *  - width >= 1024 (desktop): docked, expanded by default. A toggle collapses it
 *    to a mini rail (icons only); the choice is remembered.
 *  - 850 <= width < 1024 (tablet): docked, defaults to the mini rail. Still
 *    toggleable to the full rail.
 *  - width < 850 (mobile): undocked. The rail lives in an off-canvas drawer the
 *    top bar's menu button opens.
 *
 * 850px is the docking cut-off the product asked for; 1024 is where the mini
 * rail stops being the sensible default. Neither maps to a Tailwind breakpoint,
 * so the split is measured here rather than expressed in classes.
 */
import { computed, ref } from 'vue'

const STORAGE_KEY = 'zx-sidebar-collapsed'
const DOCK_QUERY = '(min-width: 850px)'
const MINI_DEFAULT_MAX = 1024 // below this, docked defaults to the mini rail

export const SIDEBAR_FULL = 256 // w-64
export const SIDEBAR_MINI = 76

const docked = ref(true)
const collapsed = ref(false)
const drawerOpen = ref(false)

let initialized = false

function readPref() {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === '1') return true
    if (v === '0') return false
  } catch {
    /* private mode / no storage — fall through to the width default */
  }
  return null
}

function applyViewport() {
  const wide = window.matchMedia(DOCK_QUERY).matches
  docked.value = wide
  if (wide) {
    drawerOpen.value = false
    const pref = readPref()
    // No explicit choice yet: mini on the tablet band, full on the desktop.
    collapsed.value = pref === null ? window.innerWidth < MINI_DEFAULT_MAX : pref
  }
}

function init() {
  if (initialized || typeof window === 'undefined') return
  initialized = true
  applyViewport()
  window.matchMedia(DOCK_QUERY).addEventListener('change', applyViewport)
  window.addEventListener('resize', applyViewport)
}

export function useSidebar() {
  init()

  const width = computed(() => (collapsed.value ? SIDEBAR_MINI : SIDEBAR_FULL))
  // The mini rail only exists while docked — the drawer always shows full labels.
  const mini = computed(() => docked.value && collapsed.value)

  function toggleCollapsed() {
    collapsed.value = !collapsed.value
    try {
      localStorage.setItem(STORAGE_KEY, collapsed.value ? '1' : '0')
    } catch {
      /* ignore */
    }
  }

  const openDrawer = () => (drawerOpen.value = true)
  const closeDrawer = () => (drawerOpen.value = false)
  const toggleDrawer = () => (drawerOpen.value = !drawerOpen.value)

  return {
    docked,
    collapsed,
    drawerOpen,
    mini,
    width,
    toggleCollapsed,
    openDrawer,
    closeDrawer,
    toggleDrawer,
  }
}
