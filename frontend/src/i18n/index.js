// vue-i18n setup (Composition API, legacy:false). Initial locale is the persisted
// choice, else derived from navigator.language, else English. setLocale() is
// called by the header LanguageSwitcher and persists + updates <html lang>.
import { createI18n } from 'vue-i18n'

import en from './locales/en.json'
import ru from './locales/ru.json'
import uz from './locales/uz.json'
import { workspaceMessages } from './workspace'
import { mascotMessages } from './mascot'
import { adminMessages } from './admin'
import { editorMessages } from './editor'

const STORAGE_KEY = 'zinvest.locale'

export const AVAILABLE_LOCALES = [
  { code: 'en', label: 'EN', name: 'English' },
  { code: 'ru', label: 'RU', name: 'Русский' },
  { code: 'uz', label: 'UZ', name: "O‘zbekcha" },
]

function initialLocale() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved && AVAILABLE_LOCALES.some((l) => l.code === saved)) return saved
  const lang = (navigator.language || 'en').toLowerCase()
  if (lang.startsWith('ru')) return 'ru'
  if (lang.startsWith('uz')) return 'uz'
  return 'en'
}

const locale = initialLocale()
if (typeof document !== 'undefined') document.documentElement.lang = locale

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale,
  fallbackLocale: 'en',
  messages: {
    en: { ...en, ...workspaceMessages(0), ...mascotMessages(0), ...adminMessages(0), ...editorMessages(0) },
    ru: { ...ru, ...workspaceMessages(1), ...mascotMessages(1), ...adminMessages(1), ...editorMessages(1) },
    uz: { ...uz, ...workspaceMessages(2), ...mascotMessages(2), ...adminMessages(2), ...editorMessages(2) },
  },
})

export function setLocale(code) {
  i18n.global.locale.value = code
  localStorage.setItem(STORAGE_KEY, code)
  document.documentElement.lang = code
}

export default i18n
