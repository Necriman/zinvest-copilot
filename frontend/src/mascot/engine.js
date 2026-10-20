/**
 * The live Zinvest bear: loads the model once per page, then drives one small
 * three.js scene per <BearMascot> with moods (steady behaviours such as idle,
 * talk, celebrate) and reactions (short one-shots such as a hop or a spin).
 *
 * The body moves on its skeleton (./rig.js has the face and the arrow), and
 * every mood is just a function of time that writes a pose. Moods blend into
 * each other and reactions layer on top, which keeps every transition smooth.
 */
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js'
import { clone as cloneSkinned } from 'three/addons/utils/SkeletonUtils.js'

import { MODEL } from './models'
import { PLACE_BLINKS, placeMoods } from './places'
import { FIT, applyRig, makeRigUniforms, prepareModel } from './rig'

export const MODEL_URL = MODEL.url

let assetPromise = null
export function loadBearAsset() {
  if (!assetPromise) {
    assetPromise = new GLTFLoader()
      .setMeshoptDecoder(MeshoptDecoder)
      .loadAsync(MODEL_URL)
      .then((gltf) => {
        prepareModel(gltf.scene)
        return { scene: gltf.scene, clips: gltf.animations }
      })
      .catch((e) => {
        assetPromise = null // allow a retry on the next mount
        throw e
      })
  }
  return assetPromise
}

// ---------------------------------------------------------------------------
// Poses. Angles are [x, y, z] in radians, rotations about the model's own axes
// as they are in the rest (A-)pose, applied in YXZ order at the joint. Arms:
// armR is the arm on the viewer's right. z raises an arm out to its side
// (positive for armR, negative for armL), x swings it forward (negative) and y
// turns it inwards (negative for armR). The forearm and hand angles work the
// same way, on top of the upper arm. body bends the spine, head turns the head.
const deg = Math.PI / 180

// Where each arm starts in the model's A-pose, measured from straight down with
// scripts/mascot/arms.mjs. Meshy's auto-rig is not symmetric, so one rest angle
// for both arms leaves one of them pinned against the belly — which reads as a
// bashful bear rather than a relaxed one. Re-measure when the model changes.
const A_POSE = Object.fromEntries(Object.entries(MODEL.aPose).map(([k, v]) => [k, v * deg]))
// How far the arms hang clear of the body at rest, and how much of the forearm's
// extra splay to keep: with none of it the arms look like sticks.
const REST_OUT = 13 * deg
// Bend the elbows slightly and turn the palms inward around each forearm's
// own axis. Model-Y rotations bend the angled A-pose wrists sideways.
const FORE_KEEP = 0.35

const restArm = (side) => A_POSE[side] - REST_OUT
// The forearm inherits the upper arm's turn, so it only needs the difference.
const restFore = (arm, fore) => (A_POSE[fore] - A_POSE[arm]) * (FORE_KEEP - 1)

export function neutralPose() {
  return {
    head: [0, 0, 0], body: [0, 0, 0],
    armL: [0, 0, restArm('armL')], armR: [0, 0, -restArm('armR')],
    foreL: [-14 * deg, 0, -restFore('armL', 'foreL')], foreR: [-14 * deg, 0, restFore('armR', 'foreR')],
    handL: [0, 0, 0], handR: [0, 0, 0],
    handTwistL: -40 * deg, handTwistR: 40 * deg,
    arrowSpin: 0, arrowBob: 0, arrowScale: 1,
    squash: 1, lean: 0, brow: 0, crouch: 0,
    eyeClose: 0, eyeHappy: 0, winkL: 0, winkR: 0, mouth: 0,
    hop: 0, turn: 0,
  }
}

const KEYS = Object.keys(neutralPose())

// Mirror an arm angle from the viewer's right arm to the left one.
const mirror = (a) => [a[0], -a[1], -a[2]]

function breathe(t, p, amount = 1) {
  const s = Math.sin(t * 1.7)
  p.squash = 1 + 0.009 * amount * s
  p.head[2] += 0.03 * amount * Math.sin(t * 0.7)
  p.head[0] += 0.02 * amount * Math.sin(t * 0.9 + 1)
  p.armR[2] += (2 + 2.5 * amount * s) * deg
  p.armL[2] -= (2 + 2.5 * amount * s) * deg
  p.armR[0] += 3 * amount * Math.sin(t * 0.9 + 1.4) * deg
  p.armL[0] += 3 * amount * Math.sin(t * 0.9) * deg
  p.arrowBob += 0.014 * amount * Math.sin(t * 2.1)
  p.arrowSpin += 0.22 * amount * Math.sin(t * 0.8)
}

// Each mood writes into a neutral pose. `t` is seconds since the mood started.
export const MOODS = {
  idle(t, p) { breathe(t, p) },
  wave(t, p) {
    breathe(t, p, 0.6)
    const w = Math.sin(t * 9)
    // The paw has to end out to the side, not beside the ear: a wave folded
    // in against the head reads as a shy one.
    p.armR = [-15 * deg, 0, 58 * deg]
    p.foreR = [0, 0, (50 + 20 * w) * deg]
    p.handR = [0, 0, 10 * w * deg]
    p.handTwistR = 0 // open palm toward the viewer
    p.head[2] += -5 * deg + 1.5 * deg * Math.sin(t * 4.5)
    p.brow = 0.5
    p.mouth = 0.35
    p.lean = -1.5 * deg
  },
  talk(t, p) {
    breathe(t, p, 0.7)
    const g = Math.sin(t * 2.6)
    p.mouth = 0.18 + 0.5 * Math.abs(Math.sin(t * 10.5)) * (0.65 + 0.35 * Math.sin(t * 3.3))
    p.head[0] += 2 * deg * Math.sin(t * 5)
    p.head[2] += 1.5 * deg * Math.sin(t * 2.3)
    p.armR = [(-22 + 8 * g) * deg, -8 * deg, -30 * deg]
    p.foreR = [(-55 + 18 * g) * deg, 0, 10 * deg]
    p.foreL[0] += (-12 + 6 * Math.sin(t * 2.2 + 1)) * deg
    p.brow = 0.25 + 0.2 * Math.max(0, Math.sin(t * 1.9))
  },
  think(t, p) {
    breathe(t, p, 0.5)
    p.head[2] += 8 * deg
    p.head[0] += -6 * deg
    p.head[1] += 7 * deg
    p.armL = [-95 * deg, 50 * deg, 10 * deg] // paw at the cheek
    p.foreL = [-70 * deg, 20 * deg, 0]
    p.handTwistL = 0 // keep the paw against the cheek
    p.armR = [-18 * deg, -20 * deg, -34 * deg]
    p.foreR = [-60 * deg, 0, 0]
    p.brow = 0.6
    // a slow sway while he thinks; a full turn would point it backwards
    p.arrowSpin = 0.35 * Math.sin(t * 1.2)
  },
  listen(t, p) {
    breathe(t, p, 0.8)
    p.head[2] += 6 * deg + 1.5 * deg * Math.sin(t * 1.3)
    p.armL[0] += -12 * deg
    p.armR[0] += -12 * deg
    p.foreL[0] += -20 * deg
    p.foreR[0] += -20 * deg
    p.brow = 0.35
  },
  happy(t, p) {
    const b = Math.abs(Math.sin(t * 5))
    const lag = Math.abs(Math.sin(t * 5 - 0.5)) // arms follow the body a beat late
    breathe(t, p, 0.4)
    p.hop = 0.05 * b
    p.squash = 1 - 0.02 * (1 - b)
    p.eyeHappy = 1
    p.mouth = 0.6
    p.armR = [-8 * deg, 0, (-12 + 30 * lag) * deg]
    p.armL = mirror(p.armR)
    p.foreR = [0, 0, (20 + 15 * lag) * deg]
    p.foreL = mirror(p.foreR)
    p.brow = 0.5
  },
  celebrate(t, p) {
    const c = (t % 0.9) / 0.9
    const h = 4 * c * (1 - c)
    const cl = (c + 0.92) % 1 // arms lag the jump slightly
    const hl = 4 * cl * (1 - cl)
    p.hop = 0.2 * h
    p.squash = c < 0.1 || c > 0.94 ? 0.93 : 1 + 0.03 * h
    p.crouch = c < 0.1 || c > 0.94 ? 0.6 : 0
    p.armR = [-10 * deg, 0, (35 + 60 * hl) * deg]
    p.armL = mirror(p.armR)
    p.foreR = [0, 0, (40 - 20 * hl) * deg]
    p.foreL = mirror(p.foreR)
    p.head[0] = -5 * deg * h
    p.eyeHappy = 1
    p.mouth = 0.85
    p.brow = 0.8
    p.arrowSpin = t * 7
    p.arrowScale = 1.08 + 0.12 * h
    p.arrowBob = 0.05 * h
  },
  clap(t, p) {
    breathe(t, p, 0.3)
    p.handTwistL = p.handTwistR = 0 // palms face one another
    const s = Math.max(0, Math.sin(t * 13))
    p.turn = 0.28
    p.armR = [-70 * deg, (-35 + 10 * s) * deg, -30 * deg]
    p.armL = mirror(p.armR)
    p.foreR = [0, (-25 + 10 * s) * deg, 0]
    p.foreL = mirror(p.foreR)
    p.hop = 0.02 * Math.abs(Math.sin(t * 6.5))
    p.eyeHappy = 1
    p.mouth = 0.65
    p.brow = 0.5
  },
  cheer(t, p) {
    breathe(t, p, 0.4)
    const s = Math.sin(t * 7)
    p.armR = [-12 * deg, 0, (70 + 12 * s) * deg]
    p.foreR = [0, 0, (55 - 15 * s) * deg]
    p.hop = 0.03 * Math.max(0, s)
    p.head[2] += -4 * deg
    p.mouth = 0.7
    p.brow = 0.7
  },
  confused(t, p) {
    breathe(t, p, 0.5)
    p.head[2] += -12 * deg + 2 * deg * Math.sin(t * 1.4)
    p.head[0] += 3 * deg
    p.brow = 0.9
    p.armR = [-30 * deg, 0, -18 * deg]
    p.foreR = [-55 * deg, 0, 25 * deg]
    p.armL = mirror(p.armR)
    p.foreL = mirror(p.foreR)
    p.lean = 2 * deg
    p.arrowSpin = 0.5 * Math.sin(t * 2)
  },
  sleep(t, p) {
    p.squash = 1 + 0.018 * Math.sin(t * 1.1)
    p.head = [14 * deg, 0, -7 * deg + 1 * deg * Math.sin(t * 1.1)]
    p.body = [6 * deg, 0, 0]
    p.armR[2] += -3 * deg
    p.armL[2] += 3 * deg
    p.eyeClose = 1
    p.arrowBob = -0.035 + 0.01 * Math.sin(t * 1.1)
    p.arrowScale = 0.92
  },
}

// One gesture per place on the site (hero, demo, sign-in...), see ./places.js.
Object.assign(MOODS, placeMoods({ breathe, mirror }))

// Moods that keep the eyes open get natural blinks.
const BLINKS = new Set(['idle', 'wave', 'talk', 'think', 'listen', 'cheer', 'confused', ...PLACE_BLINKS])

// Reactions: short additive one-shots. f(u) with u in 0..1 over `duration`.
export const REACTIONS = {
  hop: { duration: 0.55, f: (u, p) => { const h = 4 * u * (1 - u); p.hop += 0.14 * h; p.squash *= u < 0.12 || u > 0.9 ? 0.95 : 1; p.crouch = Math.max(p.crouch, u < 0.12 || u > 0.9 ? 0.5 : 0); p.eyeHappy = Math.max(p.eyeHappy, 1); p.armR[2] += 40 * deg * h; p.armL[2] -= 40 * deg * h } },
  spin: { duration: 0.9, f: (u, p) => { const e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2; const s = Math.sin(Math.PI * u); p.turn += e * Math.PI * 2; p.hop += 0.06 * s; p.eyeHappy = 1; p.armR[2] += 55 * deg * s; p.armL[2] -= 55 * deg * s } },
  nod: { duration: 0.7, f: (u, p) => { p.head[0] += 10 * deg * Math.sin(u * Math.PI * 2) * (1 - u); p.mouth = Math.max(p.mouth, 0.3) } },
  wink: { duration: 0.6, f: (u, p) => { const s = Math.sin(Math.PI * u); p.winkR = Math.sin(Math.PI * Math.min(1, u * 1.4)); p.head[2] += 5 * deg * s; p.mouth = Math.max(p.mouth, 0.3); p.armR[2] += 25 * deg * s; p.foreR[2] += 30 * deg * s } },
  flap: { duration: 0.8, f: (u, p) => { const a = Math.abs(Math.sin(u * Math.PI * 4)) * (1 - u); p.armR[2] += 70 * deg * a; p.armL[2] -= 70 * deg * a; p.eyeHappy = 1 } },
  shake: { duration: 0.7, f: (u, p) => { p.head[1] += 12 * deg * Math.sin(u * Math.PI * 4) * (1 - u); p.brow = Math.max(p.brow, 0.8) } },
}

function blendPose(a, b, k, out) {
  for (const key of KEYS) {
    const va = a[key], vb = b[key]
    if (Array.isArray(va)) out[key] = [0, 1, 2].map((i) => va[i] + (vb[i] - va[i]) * k)
    else out[key] = va + (vb - va) * k
  }
  return out
}

const ease = (x) => x * x * (3 - 2 * x)

// ---------------------------------------------------------------------------
// Skeleton
const BONES = {
  hips: 'Hips', spine: 'Spine', spine1: 'Spine1', spine2: 'Spine2', neck: 'Neck', head: 'Head',
  armR: 'LeftArm', foreR: 'LeftForeArm', handR: 'LeftHand',
  armL: 'RightArm', foreL: 'RightForeArm', handL: 'RightHand',
  thighR: 'LeftUpLeg', shinR: 'LeftLeg', footR: 'LeftFoot',
  thighL: 'RightUpLeg', shinL: 'RightLeg', footL: 'RightFoot',
}

function rigBones(root) {
  root.updateMatrixWorld(true)
  const byName = {}
  root.traverse((o) => { if (o.isBone) byName[o.name.replace(/^mixamorig:?/, '')] = o })
  const rootInverse = new THREE.Quaternion()
  root.getWorldQuaternion(rootInverse).invert()
  const rig = {}
  for (const [key, name] of Object.entries(BONES)) {
    const bone = byName[name]
    if (!bone) throw new Error(`bear model is missing bone ${name}`)
    const world = bone.getWorldQuaternion(new THREE.Quaternion()).premultiply(rootInverse)
    rig[key] = { bone, local: bone.quaternion.clone(), world, worldInverse: world.clone().invert(), position: bone.position.clone() }
  }
  for (const side of ['L', 'R']) {
    const hand = rig[`hand${side}`]
    // The elbow-to-wrist direction in the hand's bind frame. Twisting around
    // this axis preserves the forearm/wrist line in every animated arm pose.
    hand.twistAxis = hand.bone.getWorldPosition(new THREE.Vector3())
      .sub(rig[`fore${side}`].bone.getWorldPosition(new THREE.Vector3()))
      .normalize().applyQuaternion(rootInverse).applyQuaternion(hand.worldInverse)
  }
  return rig
}

const _euler = new THREE.Euler(0, 0, 0, 'YXZ')
const _q = new THREE.Quaternion()
const _q2 = new THREE.Quaternion()
// Turn a bone by [x, y, z] about the model axes as they were at rest.
function turnBone(entry, x, y, z, share = 1) {
  _q.setFromEuler(_euler.set(x * share, y * share, z * share))
  _q2.copy(entry.worldInverse).multiply(_q).multiply(entry.world)
  entry.bone.quaternion.copy(entry.local).multiply(_q2)
}

function twistHand(entry, angle) {
  _q.setFromAxisAngle(entry.twistAxis, angle)
  entry.bone.quaternion.multiply(_q)
}

// ---------------------------------------------------------------------------
// Scene
const FRAMING = {
  // [target y, visible height, visible width]
  full: [0.03, 2.35, 1.5],
  bust: [0.42, 1.15, 1.25],
}

function shadowTexture() {
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const g = c.getContext('2d')
  const grad = g.createRadialGradient(64, 64, 4, 64, 64, 62)
  grad.addColorStop(0, 'rgba(30,42,68,0.34)')
  grad.addColorStop(1, 'rgba(30,42,68,0)')
  g.fillStyle = grad
  g.fillRect(0, 0, 128, 128)
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  return t
}

/**
 * Creates a live bear inside `host`. Returns a controller:
 *   setMood(name), react(name), setPointer([nx, ny] | null), setVoice(fn | null),
 *   renderOnce(t), dispose()
 * `setVoice` takes a function returning the loudness of the bear's voice
 * (0..1) right now; the mouth follows it instead of the talking loop.
 * `options.onReady()` fires once the first frame is on screen.
 */
export async function createBear(host, options = {}) {
  const { framing = 'full', mood = 'idle', still = false, onReady } = options
  const base = await loadBearAsset()

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'low-power', preserveDrawingBuffer: !!options.preserveDrawingBuffer })
  renderer.setClearColor(0x000000, 0)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.05
  const canvas = renderer.domElement
  canvas.setAttribute('aria-hidden', 'true')
  Object.assign(canvas.style, { display: 'block', width: '100%', height: '100%' })
  host.appendChild(canvas)

  const scene = new THREE.Scene()
  scene.add(new THREE.HemisphereLight(0xffffff, 0xb9c3d8, 2.3))
  const key = new THREE.DirectionalLight(0xffffff, 2.1)
  key.position.set(-2, 3, 4)
  scene.add(key)
  const rim = new THREE.DirectionalLight(0xdbe6ff, 1.2)
  rim.position.set(3, 2, -3)
  scene.add(rim)

  // One skeleton per bear; geometry and textures stay shared.
  const bear = cloneSkinned(base.scene)
  const uniforms = makeRigUniforms()
  const materials = []
  bear.traverse((o) => {
    if (!o.isSkinnedMesh) return
    o.frustumCulled = false
    o.material = o.material.clone()
    applyRig(o.material, uniforms)
    materials.push(o.material)
  })
  const bones = rigBones(bear)

  const shadowTex = shadowTexture()
  const shadow = new THREE.Mesh(
    new THREE.PlaneGeometry(1.25, 0.55),
    new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false }),
  )
  shadow.rotation.x = -Math.PI / 2
  shadow.position.y = FIT.feetY + 0.002

  // root (hop, turn) > squash (scale and lean around the feet) > body frame
  // (origin at the model's centre, where props are placed) > the rigged bear
  const root = new THREE.Group()
  const squashGroup = new THREE.Group()
  squashGroup.position.y = FIT.feetY
  const model = new THREE.Group()
  model.position.y = -FIT.feetY
  squashGroup.add(model)
  root.add(squashGroup)
  bear.scale.setScalar(FIT.scale)
  bear.position.set(FIT.x, FIT.feetY, 0)
  model.add(bear)
  scene.add(root, shadow)
  for (const prop of options.props || []) model.add(prop)

  const camera = new THREE.PerspectiveCamera(26, 1, 0.1, 30)
  function frame(width, height) {
    const [ty, vh, vw] = FRAMING[framing] || FRAMING.full
    camera.aspect = width / height
    const halfV = Math.tan((camera.fov * deg) / 2)
    const dist = Math.max(vh / 2 / halfV, vw / 2 / (halfV * camera.aspect))
    camera.position.set(0, ty + 0.08, dist)
    camera.lookAt(0, ty, 0)
    camera.updateProjectionMatrix()
  }

  let width = 0, height = 0
  function resize() {
    const rect = host.getBoundingClientRect()
    const w = Math.max(1, Math.round(rect.width)), h = Math.max(1, Math.round(rect.height))
    if (w === width && h === height) return false
    width = w; height = h
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.setSize(w, h, false)
    frame(w, h)
    return true
  }

  // --- animation state
  let current = { name: mood, start: 0 }
  let previous = null
  let blendStart = -1
  const reactions = []
  let nextBlink = 1.5 + Math.random() * 2.5
  let pointer = null
  let voice = null
  let voiceLevel = 0
  const look = { yaw: 0, pitch: 0 }
  const clockStart = performance.now()
  const now = () => (performance.now() - clockStart) / 1000

  function poseAt(name, t) {
    const p = neutralPose()
    ;(MOODS[name] || MOODS.idle)(Math.max(0, t), p)
    return p
  }

  function computePose(t, dt) {
    let pose = poseAt(current.name, t - current.start)
    if (previous && blendStart >= 0) {
      const k = Math.min(1, (t - blendStart) / 0.35)
      pose = blendPose(poseAt(previous.name, t - previous.start), pose, ease(k), neutralPose())
      if (k >= 1) previous = null
    }
    for (let i = reactions.length - 1; i >= 0; i--) {
      const r = reactions[i]
      const u = (t - r.start) / r.def.duration
      if (u >= 1) { reactions.splice(i, 1); continue }
      r.def.f(Math.max(0, u), pose)
    }
    if (BLINKS.has(current.name) && pose.eyeHappy < 0.5) {
      if (t > nextBlink + 0.16) nextBlink = t + 2.2 + Math.random() * 3.8
      else if (t > nextBlink) pose.eyeClose = Math.max(pose.eyeClose, Math.sin(((t - nextBlink) / 0.16) * Math.PI))
    }
    // A real voice drives the mouth: quick to open, a little slower to close.
    if (voice) {
      const target = Math.max(0, Math.min(1, Number(voice()) || 0))
      const k = 1 - Math.pow(target > voiceLevel ? 0.0005 : 0.02, dt)
      voiceLevel += (target - voiceLevel) * k
      pose.mouth = Math.max(pose.mouth * 0.15, voiceLevel * 0.95)
    } else {
      voiceLevel = 0
    }
    // Follow the pointer with the head, a little with the body.
    const k = 1 - Math.pow(0.001, dt)
    look.yaw += ((pointer ? pointer[0] * 0.45 : 0) - look.yaw) * k
    look.pitch += ((pointer ? pointer[1] * 0.18 : 0) - look.pitch) * k
    pose.head[1] += look.yaw * 0.75
    pose.head[0] += look.pitch
    pose.turn += look.yaw * 0.3
    return pose
  }

  function apply(pose) {
    const b = bones
    turnBone(b.neck, pose.head[0], pose.head[1], pose.head[2], 0.35)
    turnBone(b.head, pose.head[0], pose.head[1], pose.head[2], 0.65)
    turnBone(b.spine, pose.body[0], pose.body[1], pose.body[2], 0.3)
    turnBone(b.spine1, pose.body[0], pose.body[1], pose.body[2], 0.35)
    turnBone(b.spine2, pose.body[0], pose.body[1], pose.body[2], 0.35)
    turnBone(b.armR, ...pose.armR)
    turnBone(b.foreR, ...pose.foreR)
    turnBone(b.handR, ...pose.handR)
    turnBone(b.armL, ...pose.armL)
    turnBone(b.foreL, ...pose.foreL)
    turnBone(b.handL, ...pose.handL)
    twistHand(b.handR, pose.handTwistR)
    twistHand(b.handL, pose.handTwistL)
    // Crouch: hips down, knees forward, feet flat.
    const c = Math.max(0, Math.min(1, pose.crouch))
    b.hips.bone.position.copy(b.hips.position)
    b.hips.bone.position.y -= 0.035 * c
    for (const side of ['L', 'R']) {
      turnBone(b[`thigh${side}`], -38 * deg * c, 0, 0)
      turnBone(b[`shin${side}`], 64 * deg * c, 0, 0)
      turnBone(b[`foot${side}`], -26 * deg * c, 0, 0)
    }
    const bulge = 1 + (1 / Math.sqrt(Math.max(pose.squash, 0.2)) - 1) * 0.6 // roughly keeps the volume
    squashGroup.scale.set(bulge, pose.squash, bulge)
    squashGroup.rotation.z = pose.lean
    uniforms.uArrow.value.set(pose.arrowSpin, pose.arrowBob / FIT.scale, pose.arrowScale)
    uniforms.uBrow.value = pose.brow
    uniforms.uEyeClose.value = Math.min(1, pose.eyeClose)
    uniforms.uEyeHappy.value = Math.min(1, pose.eyeHappy)
    uniforms.uWinkL.value = Math.min(1, pose.winkL)
    uniforms.uWinkR.value = Math.min(1, pose.winkR)
    uniforms.uMouth.value = Math.min(1, pose.mouth)
    root.position.y = pose.hop
    root.rotation.y = pose.turn
    const s = 1 - Math.min(0.35, pose.hop * 1.6)
    shadow.scale.set(s, s, s)
    shadow.material.opacity = s
  }

  // --- loop: 60fps while something moves, about 30fps when only breathing
  let raf = 0, last = 0, visible = true, disposed = false, readyFired = false
  const busy = () => reactions.length > 0 || previous !== null || voice !== null || !['idle', 'sleep', 'listen', 'think'].includes(current.name) || pointer !== null
  function tick(ms) {
    raf = 0
    if (disposed) return
    const elapsedMs = ms - last
    if (!busy() && elapsedMs < 32) { schedule(); return }
    const dt = Math.min(0.1, elapsedMs / 1000 || 0.016)
    last = ms
    resize()
    apply(computePose(now(), dt))
    renderer.render(scene, camera)
    if (!readyFired) { readyFired = true; onReady?.() }
    schedule()
  }
  function schedule() {
    if (!raf && !disposed && !still && visible && !document.hidden) raf = requestAnimationFrame(tick)
  }
  function renderOnce(t = 0.4) {
    resize()
    apply(computePose(t, 0.016))
    renderer.render(scene, camera)
    if (!readyFired) { readyFired = true; onReady?.() }
  }

  const io = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; schedule() })
  io.observe(host)
  const ro = new ResizeObserver(() => { if (resize() && (still || !raf)) renderOnce(still ? 0.4 : now()) })
  ro.observe(host)
  const onVisibility = () => schedule()
  document.addEventListener('visibilitychange', onVisibility)
  canvas.addEventListener('webglcontextlost', (e) => { e.preventDefault(); options.onError?.(new Error('context lost')) })

  if (still) renderOnce()
  else schedule()

  return {
    canvas,
    setMood(name) {
      if (!MOODS[name] || name === current.name) return
      const t = now()
      previous = current
      blendStart = t
      current = { name, start: t }
      if (still) renderOnce(0.4)
      else schedule()
    },
    react(name) {
      const def = REACTIONS[name]
      if (!def || still) return
      reactions.push({ def, start: now() })
      schedule()
    },
    setPointer(xy) {
      pointer = xy
      schedule()
    },
    setVoice(fn) {
      voice = typeof fn === 'function' ? fn : null
      schedule()
    },
    renderOnce,
    dispose() {
      disposed = true
      cancelAnimationFrame(raf)
      io.disconnect()
      ro.disconnect()
      document.removeEventListener('visibilitychange', onVisibility)
      for (const m of materials) m.dispose()
      shadow.geometry.dispose()
      shadow.material.dispose()
      shadowTex.dispose()
      renderer.dispose()
      renderer.forceContextLoss()
      canvas.remove()
    },
  }
}
