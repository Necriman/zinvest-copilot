// Prints the A-pose arm angles of a rigged export, for REST_ARM in engine.js.
//
// Meshy's auto-rig is not symmetric — the two arms start at different angles
// from straight down — so a single rest angle leaves one arm pinned to the body
// and the other one out. Run this whenever the model is rebuilt and copy the
// numbers into A_POSE.
//
//   node arms.mjs <model.glb>          (needs @gltf-transform/core + /extensions)
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'

const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
const doc = await io.read(process.argv[2])
const skin = doc.getRoot().listSkins()[0]
const joints = skin.listJoints()
const at = (name) => {
  const j = joints.find((n) => n.getName().replace('mixamorig:', '') === name)
  if (!j) throw new Error('missing ' + name)
  const m = j.getWorldMatrix()
  return [m[12], m[13], m[14]]
}
const deg = (r) => (r * 180) / Math.PI
const sub = (a, b) => a.map((v, i) => v - b[i])

for (const side of ['Left', 'Right']) {
  const shoulder = at(side + 'Arm')
  const elbow = at(side + 'ForeArm')
  const hand = at(side + 'Hand')
  const upper = sub(elbow, shoulder)
  const fore = sub(hand, elbow)
  // angle away from straight down, in the frontal plane
  const angle = (v) => deg(Math.atan2(Math.abs(v[0]), -v[1]))
  console.log(
    `${side.padEnd(6)} shoulder ${shoulder.map((n) => n.toFixed(3)).join(', ')}\n` +
    `       upper arm  ${angle(upper).toFixed(1)}° from down   length ${Math.hypot(...upper).toFixed(3)}\n` +
    `       forearm    ${angle(fore).toFixed(1)}° from down   length ${Math.hypot(...fore).toFixed(3)}\n` +
    `       hand at    ${hand.map((n) => n.toFixed(3)).join(', ')}`
  )
}
