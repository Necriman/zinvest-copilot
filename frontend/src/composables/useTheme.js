// Class-based light/dark theme + runtime brand recoloring. A module-level ref
// makes it a shared singleton, so every toggle stays in sync. init() runs in
// main.js BEFORE mount so the persisted theme + brand apply with no flash.
//
// The preference is light | dark | system; `resolvedTheme` is what actually
// ends up on the page. Both the theme and the brand colour are mirrored onto
// the account (see Settings) so they follow the user between devices — but the
// local copy is what boots the page, because waiting for /me would flash.
import { computed, ref } from 'vue'

const THEME_KEY = 'zinvest.theme'
const BRAND_KEY = 'zinvest.brand'

export const THEME_OPTIONS = ['light', 'dark', 'system']

// '' means "the theme's own colour": purple in light, blue in dark.
export const BRAND_PRESETS = [
  { key: 'violet', hex: '#6943cc' },
  { key: 'blue', hex: '#2563eb' },
  { key: 'emerald', hex: '#059669' },
  { key: 'amber', hex: '#d97706' },
  { key: 'rose', hex: '#e11d48' },
  { key: 'slate', hex: '#475569' },
]
export const DEFAULT_BRAND = BRAND_PRESETS[0].hex

const theme = ref('system') // the preference
const systemDark = ref(false) // what the OS currently reports
const brand = ref('') // '' = the stylesheet default

const resolvedTheme = computed(() =>
  theme.value === 'system' ? (systemDark.value ? 'dark' : 'light') : theme.value,
)

function apply() {
  document.documentElement.classList.toggle('dark', resolvedTheme.value === 'dark')
}

// The 50–900 ramp is derived from one hex so every brand-* utility re-tints at
// once (they resolve from these CSS variables — see tailwind.css).
const RAMP = [
  ['--brand-600', null],
  ['--brand-500', 'white 14%'],
  ['--brand-400', 'white 28%'],
  ['--brand-300', 'white 52%'],
  ['--brand-200', 'white 70%'],
  ['--brand-100', 'white 84%'],
  ['--brand-50', 'white 92%'],
  ['--brand-700', 'black 14%'],
  ['--brand-800', 'black 26%'],
  ['--brand-900', 'black 40%'],
]

function applyBrand(hex) {
  const s = document.documentElement.style
  for (const [prop, mix] of RAMP) {
    if (!hex) s.removeProperty(prop) // fall back to the stylesheet default
    else s.setProperty(prop, mix ? `color-mix(in srgb, ${hex}, ${mix})` : hex)
  }
}

function init() {
  const mql = window.matchMedia?.('(prefers-color-scheme: dark)')
  systemDark.value = !!mql?.matches
  mql?.addEventListener?.('change', (e) => {
    systemDark.value = e.matches
    if (theme.value === 'system') apply()
  })

  theme.value = localStorage.getItem(THEME_KEY) || 'system'
  apply()

  brand.value = localStorage.getItem(BRAND_KEY) || ''
  if (brand.value) applyBrand(brand.value)
}

function setTheme(value) {
  theme.value = THEME_OPTIONS.includes(value) ? value : 'system'
  localStorage.setItem(THEME_KEY, theme.value)
  apply()
}

/** Returns the preference it committed, so callers can mirror it to the account. */
function toggle() {
  // From "system", the toggle commits to the opposite of what's on screen.
  const next = resolvedTheme.value === 'dark' ? 'light' : 'dark'
  setTheme(next)
  return next
}

function setBrand(hex) {
  brand.value = hex || ''
  if (brand.value) localStorage.setItem(BRAND_KEY, brand.value)
  else localStorage.removeItem(BRAND_KEY)
  applyBrand(brand.value)
}

/**
 * Adopt whatever the account says, once /me resolves. Only touches what the
 * server actually holds, so a fresh device inherits the user's choices.
 */
function syncFromUser(user) {
  if (!user) return
  if (user.theme && user.theme !== theme.value) setTheme(user.theme)
  if ((user.brand_color || '') !== brand.value) setBrand(user.brand_color || '')
}

export function useTheme() {
  return { theme, resolvedTheme, brand, init, setTheme, toggle, setBrand, syncFromUser }
}
