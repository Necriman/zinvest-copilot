// Reports which way a paw's palm faces once the rest pose is applied, so the
// hand twist in engine.js is measured instead of guessed.
//
// The paw is a flattened shape: its flattest direction is the palm normal. The
// script finds it from the vertices skinned to the hand bone, then walks it
// through the arm and forearm rotations and prints, for each twist, how much
// the palm ends up pointing at the torso (1 = straight at it).
//
//   node palm.mjs <model.glb> [RightHand|LeftHand]   (needs @gltf-transform/*)
// Which way does the paw's palm face, and what twist turns it toward the torso?
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'

const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
const doc = await io.read(process.argv[2])
const skin = doc.getRoot().listSkins()[0]
const joints = skin.listJoints()
const name = (j) => j.getName().replace('mixamorig:', '')
const HAND = process.argv[3] || 'RightHand'          // code armL is the model's RightArm
const handIndex = joints.findIndex((j) => name(j) === HAND)
const hand = joints[handIndex]
const M = hand.getWorldMatrix()

const prim = doc.getRoot().listMeshes()[0].listPrimitives()[0]
const POS = prim.getAttribute('POSITION'), J = prim.getAttribute('JOINTS_0'), W = prim.getAttribute('WEIGHTS_0')
const pts = []
const p = [], jj = [], ww = []
for (let i = 0; i < POS.getCount(); i++) {
  J.getElement(i, jj); W.getElement(i, ww)
  let w = 0
  for (let k = 0; k < 4; k++) if (jj[k] === handIndex) w += ww[k]
  if (w > 0.6) { POS.getElement(i, p); pts.push([p[0], p[1], p[2]]) }
}
if (!pts.length) throw new Error('no vertices on ' + HAND)

// centre, then the covariance's smallest eigenvector = the flat direction
const c = [0, 1, 2].map((a) => pts.reduce((s, q) => s + q[a], 0) / pts.length)
const cov = [[0,0,0],[0,0,0],[0,0,0]]
for (const q of pts) { const d = [q[0]-c[0], q[1]-c[1], q[2]-c[2]]
  for (let a = 0; a < 3; a++) for (let b = 0; b < 3; b++) cov[a][b] += d[a] * d[b] }
// power iteration on the inverse-ish: find the eigenvector with the smallest eigenvalue
// by deflating with the two largest.
const mul = (m, v) => [0,1,2].map((a) => m[a][0]*v[0] + m[a][1]*v[1] + m[a][2]*v[2])
const norm = (v) => { const n = Math.hypot(...v); return v.map((x) => x / n) }
const dot = (a, b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
function largest(m) { let v = norm([0.3, 0.7, 0.21]); for (let i = 0; i < 300; i++) v = norm(mul(m, v)); return v }
function deflate(m, v) { const l = dot(v, mul(m, v)); return m.map((row, a) => row.map((x, b) => x - l * v[a] * v[b])) }
const e1 = largest(cov)
const e2 = largest(deflate(cov, e1))
const e3 = norm([e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2], e1[0]*e2[1]-e1[1]*e2[0]])
const spread = (v) => { const xs = pts.map((q) => dot([q[0]-c[0], q[1]-c[1], q[2]-c[2]], v)); return Math.max(...xs) - Math.min(...xs) }
console.log(`${HAND}: ${pts.length} vertices, centre ${c.map((n) => n.toFixed(3)).join(', ')}`)
console.log(`  axis1 ${e1.map((n) => n.toFixed(2)).join(',')}  spread ${spread(e1).toFixed(3)}`)
console.log(`  axis2 ${e2.map((n) => n.toFixed(2)).join(',')}  spread ${spread(e2).toFixed(3)}`)
console.log(`  axis3 ${e3.map((n) => n.toFixed(2)).join(',')}  spread ${spread(e3).toFixed(3)}  <- flattest = palm normal`)

// Rest-pose palm normal, pointed away from the body (+x is the torso side for the left arm)
let n0 = e3
const toTorso = c[0] < 0 ? 1 : -1                 // the torso lies this way in x
console.log(`  torso is at ${toTorso > 0 ? '+x' : '-x'} from this paw`)

// Apply the pose chain: arm and forearm turn about model z, the hand about model y.
const deg = Math.PI / 180
const rotZ = (v, a) => [v[0]*Math.cos(a) - v[1]*Math.sin(a), v[0]*Math.sin(a) + v[1]*Math.cos(a), v[2]]
const rotY = (v, a) => [v[0]*Math.cos(a) + v[2]*Math.sin(a), v[1], -v[0]*Math.sin(a) + v[2]*Math.cos(a)]
const A_POSE = { armL: 37.5 * deg, foreL: 53.8 * deg }
const REST_OUT = 13 * deg, FORE_KEEP = 0.35
const armZ = A_POSE.armL - REST_OUT
const foreZ = -((A_POSE.foreL - A_POSE.armL) * (FORE_KEEP - 1))
console.log(`\n  pose: arm z ${(armZ/deg).toFixed(1)}째, forearm z ${(foreZ/deg).toFixed(1)}째`)
console.log('  twist   palm points (x,y,z)      toward torso')
for (const t of [-180, -135, -90, -45, 0, 45, 90, 135, 180]) {
  const v = rotZ(rotZ(rotY(n0, t * deg), foreZ), armZ)
  console.log(`   ${String(t).padStart(5)}째  ${v.map((n) => n.toFixed(2).padStart(6)).join(' ')}   ${(v[0] * toTorso).toFixed(2).padStart(6)}`)
}
