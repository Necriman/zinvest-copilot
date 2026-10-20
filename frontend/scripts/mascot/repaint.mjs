// Touch-up of the Meshy bear's paint, on the full-size (4K) texture. Runs on
// the full-size GLB after arrow-lift.mjs and before build-web.mjs:
//   node scripts/mascot/repaint.mjs in.glb out.glb --model v8 [--models path/to/models.js] [--debug dir]
//   DEBUG_TEX=1 ... paints the classes red / green / magenta instead.
//
// Meshy bakes everything (body, glasses, brows, chain) into one mesh and one
// atlas, and fills the space between UV islands with whatever it had — mostly
// the chain's blue. Downscaled for the web, that blue bleeds in along every
// seam: blue under the brows, blue flecks on the glasses. So:
//   1. every texel gets its model-space position (rasterise the triangles in UV);
//   2. glasses: dark texels in a band around the head, mapped onto a cylinder
//      around the head and closed (dilate + erode) so the white streaks Meshy
//      painted into the frame are filled. Under that mask, dark texels and the
//      outer layer (the frame itself, not the face seen through the lens) are
//      painted one clean black, a little glossier;
//   3. brows: one flat charcoal, and the blue next to them becomes fur;
//   4. blue anywhere else on the head becomes fur;
//   5. the space between islands is refilled from the nearest island (edge
//      padding), in all three textures, so nothing foreign bleeds in any more.
// Before any of that, a washed-out export is graded: grey fur is lifted to
// white and a dull arrow gets its yellow back (v8 came out at fur 195/255 and
// a mustard arrow; v7's 252 and bright yellow are left alone), and grey smudges
// on the ears become fur.
//
// Where the face is comes from the model's entry in src/mascot/models.js
// (eyes, brows, rim, mouth, arrow); every size is scaled by its faceScale, as
// the numbers were first tuned on v7.
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'
import sharp from 'sharp'
import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const argv = process.argv.slice(2)
const flag = (name, fallback) => (argv.includes(name) ? argv[argv.indexOf(name) + 1] : fallback)
const [input, output] = argv.filter((a, i) => !a.startsWith('--') && !argv[i - 1]?.startsWith('--'))
const debugDir = flag('--debug', '')
const modelKey = flag('--model', 'v7')
const modelsPath = flag('--models', resolve(dirname(fileURLToPath(import.meta.url)), '../../src/mascot/models.js'))
const { MODELS } = await import(pathToFileURL(modelsPath).href)
const MODEL = MODELS[modelKey]
if (!MODEL) throw new Error(`no model ${modelKey} in ${modelsPath}`)
const L = MODEL.landmarks
const S = MODEL.faceScale || 1
console.log('model', modelKey, 'faceScale', S)
if (debugDir) mkdirSync(debugDir, { recursive: true })
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
const doc = await io.read(input)
const mat = doc.getRoot().listMaterials()[0]
const prim = doc.getRoot().listMeshes()[0].listPrimitives()[0]
const baseTex = mat.getBaseColorTexture()
const [W, H] = baseTex.getSize()
const decode = async (tex) => (await sharp(Buffer.from(tex.getImage())).ensureAlpha().raw().toBuffer({ resolveWithObject: true })).data
const base = await decode(baseTex)

// ---- 1. texel -> model position -------------------------------------------
const POS = prim.getAttribute('POSITION'), UV = prim.getAttribute('TEXCOORD_0')
const N = POS.getCount()
const pos = new Float32Array(N * 3), uv = new Float32Array(N * 2)
{ const p = [], t = []; for (let i = 0; i < N; i++) { POS.getElement(i, p); pos.set(p, i * 3); UV.getElement(i, t); uv.set(t, i * 2) } }
const idx = prim.getIndices().getArray()
const covered = new Uint8Array(W * H)
const PX = new Float32Array(W * H), PY = new Float32Array(W * H), PZ = new Float32Array(W * H)
for (let t = 0; t < idx.length; t += 3) {
  const a = idx[t], b = idx[t + 1], c = idx[t + 2]
  const x0 = uv[a * 2] * W, y0 = uv[a * 2 + 1] * H, x1 = uv[b * 2] * W, y1 = uv[b * 2 + 1] * H, x2 = uv[c * 2] * W, y2 = uv[c * 2 + 1] * H
  const area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
  if (Math.abs(area) < 1e-9) continue
  const i0 = Math.max(0, Math.floor(Math.min(x0, x1, x2))), i1 = Math.min(W - 1, Math.ceil(Math.max(x0, x1, x2)))
  const j0 = Math.max(0, Math.floor(Math.min(y0, y1, y2))), j1 = Math.min(H - 1, Math.ceil(Math.max(y0, y1, y2)))
  for (let j = j0; j <= j1; j++) {
    const cy = j + 0.5
    for (let i = i0; i <= i1; i++) {
      const cx = i + 0.5
      const w0 = ((x1 - cx) * (y2 - cy) - (x2 - cx) * (y1 - cy)) / area
      const w1 = ((x2 - cx) * (y0 - cy) - (x0 - cx) * (y2 - cy)) / area
      const w2 = 1 - w0 - w1
      if (w0 < -1e-4 || w1 < -1e-4 || w2 < -1e-4) continue
      const k = j * W + i
      covered[k] = 1
      PX[k] = w0 * pos[a * 3] + w1 * pos[b * 3] + w2 * pos[c * 3]
      PY[k] = w0 * pos[a * 3 + 1] + w1 * pos[b * 3 + 1] + w2 * pos[c * 3 + 1]
      PZ[k] = w0 * pos[a * 3 + 2] + w1 * pos[b * 3 + 2] + w2 * pos[c * 3 + 2]
    }
  }
}
let nCov = 0; for (let k = 0; k < W * H; k++) nCov += covered[k]
console.log('covered texels', nCov, `(${(100 * nCov / W / H).toFixed(1)}%)`)

// ---- colour classes --------------------------------------------------------
const rgb = (k) => [base[k * 4], base[k * 4 + 1], base[k * 4 + 2]]
const isDark = (r, g, b) => Math.max(r, g, b) < 80
const isBlue = (r, g, b) => b > 90 && b - Math.max(r, g) > 25
const isFur = (r, g, b) => Math.min(r, g, b) > 170 && Math.max(r, g, b) - Math.min(r, g, b) < 40

// The face's own numbers, from src/mascot/models.js. The offsets were tuned on
// v7 (eyes at 1.156, mouth at 0.993) and scale with the painted face.
const EYES = [L.eyeL, L.eyeR]
const BROWS = [L.browL, L.browR]
const EYE_Y = (L.eyeL[1] + L.eyeR[1]) / 2
const HEAD_LO = L.mouth[1] + 0.037 * S // above the chain and the mouth
const HEAD_HI = L.arrowY // the arrow starts above
const inEye = (x, y, z) => z > 0.15 && EYES.some(([ex, ey]) => ((x - ex) / (0.062 * S)) ** 2 + ((y - ey) / (0.086 * S)) ** 2 < 1)
const inNose = (x, y, z) => z > 0.2 && y < EYE_Y - 0.056 * S && Math.abs(x) < 0.1 * S
const browD = (x, y) => Math.min(...BROWS.map(([bx, by]) => Math.hypot((x - bx) / (0.085 * S), (y - by) / (0.034 * S))))

// ---- 0. grading a washed-out export -------------------------------------------
const lumOf = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b
{
  const furLum = []
  for (let k = 0; k < W * H; k += 5) {
    if (!covered[k] || PY[k] < EYE_Y - 0.1 || PY[k] > L.arrowY) continue
    const [r, g, b] = rgb(k)
    if (Math.max(r, g, b) - Math.min(r, g, b) < 30 && lumOf(r, g, b) > 140) furLum.push(lumOf(r, g, b))
  }
  furLum.sort((a, b) => a - b)
  const furMedian = furLum[furLum.length >> 1]
  // Lift grey fur to near white; darker greys (brows, shadows) fade out of it.
  const lift = furMedian < 235 ? 246 / furMedian : 1
  const arrowSat = []
  for (let k = 0; k < W * H; k += 3) {
    if (!covered[k] || PY[k] < L.arrowY) continue
    const [r, g, b] = rgb(k)
    const mx = Math.max(r, g, b)
    if (mx > 40) arrowSat.push((mx - Math.min(r, g, b)) / mx)
  }
  arrowSat.sort((a, b) => a - b)
  const arrowMedian = arrowSat[arrowSat.length >> 1] || 1
  console.log('fur median', furMedian?.toFixed(1), 'lift', lift.toFixed(3), 'arrow saturation', arrowMedian.toFixed(2))
  const hsv2rgb = (h, s, v) => {
    const f = (n) => { const k = (n + h / 60) % 6; return v - v * s * Math.max(0, Math.min(k, 4 - k, 1)) }
    return [f(5), f(3), f(1)].map((c) => Math.round(Math.min(255, c * 255)))
  }
  for (let k = 0; k < W * H; k++) {
    if (!covered[k]) continue
    const [r, g, b] = rgb(k)
    const mx = Math.max(r, g, b), sat = mx - Math.min(r, g, b)
    if (PY[k] >= L.arrowY) {
      // The arrow: v7's saturated yellow (hue 48°), keeping the baked shading.
      if (arrowMedian < 0.65 && mx > 30) base.set(hsv2rgb(48, 0.8, Math.min(1, (mx / 255) * 1.18)), k * 4)
      continue
    }
    if (lift !== 1 && sat < 40) {
      const w = Math.max(0, Math.min(1, (lumOf(r, g, b) - 90) / 50))
      const f = 1 + (lift - 1) * w
      base[k * 4] = Math.min(255, r * f); base[k * 4 + 1] = Math.min(255, g * f); base[k * 4 + 2] = Math.min(255, b * f)
    }
  }
}

// head axis for the cylinder
let zMin = 9, zMax = -9
for (let i = 0; i < N; i++) { const y = pos[i * 3 + 1]; if (y > EYE_Y - 0.06 && y < EYE_Y + 0.14 && Math.abs(pos[i * 3]) < 0.05) { zMin = Math.min(zMin, pos[i * 3 + 2]); zMax = Math.max(zMax, pos[i * 3 + 2]) } }
const CZ = (zMin + zMax) / 2
console.log('head z', zMin.toFixed(3), zMax.toFixed(3), 'axis at z', CZ.toFixed(3))

// ---- 2. glasses mask on a cylinder around the head ------------------------
const TB = 0.004, YB = 0.0015
const GW = Math.ceil((2 * Math.PI) / TB), GH = Math.ceil((HEAD_HI - HEAD_LO) / YB)
const cellOf = (k) => {
  const th = Math.atan2(PX[k], PZ[k] - CZ) + Math.PI
  return Math.min(GH - 1, Math.floor((PY[k] - HEAD_LO) / YB)) * GW + (Math.floor(th / TB) % GW)
}
const radius = (k) => Math.hypot(PX[k], PZ[k] - CZ)
// rMax: the outermost surface in each cell. The frame stands 5-6 cm off the
// face, so the cylinder also puts some of the face seen through the lens under
// it; only the outer layer is the frame.
const nDark = new Uint32Array(GW * GH), nAny = new Uint32Array(GW * GH), rMax = new Float32Array(GW * GH)
for (let k = 0; k < W * H; k++) {
  if (!covered[k] || PY[k] < HEAD_LO || PY[k] >= HEAD_HI) continue
  if (inEye(PX[k], PY[k], PZ[k]) || inNose(PX[k], PY[k], PZ[k])) continue
  const c = cellOf(k)
  nAny[c]++
  rMax[c] = Math.max(rMax[c], radius(k))
  const [r, g, b] = rgb(k)
  if (isDark(r, g, b)) nDark[c]++
}
let mask = new Uint8Array(GW * GH)
for (let c = 0; c < GW * GH; c++) mask[c] = nDark[c] >= 2 && nDark[c] >= 0.25 * nAny[c] ? 1 : 0
const morph = (m, r, grow) => {
  const out = new Uint8Array(GW * GH)
  for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
    let hit = grow ? 0 : 1
    for (let dy = -r; dy <= r && hit === (grow ? 0 : 1); dy++) {
      const yy = y + dy
      if (yy < 0 || yy >= GH) { if (!grow) hit = 1; continue }
      for (let dx = -r; dx <= r; dx++) {
        if (dx * dx + dy * dy > r * r) continue
        const v = m[yy * GW + ((x + dx + GW) % GW)]
        if (grow && v) { hit = 1; break }
        if (!grow && !v) { hit = 0; break }
      }
    }
    out[y * GW + x] = hit
  }
  return out
}
const R = 3
const closed = morph(morph(mask, R, true), R, false)
// speckles: drop mask islands smaller than a few cells
{
  const seen = new Uint8Array(GW * GH)
  for (let s = 0; s < GW * GH; s++) {
    if (!closed[s] || seen[s]) continue
    const stack = [s], comp = []; seen[s] = 1
    while (stack.length) {
      const c = stack.pop(); comp.push(c)
      const x = c % GW, y = (c - x) / GW
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const yy = y + dy; if (yy < 0 || yy >= GH) continue
        const n = yy * GW + ((x + dx + GW) % GW)
        if (closed[n] && !seen[n]) { seen[n] = 1; stack.push(n) }
      }
    }
    if (comp.length < 40) for (const c of comp) closed[c] = 0
  }
}
if (debugDir) {
  const img = Buffer.alloc(GW * GH * 3)
  for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
    const c = y * GW + x, o = ((GH - 1 - y) * GW + x) * 3
    if (!nAny[c]) { img[o] = 230; img[o + 1] = 235; img[o + 2] = 245; continue }
    const d = nDark[c] / nAny[c]
    img[o] = closed[c] ? 200 : 255 * (1 - d); img[o + 1] = closed[c] ? 40 * (1 - d) : 255 * (1 - d); img[o + 2] = closed[c] ? 40 * (1 - d) : 255 * (1 - d)
  }
  await sharp(img, { raw: { width: GW, height: GH, channels: 3 } }).png().toFile(`${debugDir}/cyl-mask.png`)
}

// ---- 3./4. repaint ----------------------------------------------------------
// DEBUG_TEX=1 paints the classes in loud colours instead, to see them on the model.
const DBG = !!process.env.DEBUG_TEX
const GLASS = DBG ? [255, 0, 0] : [14, 15, 19], BROW = DBG ? [0, 200, 0] : [74, 77, 86]
// the fur colour: median of the head's white texels
const furSamples = []
for (let k = 0; k < W * H; k += 7) if (covered[k] && PY[k] > EYE_Y - 0.06 && PY[k] < L.arrowY - 0.07) { const [r, g, b] = rgb(k); if (isFur(r, g, b)) furSamples.push([r, g, b]) }
const med = (a) => { a.sort((x, y) => x - y); return a[a.length >> 1] }
const FUR = [0, 1, 2].map((ch) => med(furSamples.map((s) => s[ch])))
console.log('fur', FUR, 'from', furSamples.length)
const paintClass = new Uint8Array(W * H) // 1 glasses, 2 brow, 3 fur fix
const put = (k, c) => { base[k * 4] = c[0]; base[k * 4 + 1] = c[1]; base[k * 4 + 2] = c[2] }
const counts = [0, 0, 0, 0]
for (let k = 0; k < W * H; k++) {
  if (!covered[k] || PY[k] < HEAD_LO || PY[k] >= HEAD_HI) continue
  const x = PX[k], y = PY[k], z = PZ[k]
  const [r, g, b] = rgb(k)
  if (inEye(x, y, z) || inNose(x, y, z)) {
    // blue flecks round the eyes and nose: back to black or fur, whichever is closer
    if (isBlue(r, g, b)) put(k, DBG ? [255, 0, 255] : r + g + b < 330 ? [8, 8, 10] : FUR)
    continue
  }
  const bd = z > 0.15 && y > L.rimTop + 0.003 * S ? browD(x, y) : 9
  if (bd < 1 && !isFur(r, g, b)) { put(k, BROW); paintClass[k] = 2; counts[2]++; continue }
  const cell = cellOf(k)
  // Dark texels under the mask are frame already; white and blue ones only
  // when they are on the outer layer (the frame's own streaks and flecks).
  if (closed[cell] && (isDark(r, g, b) || radius(k) > rMax[cell] - 0.012 * S)) { put(k, GLASS); paintClass[k] = 1; counts[1]++; continue }
  // Grey smudges out on the ears (v8's left ear), above the frame and beyond
  // the brows: the ears are plain fur.
  const smudge = y > L.rimTop && Math.abs(x) > Math.abs(L.browL[0]) + 0.1 * S &&
    lumOf(r, g, b) > 40 && lumOf(r, g, b) < 150 && Math.max(r, g, b) - Math.min(r, g, b) < 30
  if (isBlue(r, g, b) || smudge || (bd < 1.5 && !isFur(r, g, b))) { put(k, DBG ? [255, 0, 255] : FUR); paintClass[k] = 3; counts[3]++ }
}
console.log('painted: glasses', counts[1], 'brows', counts[2], 'fur fixes', counts[3])
// where the brows ended up (for the brow lift in rig.js)
for (const side of [-1, 1]) {
  const lo = [9, 9, 9], hi = [-9, -9, -9]
  for (let k = 0; k < W * H; k++) if (paintClass[k] === 2 && Math.sign(PX[k]) === side) {
    const p = [PX[k], PY[k], PZ[k]]
    for (let a = 0; a < 3; a++) { lo[a] = Math.min(lo[a], p[a]); hi[a] = Math.max(hi[a], p[a]) }
  }
  console.log('brow', side, lo.map((v) => v.toFixed(3)).join(','), '->', hi.map((v) => v.toFixed(3)).join(','))
}
// the glasses' top edge under each brow
for (const bx of [-0.136, 0.135]) {
  let top = 0
  for (let k = 0; k < W * H; k++) if (paintClass[k] === 1 && PZ[k] > 0.15 && Math.abs(PX[k] - bx) < 0.06) top = Math.max(top, PY[k])
  console.log('frame top under brow at x', bx, top.toFixed(3))
}

// ---- 5. edge padding: grow islands outwards, then push-pull the rest ---------
function pad(data, channels, iters) {
  const filled = covered.slice()
  let front = []
  for (let k = 0; k < W * H; k++) if (!filled[k]) {
    const i = k % W, j = (k - i) / W
    if ((i > 0 && filled[k - 1]) || (i < W - 1 && filled[k + 1]) || (j > 0 && filled[k - W]) || (j < H - 1 && filled[k + W])) front.push(k)
  }
  const acc = new Float32Array(channels)
  for (let it = 0; it < iters && front.length; it++) {
    const done = []
    for (const k of front) {
      const i = k % W, j = (k - i) / W
      acc.fill(0); let n = 0
      for (let dj = -1; dj <= 1; dj++) for (let di = -1; di <= 1; di++) {
        const ii = i + di, jj = j + dj
        if (ii < 0 || jj < 0 || ii >= W || jj >= H) continue
        const q = jj * W + ii
        if (filled[q] !== 1) continue
        for (let ch = 0; ch < channels; ch++) acc[ch] += data[q * 4 + ch]
        n++
      }
      if (n) { for (let ch = 0; ch < channels; ch++) data[k * 4 + ch] = Math.round(acc[ch] / n); done.push(k) }
    }
    for (const k of done) filled[k] = 2 // not a source until the pass ends
    const next = new Set()
    for (const k of done) {
      filled[k] = 1
      const i = k % W, j = (k - i) / W
      if (i > 0 && !filled[k - 1]) next.add(k - 1)
      if (i < W - 1 && !filled[k + 1]) next.add(k + 1)
      if (j > 0 && !filled[k - W]) next.add(k - W)
      if (j < H - 1 && !filled[k + W]) next.add(k + W)
    }
    front = [...next]
  }
  // push-pull for whatever is still empty
  let levels = [{ w: W, h: H, c: new Float32Array(W * H * channels), m: new Float32Array(W * H) }]
  for (let k = 0; k < W * H; k++) if (filled[k]) { levels[0].m[k] = 1; for (let ch = 0; ch < channels; ch++) levels[0].c[k * channels + ch] = data[k * 4 + ch] }
  while (levels.at(-1).w > 1) {
    const s = levels.at(-1), w = s.w >> 1, h = s.h >> 1
    const c = new Float32Array(w * h * channels), m = new Float32Array(w * h)
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
      let mm = 0; const o = j * w + i
      for (const [di, dj] of [[0, 0], [1, 0], [0, 1], [1, 1]]) {
        const q = (j * 2 + dj) * s.w + i * 2 + di
        mm += s.m[q]
        for (let ch = 0; ch < channels; ch++) c[o * channels + ch] += s.c[q * channels + ch] * s.m[q]
      }
      if (mm > 0) { for (let ch = 0; ch < channels; ch++) c[o * channels + ch] /= mm; m[o] = 1 }
    }
    levels.push({ w, h, c, m })
  }
  for (let l = levels.length - 2; l >= 0; l--) {
    const s = levels[l], p = levels[l + 1]
    for (let j = 0; j < s.h; j++) for (let i = 0; i < s.w; i++) {
      const o = j * s.w + i
      if (s.m[o]) continue
      const q = Math.min(p.h - 1, j >> 1) * p.w + Math.min(p.w - 1, i >> 1)
      for (let ch = 0; ch < channels; ch++) s.c[o * channels + ch] = p.c[q * channels + ch]
      s.m[o] = 1
    }
  }
  for (let k = 0; k < W * H; k++) if (!filled[k]) for (let ch = 0; ch < channels; ch++) data[k * 4 + ch] = Math.round(levels[0].c[k * channels + ch])
}
const encode = (data) => sharp(data, { raw: { width: W, height: H, channels: 4 } }).removeAlpha().png().toBuffer()

pad(base, 3, 32)
baseTex.setImage(new Uint8Array(await encode(base)))

// glasses a touch glossier: roughness (G) down where they were painted
const mrTex = mat.getMetallicRoughnessTexture()
if (mrTex) {
  const mr = await decode(mrTex)
  for (let k = 0; k < W * H; k++) if (paintClass[k] === 1) { mr[k * 4 + 1] = Math.min(mr[k * 4 + 1], 90); mr[k * 4 + 2] = 0 }
  pad(mr, 3, 32)
  mrTex.setImage(new Uint8Array(await encode(mr)))
}
const nTex = mat.getNormalTexture()
if (nTex) {
  const nm = await decode(nTex)
  pad(nm, 3, 32)
  nTex.setImage(new Uint8Array(await encode(nm)))
}
if (debugDir) {
  await sharp(base, { raw: { width: W, height: H, channels: 4 } }).removeAlpha().resize(1024, 1024).png().toFile(`${debugDir}/tex-after.png`)
}
await io.write(output, doc)
console.log('wrote', output)
