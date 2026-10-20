import { createApp, watch } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { applyTitle } from './router/titles'
import i18n from './i18n'
import { bootstrapAuth } from './api/bootstrap'
import { useTheme } from './composables/useTheme'
import { OverlayScrollbarsPlugin, initBodyOverlayScrollbars } from './plugins/overlayScrollbars'
import { installTooltips } from './plugins/tooltip'
import './tailwind.css'
import './style.scss'

// Apply the persisted theme BEFORE mount so there is no flash of wrong colors.
useTheme().init()

const app = createApp(App)

app.use(createPinia()) // Pinia FIRST — stores must exist before bootstrap/guard run
app.use(router)
app.use(i18n)
app.use(OverlayScrollbarsPlugin) // registers the global `v-os` directive

// Kick off the silent refresh. Not awaited: the router guard awaits `authReady`,
// so the first protected navigation is gated on the refresh while the shell paints.
bootstrapAuth()

app.mount('#app')

// The tab title follows a language switch, not only navigation.
watch(i18n.global.locale, () => applyTitle(router.currentRoute.value))

// Styled tooltips for every `title` in the app (delegated — no per-component work).
installTooltips()

// Overlay scrollbar for the page (see plugins/overlayScrollbars.js for the shared
// config + the `v-os` directive that gives every other scroll container the same).
initBodyOverlayScrollbars()
