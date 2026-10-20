// Builds public/models/zinvest-bear-v6.glb from Meshy's "rig ready biped" export.
//
// Meshy's auto-rig puts a Mixamo skeleton inside the model but paints most of
// the upper body onto the head and shoulder bones (the upper arms barely follow
// their own bones), so raising an arm drags the chest along. This script keeps
// the skeleton and repaints the weights. The model must be in an A-pose, with
// the arms clear of the body down to the armpit.
//
//   * arms: "heat" spreads over the surface from the paw and forearm (fixed at
//     1) towards the middle of the body (fixed at 0), with each edge conducting
//     1 / length, so it stays in the arm and fades at the armpit. Seeds are
//     vertices near the bones that the bone can see (the segment from the bone
//     does not cross the surface).
//   * inside an arm: hand / forearm / upper arm by position along the bones,
//     blended at the wrist and elbow; the root blends into the chest.
//   * legs: by height and side, blended at the knee and the hip.
//   * head: everything above the collar, the floating arrow included.
//   * body: the spine bones by height.
// The weights are then smoothed over the surface a few times. The walk clip
// of the first file and the run clip of the second are kept as "walk" / "run".
//
// Needs @gltf-transform/core and /extensions (not project dependencies):
//   node reskin.mjs <..._Walking_withSkin.glb> <out.glb> [--clips <..._Running_withSkin.glb>] [--report]
//   npx @gltf-transform/cli optimize out.glb zinvest-bear-v6.glb --compress meshopt
//     --texture-compress webp --texture-size 1024 --simplify false
//
// v7 (a 200k-triangle export whose arrow touches the ears) adds three steps, which
// also need @gltf-transform/functions, meshoptimizer and sharp:
//   node reskin.mjs <..._Walking_withSkin.glb> skinned.glb --clips <..._Running_withSkin.glb>
//   node arrow-lift.mjs skinned.glb lifted.glb 0.02      # prints arrowY and the arrow centre
//   node --max-old-space-size=8192 repaint.mjs lifted.glb painted.glb   # clean glasses, brows, seams
//   node build-web.mjs painted.glb zinvest-bear-v7.glb 0.12   # ~24k triangles, 1024px WebP
// then arms.mjs and measure.html for the numbers in src/mascot/models.js.
//
// v8 (10k triangles, no finger bones, grey paint, metallic + emissive material):
//   node reskin.mjs <..._Walking_withSkin.glb> skinned.glb --clips <..._Running_withSkin.glb>
//   node arrow-lift.mjs skinned.glb lifted.glb 0.02
//   (write the v8 entry in models.js first: repaint reads its face numbers)
//   node --max-old-space-size=8192 repaint.mjs lifted.glb painted.glb --model v8
//   node build-web.mjs painted.glb zinvest-bear-v8.glb 1      # no simplifying; matte material
// The lengths in this script scale with the skeleton (SX, SY below), and the
// paw tip comes from the forearm when there are no finger bones. The face
// numbers came from the texture itself (every texel at its model position,
// frontmost wins), since measure.html cannot tell grey fur from grey brows.
// Stickers: node render-stickers.cjs (in two batches; a page holds ~16 bears).
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'

const args = process.argv.slice(2)
const [input, output] = args.filter((a, i) => !a.startsWith('--') && args[i - 1] !== '--clips')
const clipsFile = args.includes('--clips') ? args[args.indexOf('--clips') + 1] : null
const report = args.includes('--report')
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
const doc = await io.read(input)
const root = doc.getRoot()
const skin = root.listSkins()[0]
const joints = skin.listJoints()
const jointIndex = new Map(joints.map((j, i) => [j.getName().replace('mixamorig:', ''), i]))
const J = (name) => {
  if (!jointIndex.has(name)) throw new Error('missing joint ' + name)
  return jointIndex.get(name)
}
const at = (name) => { const m = joints[J(name)].getWorldMatrix(); return [m[12], m[13], m[14]] }

// Every length below was tuned on v6/v7, whose head joint sits at y 0.929 and
// upper arm at x 0.246. Another model scales them by its own skeleton: heights
// by the head, widths by the shoulders, distances from a bone by both (v8 is
// 1.11 times as tall and 1.2 times as wide).
const SY = at('Head')[1] / 0.929
const SX = Math.abs(at('LeftArm')[0]) / 0.246
const SD = (SX + SY) / 2
if (report) console.log('scale', { SX: +SX.toFixed(3), SY: +SY.toFixed(3) })

const prim = root.listMeshes()[0].listPrimitives()[0]
const POS = prim.getAttribute('POSITION')
const N = POS.getCount()
const pos = new Float32Array(N * 3)
{ const p = []; for (let i = 0; i < N; i++) { POS.getElement(i, p); pos.set(p, i * 3) } }
const P = (i) => [pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]]
const NRM = prim.getAttribute('NORMAL')

// --- surface graph, welded by position so UV seams do not cut it
const weldKey = new Map()
const pid = new Int32Array(N)
for (let i = 0; i < N; i++) {
  const k = `${Math.round(pos[i * 3] * 1e5)},${Math.round(pos[i * 3 + 1] * 1e5)},${Math.round(pos[i * 3 + 2] * 1e5)}`
  if (!weldKey.has(k)) weldKey.set(k, weldKey.size)
  pid[i] = weldKey.get(k)
}
const M = weldKey.size
const rep = new Int32Array(M).fill(-1)
for (let i = 0; i < N; i++) if (rep[pid[i]] < 0) rep[pid[i]] = i
const nrm = new Float32Array(M * 3) // welded normals: average of the duplicates
{ const n = []; for (let i = 0; i < N; i++) { NRM.getElement(i, n); for (let k = 0; k < 3; k++) nrm[pid[i] * 3 + k] += n[k] } }
for (let a = 0; a < M; a++) { const l = Math.hypot(nrm[a * 3], nrm[a * 3 + 1], nrm[a * 3 + 2]) || 1; for (let k = 0; k < 3; k++) nrm[a * 3 + k] /= l }
const nbr = Array.from({ length: M }, () => new Set())
const idx = prim.getIndices().getArray()
for (let t = 0; t < idx.length; t += 3) {
  const a = pid[idx[t]], b = pid[idx[t + 1]], c = pid[idx[t + 2]]
  nbr[a].add(b); nbr[a].add(c); nbr[b].add(a); nbr[b].add(c); nbr[c].add(a); nbr[c].add(b)
}
const len3 = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])
const edges = nbr.map((set, a) => [...set].map((b) => [b, len3(P(rep[a]), P(rep[b]))]))

// component id (the floating arrow is its own component)
const comp = new Int32Array(M).fill(-1)
let compCount = 0
for (let s = 0; s < M; s++) {
  if (comp[s] >= 0) continue
  const stack = [s]; comp[s] = compCount
  while (stack.length) { const a = stack.pop(); for (const [b] of edges[a]) if (comp[b] < 0) { comp[b] = compCount; stack.push(b) } }
  compCount++
}
const compSize = new Int32Array(compCount)
for (let a = 0; a < M; a++) compSize[comp[a]]++
const mainComp = compSize.indexOf(Math.max(...compSize))

// Closest point on a polyline; returns { s: arc length from the first point, d: distance, q: the point }.
function project(chain, p) {
  let best = { s: 0, d: Infinity, q: chain[0] }, acc = 0
  for (let k = 0; k < chain.length - 1; k++) {
    const a = chain[k], b = chain[k + 1]
    const ab = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
    const L = Math.hypot(...ab)
    let t = ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1] + (p[2] - a[2]) * ab[2]) / (L * L)
    t = Math.max(0, Math.min(1, t))
    const q = [a[0] + ab[0] * t, a[1] + ab[1] * t, a[2] + ab[2] * t]
    const d = len3(p, q)
    if (d < best.d) best = { s: acc + t * L, d, q }
    acc += L
  }
  return best
}

// --- triangles in a uniform grid, for segment/surface tests
const CELL = 0.03
const tris = []
const grid = new Map()
const cellKey = (x, y, z) => `${x},${y},${z}`
for (let t = 0; t < idx.length; t += 3) {
  const a = P(idx[t]), b = P(idx[t + 1]), c = P(idx[t + 2])
  const id = tris.length
  tris.push([a, b, c, pid[idx[t]], pid[idx[t + 1]], pid[idx[t + 2]]])
  const lo = [0, 1, 2].map((k) => Math.floor(Math.min(a[k], b[k], c[k]) / CELL))
  const hi = [0, 1, 2].map((k) => Math.floor(Math.max(a[k], b[k], c[k]) / CELL))
  for (let x = lo[0]; x <= hi[0]; x++) for (let y = lo[1]; y <= hi[1]; y++) for (let z = lo[2]; z <= hi[2]; z++) {
    const key = cellKey(x, y, z)
    let list = grid.get(key)
    if (!list) grid.set(key, (list = []))
    list.push(id)
  }
}
// Does the open segment from q to vertex a cross any triangle not touching a?
function blocked(q, a) {
  const p = P(rep[a])
  const dir = [p[0] - q[0], p[1] - q[1], p[2] - q[2]]
  const L = Math.hypot(...dir)
  const steps = Math.max(1, Math.ceil(L / (CELL * 0.5)))
  const seen = new Set()
  for (let k = 0; k <= steps; k++) {
    const f = k / steps
    const c = [q[0] + dir[0] * f, q[1] + dir[1] * f, q[2] + dir[2] * f].map((v) => Math.floor(v / CELL))
    for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) for (let dz = -1; dz <= 1; dz++) {
      const list = grid.get(cellKey(c[0] + dx, c[1] + dy, c[2] + dz))
      if (!list) continue
      for (const id of list) {
        if (seen.has(id)) continue
        seen.add(id)
        const [v0, v1, v2, i0, i1, i2] = tris[id]
        if (i0 === a || i1 === a || i2 === a) continue
        // Moller-Trumbore
        const e1 = [v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]], e2 = [v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]]
        const h = [dir[1] * e2[2] - dir[2] * e2[1], dir[2] * e2[0] - dir[0] * e2[2], dir[0] * e2[1] - dir[1] * e2[0]]
        const det = e1[0] * h[0] + e1[1] * h[1] + e1[2] * h[2]
        if (Math.abs(det) < 1e-12) continue
        const inv = 1 / det
        const sv = [q[0] - v0[0], q[1] - v0[1], q[2] - v0[2]]
        const u = inv * (sv[0] * h[0] + sv[1] * h[1] + sv[2] * h[2])
        if (u < 0 || u > 1) continue
        const qv = [sv[1] * e1[2] - sv[2] * e1[1], sv[2] * e1[0] - sv[0] * e1[2], sv[0] * e1[1] - sv[1] * e1[0]]
        const v = inv * (dir[0] * qv[0] + dir[1] * qv[1] + dir[2] * qv[2])
        if (v < 0 || u + v > 1) continue
        const t = inv * (e2[0] * qv[0] + e2[1] * qv[1] + e2[2] * qv[2])
        if (t > 1e-4 && t < 0.985) return true
      }
    }
  }
  return false
}

const smooth = (e0, e1, x) => { const t = Math.max(0, Math.min(1, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t) }

// weights[a] = Map(jointIndex -> weight) per welded vertex
const weights = Array.from({ length: M }, () => new Map())
const add = (a, j, w) => { if (w > 1e-4) weights[a].set(j, (weights[a].get(j) || 0) + w) }

// --- arms
const ARM_RADIUS = 0.13 // generous: the facing test does the real separation
const armOf = new Float32Array(M) // how much of each vertex belongs to an arm (either side)
for (const side of ['Left', 'Right']) {
  const wrist = at(`${side}Hand`), elbow = at(`${side}ForeArm`), shoulder = at(`${side}Arm`)
  // Skeletons without finger bones (v8) get the paw tip from the forearm: in
  // v7 the middle finger's tip sits 0.57 forearm-lengths past the wrist.
  const tip = jointIndex.has(`${side}HandMiddle4`)
    ? at(`${side}HandMiddle4`)
    : wrist.map((w, k) => w + (w - elbow[k]) * 0.57)
  // past the hand tip a little, so the rounded end of the paw projects inside the chain
  const beyond = [tip[0] + (tip[0] - wrist[0]) * 0.6, tip[1] + (tip[1] - wrist[1]) * 0.6, tip[2] + (tip[2] - wrist[2]) * 0.6]
  const chain = [beyond, tip, wrist, elbow, shoulder, at(`${side}Shoulder`)]
  const s0 = len3(beyond, tip)
  const sWrist = s0 + len3(tip, wrist), sElbow = sWrist + len3(wrist, elbow), sShoulder = sElbow + len3(elbow, shoulder)
  const info = new Array(M)
  const region = []
  const heat = new Float64Array(M)
  const fixed = new Uint8Array(M)
  for (let a = 0; a < M; a++) {
    if (comp[a] !== mainComp) continue
    const p = P(rep[a])
    const pr = project(chain, p)
    if (pr.d > 0.22 * SD || pr.s > sShoulder + 0.14 * SD) continue
    info[a] = pr
    region.push(a)
    const outside = side === 'Left' ? p[0] > 0.31 * SX : p[0] < -0.31 * SX
    const inside = side === 'Left' ? p[0] < 0.19 * SX : p[0] > -0.19 * SX
    if (inside || p[1] > 0.93 * SY || p[1] < 0.3 * SY) { fixed[a] = 1; heat[a] = 0 }
    else if ((pr.d < 0.06 * SD && pr.s < sElbow + 0.02 * SD) || (outside && pr.d < 0.075 * SD)) {
      if (!blocked(pr.q, a)) { fixed[a] = 1; heat[a] = 1 }
    }
  }
  const inRegion = new Uint8Array(M)
  for (const a of region) inRegion[a] = 1
  for (let iter = 0; iter < 600; iter++) {
    for (const a of region) {
      if (fixed[a]) continue
      let sum = 0, wsum = 0
      for (const [b, L] of edges[a]) {
        const w = 1 / Math.max(L, 0.004)
        sum += w * (inRegion[b] ? heat[b] : 0)
        wsum += w
      }
      heat[a] = sum / wsum
    }
  }
  const inArm = new Float32Array(M)
  for (const a of region) inArm[a] = smooth(0.3, 0.6, heat[a])
  const seeds = region.filter((a) => fixed[a] && heat[a] === 1)
  let count = 0
  for (let a = 0; a < M; a++) {
    if (!inArm[a]) continue
    const { s } = info[a]
    // the root of the arm melts into the chest
    const w = inArm[a] * (1 - smooth(sShoulder - 0.04 * SD, sShoulder + 0.06 * SD, s))
    if (w <= 0) continue
    armOf[a] += w
    count++
    const hand = 1 - smooth(sWrist - 0.02 * SD, sWrist + 0.03 * SD, s)
    const fore = (1 - hand) * (1 - smooth(sElbow - 0.03 * SD, sElbow + 0.03 * SD, s))
    const upper = 1 - hand - fore
    add(a, J(`${side}Hand`), w * hand)
    add(a, J(`${side}ForeArm`), w * fore)
    add(a, J(`${side}Arm`), w * upper)
  }
  if (report) console.log(side, 'arm seeds', seeds.length, 'arm vertices', count, 'chain', [sWrist, sElbow, sShoulder].map((v) => v.toFixed(3)))
}

// --- head, legs and body share whatever the arms did not take
const HEAD_LOW = 0.845 * SY, HEAD_HIGH = 0.925 * SY
for (let a = 0; a < M; a++) {
  const rest = Math.max(0, 1 - armOf[a])
  if (rest <= 1e-4) continue
  const [x, y] = P(rep[a])
  if (comp[a] !== mainComp) { add(a, J('Head'), rest); continue }
  const head = smooth(HEAD_LOW, HEAD_HIGH, y)
  add(a, J('Head'), rest * head)
  let body = rest * (1 - head)
  if (body <= 1e-4) continue
  const leg = 1 - smooth(0.24 * SY, 0.35 * SY, y)
  if (leg > 0) {
    const left = smooth(-0.035 * SX, 0.035 * SX, x)
    const foot = 1 - smooth(0.06 * SY, 0.11 * SY, y)
    const shin = (1 - foot) * (1 - smooth(0.17 * SY, 0.23 * SY, y))
    const thigh = 1 - foot - shin
    for (const [side, share] of [['Left', left], ['Right', 1 - left]]) {
      const w = body * leg * share
      add(a, J(`${side}Foot`), w * foot)
      add(a, J(`${side}Leg`), w * shin)
      add(a, J(`${side}UpLeg`), w * thigh)
    }
    body *= 1 - leg
  }
  const bands = [['Hips', -1, 0.40 * SY], ['Spine', 0.40 * SY, 0.53 * SY], ['Spine1', 0.53 * SY, 0.66 * SY], ['Spine2', 0.66 * SY, 9]]
  let total = 0
  const shares = bands.map(([, lo, hi]) => { const w = smooth(lo - 0.04 * SY, lo + 0.04 * SY, y) * (1 - smooth(hi - 0.04 * SY, hi + 0.04 * SY, y)); total += w; return w })
  bands.forEach(([name], k) => add(a, J(name), body * shares[k] / (total || 1)))
}

// --- smooth over the surface (keeps the arrow and the far ends untouched)
for (let iter = 0; iter < 2; iter++) {
  const next = weights.map((w, a) => {
    if (comp[a] !== mainComp) return w
    const out = new Map()
    const mix = (m, k) => { for (const [j, v] of m) out.set(j, (out.get(j) || 0) + v * k) }
    mix(w, 0.5)
    const list = edges[a]
    for (const [b] of list) mix(weights[b], 0.5 / list.length)
    return out
  })
  for (let a = 0; a < M; a++) weights[a] = next[a]
}

// --- write the four strongest influences
const JOINTS = new Uint16Array(N * 4)
const WEIGHTS = new Float32Array(N * 4)
const dominant = new Map()
for (let i = 0; i < N; i++) {
  const top = [...weights[pid[i]].entries()].sort((p, q) => q[1] - p[1]).slice(0, 4)
  const sum = top.reduce((s, [, w]) => s + w, 0) || 1
  top.forEach(([j, w], k) => { JOINTS[i * 4 + k] = j; WEIGHTS[i * 4 + k] = w / sum })
  const name = joints[top[0][0]].getName().replace('mixamorig:', '')
  dominant.set(name, (dominant.get(name) || 0) + 1)
}
prim.getAttribute('JOINTS_0').setArray(JOINTS)
prim.getAttribute('WEIGHTS_0').setArray(WEIGHTS)
if (report) console.log('dominant joints', Object.fromEntries([...dominant.entries()].sort((a, b) => b[1] - a[1])))
// --- animation clips: "walk" from this file, "run" from the twin export
for (const a of root.listAnimations()) {
  if (a.getName().endsWith('.001')) a.dispose() // one-frame rest pose
  else a.setName('walk')
}
if (clipsFile) {
  const other = await io.read(clipsFile)
  const byName = new Map(root.listNodes().map((n) => [n.getName(), n]))
  const buffer = root.listBuffers()[0]
  for (const src of other.getRoot().listAnimations()) {
    if (src.getName().endsWith('.001')) continue
    const anim = doc.createAnimation('run')
    const samplers = new Map()
    for (const ch of src.listChannels()) {
      const s0 = ch.getSampler()
      let sampler = samplers.get(s0)
      if (!sampler) {
        const copy = (acc) => doc.createAccessor().setType(acc.getType()).setArray(acc.getArray().slice()).setBuffer(buffer)
        sampler = doc.createAnimationSampler().setInput(copy(s0.getInput())).setOutput(copy(s0.getOutput())).setInterpolation(s0.getInterpolation())
        samplers.set(s0, sampler)
        anim.addSampler(sampler)
      }
      const target = byName.get(ch.getTargetNode().getName())
      if (!target) throw new Error('missing node ' + ch.getTargetNode().getName())
      anim.addChannel(doc.createAnimationChannel().setTargetNode(target).setTargetPath(ch.getTargetPath()).setSampler(sampler))
    }
  }
}
await io.write(output, doc)
console.log('wrote', output)
