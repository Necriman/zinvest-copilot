// Renders every mascot sticker from the live 3D bear, so the stills and the
// animated bear always match. Each entry: a pose (a static mood), optional
// props held in the paws, and an optional 2D decoration drawn over the render.
import * as THREE from 'three'

import { MOODS, createBear } from '/src/mascot/engine.js'
import { drawMark } from '/src/components/ui/brandMark.js'

const deg = Math.PI / 180
const NAVY = '#1e2a44', BLUE = '#2e6cf6', GOLD = '#d4a72c'

// ---------------------------------------------------------------------------
// Props
function canvasTexture(w, h, draw) {
  const c = document.createElement('canvas')
  c.width = w
  c.height = h
  draw(c.getContext('2d'), w, h)
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  t.anisotropy = 4
  return t
}

function coin() {
  const face = canvasTexture(512, 512, (g, w) => {
    const grad = g.createRadialGradient(w * 0.4, w * 0.35, w * 0.05, w / 2, w / 2, w * 0.5)
    grad.addColorStop(0, '#f6d774')
    grad.addColorStop(1, '#c9951f')
    g.fillStyle = grad
    g.fillRect(0, 0, w, w)
    g.strokeStyle = 'rgba(120,80,10,0.45)'
    g.lineWidth = 22
    g.beginPath(); g.arc(w / 2, w / 2, w * 0.39, 0, Math.PI * 2); g.stroke()
    g.fillStyle = '#9a6d10'
    g.font = `800 ${w * 0.46}px system-ui, sans-serif`
    g.textAlign = 'center'
    g.textBaseline = 'middle'
    g.fillText('$', w / 2, w * 0.53)
  })
  const gold = new THREE.MeshStandardMaterial({ color: GOLD, metalness: 0.35, roughness: 0.35 })
  const cap = new THREE.MeshStandardMaterial({ map: face, metalness: 0.2, roughness: 0.4 })
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(0.23, 0.23, 0.05, 64), [gold, cap, cap])
  mesh.rotation.x = Math.PI / 2
  return mesh
}

function slab(w, h, d, frontDraw, color = NAVY, sideColor) {
  const front = canvasTexture(512, Math.round((512 * h) / w), frontDraw)
  const body = new THREE.MeshStandardMaterial({ color, roughness: 0.55, metalness: 0.05 })
  const side = new THREE.MeshStandardMaterial({ color: sideColor || color, roughness: 0.7 })
  const face = new THREE.MeshStandardMaterial({ map: front, roughness: 0.45 })
  // BoxGeometry groups: +x, -x, +y, -y, +z, -z
  return new THREE.Mesh(new THREE.BoxGeometry(w, h, d), [side, side, side, side, face, body])
}

function tablet() {
  return slab(0.42, 0.54, 0.035, (g, w, h) => {
    g.fillStyle = NAVY
    g.fillRect(0, 0, w, h)
    g.fillStyle = '#243457'
    g.fillRect(w * 0.06, h * 0.05, w * 0.88, h * 0.9)
    drawMark(g, w / 2, h / 2, w * 0.46, '#e8eefc')
  })
}

function book() {
  const b = slab(0.4, 0.5, 0.08, (g, w, h) => {
    g.fillStyle = NAVY
    g.fillRect(0, 0, w, h)
    g.fillStyle = '#16203a'
    g.fillRect(0, 0, w * 0.08, h)
    drawMark(g, w * 0.54, h * 0.46, w * 0.42, '#e8eefc')
    g.fillStyle = 'rgba(232,238,252,0.55)'
    g.fillRect(w * 0.3, h * 0.78, w * 0.48, h * 0.03)
  }, NAVY, '#f3efe3')
  return b
}

function phone() {
  return slab(0.24, 0.44, 0.03, (g, w, h) => {
    g.fillStyle = '#10182c'
    g.fillRect(0, 0, w, h)
    const grad = g.createLinearGradient(0, 0, 0, h)
    grad.addColorStop(0, '#dfe8fb')
    grad.addColorStop(1, '#b9cdf7')
    g.fillStyle = grad
    g.fillRect(w * 0.08, h * 0.05, w * 0.84, h * 0.9)
    g.fillStyle = BLUE
    const bars = [0.35, 0.5, 0.42, 0.68, 0.8]
    bars.forEach((v, i) => g.fillRect(w * (0.17 + i * 0.14), h * (0.8 - v * 0.5), w * 0.09, h * v * 0.5))
    drawMark(g, w / 2, h * 0.2, w * 0.3, NAVY)
  })
}

// ---------------------------------------------------------------------------
// Decorations (SVG over the render), in the mascot sheet's accents
const star = (x, y, r, fill) => `<path d="M${x} ${y - r}L${x + r * 0.28} ${y - r * 0.28}L${x + r} ${y}L${x + r * 0.28} ${y + r * 0.28}L${x} ${y + r}L${x - r * 0.28} ${y + r * 0.28}L${x - r} ${y}L${x - r * 0.28} ${y - r * 0.28}Z" fill="${fill}"/>`
const DECOR = {
  sparkles: star(92, 150, 26, GOLD) + star(430, 110, 20, BLUE) + star(418, 250, 14, GOLD),
  question: `<text x="398" y="118" font-family="system-ui" font-weight="800" font-size="96" fill="${BLUE}">?</text>`,
  sleep: `<text x="360" y="120" font-family="system-ui" font-weight="800" font-size="58" fill="${BLUE}">z</text><text x="405" y="80" font-family="system-ui" font-weight="800" font-size="40" fill="${BLUE}">z</text>`,
  dots: `<circle cx="372" cy="106" r="11" fill="#9fb4d9"/><circle cx="404" cy="92" r="14" fill="#9fb4d9"/><circle cx="442" cy="74" r="18" fill="#9fb4d9"/>`,
  motion: `<path d="M418 170l30-22M430 205l36-10" stroke="${BLUE}" stroke-width="10" stroke-linecap="round"/>`,
  burst: `<path d="M256 250v-26M226 258l-16-18M286 258l16-18" stroke="${GOLD}" stroke-width="9" stroke-linecap="round"/>` + star(420, 120, 18, BLUE),
}

// ---------------------------------------------------------------------------
// Poses. Static moods: the sticker renders one frame.
const pose = (fn) => (t, p) => fn(p)
const both = (p, arm, fore) => { p.armR = arm.map((a) => a * deg); p.armL = [arm[0], -arm[1], -arm[2]].map((a) => a * deg); p.foreR = fore.map((a) => a * deg); p.foreL = [fore[0], -fore[1], -fore[2]].map((a) => a * deg) }
const holdBoth = (p) => both(p, [-62, -22, -30], [-22, -12, 0])

MOODS.s_idle = pose((p) => { p.armR[2] += 3 * deg; p.armL[2] -= 3 * deg })
MOODS.s_wave = pose((p) => { p.armR = [-15 * deg, 0, 58 * deg]; p.foreR = [0, 0, 56 * deg]; p.handR = [0, 0, 12 * deg]; p.head[2] = -6 * deg; p.brow = 0.5; p.mouth = 0.35; p.lean = -1.5 * deg })
MOODS.s_think = pose((p) => { p.head = [-6 * deg, 7 * deg, 8 * deg]; p.armL = [-95 * deg, 50 * deg, 10 * deg]; p.foreL = [-70 * deg, 20 * deg, 0]; p.brow = 0.6 })
MOODS.s_happy = pose((p) => { both(p, [-8, 0, 10], [0, 0, 30]); p.eyeHappy = 1; p.mouth = 0.6; p.brow = 0.5; p.head[2] = 4 * deg; p.hop = 0.03 })
MOODS.s_celebrate = pose((p) => { both(p, [-10, 0, 95], [0, 0, 20]); p.hop = 0.12; p.eyeHappy = 1; p.mouth = 0.85; p.brow = 0.8; p.arrowScale = 1.15; p.arrowBob = 0.04 })
MOODS.s_clap = pose((p) => { both(p, [-70, -32, -30], [0, -20, 0]); p.turn = 0.3; p.eyeHappy = 1; p.mouth = 0.65; p.brow = 0.5 })
MOODS.s_cheer = pose((p) => { p.armR = [-12 * deg, 0, 72 * deg]; p.foreR = [0, 0, 60 * deg]; p.head[2] = -4 * deg; p.mouth = 0.7; p.brow = 0.7 })
MOODS.s_confused = pose((p) => { both(p, [-30, 0, -18], [-55, 0, 25]); p.head = [3 * deg, 0, -13 * deg]; p.brow = 0.9; p.lean = 2 * deg })
MOODS.s_sleep = pose((p) => { p.head = [14 * deg, 0, -8 * deg]; p.body = [6 * deg, 0, 0]; p.eyeClose = 1; p.arrowBob = -0.035; p.arrowScale = 0.92 })
MOODS.s_coin = pose((p) => { holdBoth(p); p.winkR = 1; p.mouth = 0.35; p.head[2] = 5 * deg })
MOODS.s_book = pose((p) => { holdBoth(p); p.head[0] = 12 * deg; p.brow = 0.3; p.turn = 0.25 })
MOODS.s_tablet = pose((p) => { holdBoth(p); p.mouth = 0.35; p.brow = 0.4; p.turn = -0.22; p.head[2] = 4 * deg })
MOODS.s_phone = pose((p) => { p.armR = [-70 * deg, -28 * deg, -30 * deg]; p.foreR = [-35 * deg, -10 * deg, 0]; p.head = [8 * deg, -10 * deg, -4 * deg]; p.mouth = 0.3; p.turn = 0.2 })

// The per-place gestures (src/mascot/places.js), each caught at its most
// telling moment: the stills that stand in for them while the model loads and
// for anyone who turned animation off.
const at = (mood, t) => (_, p) => MOODS[mood](t, p)
MOODS.s_present = at('present', 2.0)
MOODS.s_weigh = at('weigh', 1.05)
MOODS.s_introduce = at('introduce', 2.0)
MOODS.s_invite = at('invite', 1.05)
MOODS.s_welcome = at('welcome', 0.8)
MOODS.s_ready = at('ready', 0.75)
MOODS.s_handshake = at('handshake', 1.2)
MOODS.s_warmup = at('warmup', 2.0)
MOODS.s_point = at('point', 0.65)
MOODS.s_proud = at('proud', 1.7)
MOODS.s_eager = at('eager', 0.3)
MOODS.s_reading = at('reading', 1.2)
MOODS.s_shy = at('shy', 1.0)
MOODS.s_peek = at('peek', 1.0)

const place = (mesh, x, y, z, rx = 0, ry = 0, rz = 0) => { mesh.position.set(x, y, z); mesh.rotation.x += rx; mesh.rotation.y += ry; mesh.rotation.z += rz; return mesh }

export const SPECS = [
  { name: 'idle', mood: 's_idle' },
  { name: 'wave', mood: 's_wave', decor: 'motion' },
  { name: 'think', mood: 's_think', decor: 'dots' },
  { name: 'happy', mood: 's_happy', decor: 'sparkles' },
  { name: 'celebrate', mood: 's_celebrate', decor: 'sparkles' },
  { name: 'clap', mood: 's_clap', decor: 'burst' },
  { name: 'cheer', mood: 's_cheer', decor: 'motion' },
  { name: 'confused', mood: 's_confused', decor: 'question' },
  { name: 'sleep', mood: 's_sleep', decor: 'sleep' },
  { name: 'coin', mood: 's_coin', decor: 'sparkles', props: () => [place(coin(), 0, -0.24, 0.47, 0, 0, -0.15)] },
  { name: 'book', mood: 's_book', props: () => [place(book(), 0, -0.2, 0.46, -0.3, 0, 0.06)] },
  { name: 'tablet', mood: 's_tablet', props: () => [place(tablet(), -0.02, -0.19, 0.45, -0.18, 0, -0.06)] },
  { name: 'phone', mood: 's_phone', props: () => [place(phone(), 0.1, -0.08, 0.48, -0.2, -0.25, -0.12)] },
  { name: 'present', mood: 's_present' },
  { name: 'weigh', mood: 's_weigh' },
  { name: 'introduce', mood: 's_introduce' },
  { name: 'invite', mood: 's_invite', decor: 'motion' },
  { name: 'welcome', mood: 's_welcome', decor: 'sparkles' },
  { name: 'ready', mood: 's_ready', decor: 'motion' },
  { name: 'handshake', mood: 's_handshake' },
  { name: 'warmup', mood: 's_warmup', decor: 'motion' },
  { name: 'point', mood: 's_point' },
  { name: 'proud', mood: 's_proud' },
  { name: 'eager', mood: 's_eager', decor: 'sparkles' },
  { name: 'reading', mood: 's_reading' },
  { name: 'shy', mood: 's_shy' },
  { name: 'peek', mood: 's_peek' },
]

const grid = document.getElementById('grid')
const only = new URLSearchParams(location.search).get('only')
if (new URLSearchParams(location.search).has('capture')) document.body.classList.add('capture')

window.__stickers = []
for (const spec of SPECS.filter((s) => !only || only.split(',').includes(s.name))) {
  const box = document.createElement('div')
  box.className = 'sticker'
  box.dataset.name = spec.name
  box.innerHTML = `<div class="stage"></div>${spec.decor ? `<svg viewBox="0 0 512 512">${DECOR[spec.decor]}</svg>` : ''}<span class="label">${spec.name}</span>`
  grid.appendChild(box)
  await createBear(box.querySelector('.stage'), {
    mood: spec.mood,
    still: true,
    preserveDrawingBuffer: true,
    props: spec.props ? spec.props() : [],
  })
  window.__stickers.push(spec.name)
}
window.__done = true
