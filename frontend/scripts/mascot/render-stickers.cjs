// Captures the mascot stickers into public/mascot/*.webp.
//
//   1. npm run dev            (serves scripts/mascot/stickers.html)
//   2. node scripts/mascot/render-stickers.cjs [name,name]
//
// Needs Playwright and ffmpeg on the machine. Neither is a project dependency:
// set PLAYWRIGHT_MODULE to a Playwright install and FFMPEG to the binary if they
// are not on the default paths.
const path = require('node:path')
const fs = require('node:fs')
const os = require('node:os')
const { execFileSync } = require('node:child_process')

const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const FFMPEG = process.env.FFMPEG || 'ffmpeg'
const ORIGIN = process.env.DEV_ORIGIN || 'http://127.0.0.1:5173'
const OUT = path.resolve(__dirname, '../../public/mascot')
const SIZE = 384

;(async () => {
  const only = process.argv[2] ? `&only=${process.argv[2]}` : ''
  const browser = await chromium.launch({ headless: true, args: ['--enable-unsafe-swiftshader', '--use-angle=swiftshader'] , executablePath: process.env.CHROME || undefined })
  const page = await browser.newPage({ viewport: { width: 1600, height: 1200 }, deviceScaleFactor: 1 })
  page.on('pageerror', (e) => console.error('pageerror', e.message))
  page.on('console', (m) => { if (m.type() === 'error') console.error('console', m.text()) })
  await page.goto(`${ORIGIN}/scripts/mascot/stickers.html?capture${only}`)
  await page.waitForFunction(() => window.__done === true, null, { timeout: 180000 })
  fs.mkdirSync(OUT, { recursive: true })
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'zinvest-stickers-'))
  for (const name of await page.evaluate(() => window.__stickers)) {
    const png = path.join(tmp, `${name}.png`)
    await page.locator(`.sticker[data-name="${name}"]`).screenshot({ path: png, omitBackground: true })
    const webp = path.join(OUT, `${name}.webp`)
    execFileSync(FFMPEG, ['-y', '-loglevel', 'error', '-i', png, '-vf', `scale=${SIZE}:${SIZE}:flags=lanczos`, '-c:v', 'libwebp', '-quality', '86', '-pix_fmt', 'yuva420p', webp])
    console.log(name, fs.statSync(webp).size, 'bytes')
  }
  await browser.close()
})().catch((e) => { console.error(e); process.exit(1) })
