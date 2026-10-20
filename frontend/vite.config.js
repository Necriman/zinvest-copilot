import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// Serve the dev server over HTTPS with the same locally-trusted cert nginx uses
// for zinvest.loc, when it's present. The backend redirects HTTP→HTTPS and sets a
// `Secure` refresh cookie, which a plain-http origin (http://zinvest.loc:5173)
// can't store — so the SPA has to run on https too. Falls back to http on a
// machine without the cert (e.g. CI), where the plain-SQLite backend is fine.
const certPath = fileURLToPath(new URL('../deploy/nginx/certs/zinvest.loc.pem', import.meta.url))
const keyPath = fileURLToPath(new URL('../deploy/nginx/certs/zinvest.loc-key.pem', import.meta.url))
const https =
  !process.env.ZINVEST_HTTP && existsSync(certPath) && existsSync(keyPath)
    ? { cert: readFileSync(certPath), key: readFileSync(keyPath) }
    : undefined

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue({
      // MathLive ships <math-field> as a native custom element; tell the Vue
      // compiler to leave it alone instead of trying to resolve a component.
      template: { compilerOptions: { isCustomElement: (tag) => tag === 'math-field' } },
    }),
    tailwindcss(),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    https,

    allowedHosts: ['zinvest.loc'],
    // Same-origin illusion in dev so the SameSite=Strict refresh cookie works
    // without CORS: the SPA and /api are served from the same Vite origin. The
    // target MUST be https — http://zinvest.loc 301-redirects to https, and the
    // browser follows that cross-origin redirect (turning the refresh POST into a
    // GET), which fails CORS and returns 405. `secure: false` skips cert
    // verification for this known local host so a cert regen can't break dev.
    proxy: {
      '/api': { target: process.env.ZINVEST_API_TARGET || (https ? 'https://zinvest.loc' : 'http://127.0.0.1:8000'), changeOrigin: true, secure: false },
      // Uploaded avatars. Django serves these only while DEBUG is on; in
      // production Nginx maps /media/ straight to the volume.
      '/media': { target: process.env.ZINVEST_API_TARGET || (https ? 'https://zinvest.loc' : 'http://127.0.0.1:8000'), changeOrigin: true, secure: false },
    },
  },
})
