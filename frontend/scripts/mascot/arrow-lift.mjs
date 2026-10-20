// The floating growth arrow is its own piece of the mesh. The site's shader
// finds it by height ("everything above arrowY"), which needs clear air between
// the ears and the arrow. This finds the arrow by connectivity and lifts it
// until there is a gap, then prints the numbers rig.js needs.
//   node arrow-lift.mjs in.glb out.glb [gap]
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'

const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
const [input, output, gapArg = '0.02'] = process.argv.slice(2)
const GAP = Number(gapArg)
const doc = await io.read(input)
const prim = doc.getRoot().listMeshes()[0].listPrimitives()[0]
const POS = prim.getAttribute('POSITION')
const IDX = prim.getIndices()
const N = POS.getCount()
const pos = new Float32Array(N * 3)
{ const p = []; for (let i = 0; i < N; i++) { POS.getElement(i, p); pos.set(p, i * 3) } }

// weld by position so UV seams do not split a shell
const key = new Map()
const weld = new Int32Array(N)
for (let i = 0; i < N; i++) {
  const k = `${Math.round(pos[i * 3] * 1e5)},${Math.round(pos[i * 3 + 1] * 1e5)},${Math.round(pos[i * 3 + 2] * 1e5)}`
  if (!key.has(k)) key.set(k, key.size)
  weld[i] = key.get(k)
}
// union-find over triangles
const parent = new Int32Array(key.size).map((_, i) => i)
const find = (a) => { while (parent[a] !== a) { parent[a] = parent[parent[a]]; a = parent[a] } return a }
const unite = (a, b) => { a = find(a); b = find(b); if (a !== b) parent[a] = b }
const idx = IDX.getArray()
for (let t = 0; t < idx.length; t += 3) {
  unite(weld[idx[t]], weld[idx[t + 1]])
  unite(weld[idx[t]], weld[idx[t + 2]])
}
const shells = new Map()
for (let i = 0; i < N; i++) {
  const r = find(weld[i])
  if (!shells.has(r)) shells.set(r, { verts: [], minY: 9, maxY: -9 })
  const s = shells.get(r)
  s.verts.push(i)
  s.minY = Math.min(s.minY, pos[i * 3 + 1])
  s.maxY = Math.max(s.maxY, pos[i * 3 + 1])
}
const list = [...shells.values()].sort((a, b) => b.verts.length - a.verts.length)
console.log('shells', list.length, list.slice(0, 8).map((s) => `${s.verts.length}v y${s.minY.toFixed(3)}..${s.maxY.toFixed(3)}`).join(' | '))

// The arrow: shells that float entirely above the shoulders' height of the head.
const arrow = list.filter((s) => s.minY > 1.45)
const rest = list.filter((s) => s.minY <= 1.45)
const arrowMin = Math.min(...arrow.map((s) => s.minY))
const bodyMax = Math.max(...rest.map((s) => s.maxY))
console.log('arrow shells', arrow.length, 'verts', arrow.reduce((n, s) => n + s.verts.length, 0), 'arrow bottom', arrowMin.toFixed(3), 'top of the rest', bodyMax.toFixed(3))
const lift = Math.max(0, bodyMax + GAP - arrowMin)
const arrowVerts = new Set(arrow.flatMap((s) => s.verts))
if (lift > 0) {
  const p = []
  for (const i of arrowVerts) { POS.getElement(i, p); p[1] += lift; POS.setElement(i, p) }
}
// the numbers for rig.js
let lo = [9, 9, 9], hi = [-9, -9, -9]
{ const p = []; for (const i of arrowVerts) { POS.getElement(i, p); for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], p[k]); hi[k] = Math.max(hi[k], p[k]) } } }
console.log('lifted by', lift.toFixed(3))
console.log('arrowY (halfway through the gap)', ((bodyMax + lo[1]) / 2).toFixed(3))
console.log('arrow centre', [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2].map((v) => v.toFixed(3)))
console.log('model top', hi[1].toFixed(3))
await io.write(output, doc)
console.log('wrote', output)
