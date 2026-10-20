/**
 * Rig for the Zinvest bear.
 *
 * The model (the one ./models.js selects) is a Meshy mascot in an A-pose with
 * a Mixamo skeleton. Meshy's own skin weights glue the upper arms
 * to the head, so scripts/mascot/reskin.mjs repaints them before the GLB is
 * compressed (see the script for how). The engine turns bones for the body,
 * head, arms and legs; this file adds what the skeleton cannot do, as a shader
 * on the one skinned mesh: the growth arrow spinning and bobbing, the brows
 * lifting (the brow texture is shifted upwards, or, where the brows are bumps
 * in the mesh, their vertices are moved), closed, happy and winking eyes
 * and an open mouth drawn over the face. All of it works on the rest-pose
 * position, before skinning, so it follows the head wherever the bones take it.
 *
 * Landmarks are in the model's own frame: feet at y = 0, facing +z, and they
 * live in ./models.js next to the file they belong to. Re-measure whenever the
 * model is rebuilt — v6 sat about 0.02 further left than v5 did, and a shader
 * eye drawn on the last model's numbers lands beside the painted one. They come
 * from scripts/mascot/measure.html, which finds the painted shapes in the
 * render rather than asking anyone to read them off a grid.
 */
import * as THREE from 'three'

import { MODEL } from './models'

// The model's own numbers (see ./models.js for what each one means).
export const LANDMARKS = MODEL.landmarks

// How far the brows can travel, in model units (see ./models.js).
const BROW_LIFT = MODEL.browLift
// Where the brows are bumps in the mesh, their vertices move; otherwise the
// painted brows are lifted by shifting the texture.
const BROW_MESH = MODEL.browMesh

/**
 * How the model sits in the scene: the same frame the stickers, props and
 * camera framings were designed for (1.903 tall with the arrow, feet at -0.952,
 * centred on the face).
 */
export const FIT = { scale: 1.903 / MODEL.height, x: -MODEL.faceX * (1.903 / MODEL.height), feetY: -0.952 }

const v3 = (a) => `vec3(${a.map((n) => n.toFixed(4)).join(',')})`
const v2 = (a) => `vec2(${a.map((n) => n.toFixed(4)).join(',')})`
const L = LANDMARKS

const VERTEX_PARS = /* glsl */ `
uniform vec3 uArrow;   // x: spin, y: bob, z: scale
uniform float uBrow;
varying vec3 vRest;
mat3 zbRotY(float a){float c=cos(a),s=sin(a);return mat3(c,0.,-s,0.,1.,0.,s,0.,c);}
`

const VERTEX_NORMAL = /* glsl */ `
vec3 objectNormal = vec3( normal );
float zbArrowN = smoothstep(${(L.arrowY - 0.003).toFixed(3)}, ${(L.arrowY + 0.005).toFixed(3)}, position.y);
if (zbArrowN > 0.0) objectNormal = normalize(mix(objectNormal, zbRotY(uArrow.x) * objectNormal, zbArrowN));
#ifdef USE_TANGENT
vec3 objectTangent = vec3( tangent.xyz );
#endif
`

const VERTEX_POSITION = /* glsl */ `
vRest = position;
vec3 transformed = vec3( position );
float zbArrow = smoothstep(${(L.arrowY - 0.003).toFixed(3)}, ${(L.arrowY + 0.005).toFixed(3)}, position.y);
if (zbArrow > 0.0) {
  vec3 c = ${v3(L.arrow)};
  transformed = mix(transformed, c + zbRotY(uArrow.x) * (transformed - c) * uArrow.z + vec3(0.0, uArrow.y, 0.0), zbArrow);
}
${BROW_MESH ? browMeshLift(BROW_MESH) : ''}`

// The brow bumps move up whole, and the fur between them and the frame
// stretches; the weight is 0 at the frame's top edge, so the glasses stay put.
function browMeshLift(b) {
  const f = (n) => n.toFixed(4)
  return /* glsl */ `
if (uBrow > 0.001 && position.y > ${f(b.rim)} && position.y < ${f(b.fade)}) {
  float zbDx = min(abs(position.x - ${f(L.browL[0])}), abs(position.x - ${f(L.browR[0])}));
  float zbW = (1.0 - smoothstep(${f(b.halfWidth)}, ${f(b.halfWidth + 0.03)}, zbDx))
    * smoothstep(${f(b.rim)}, ${f(b.bottom)}, position.y)
    * (1.0 - smoothstep(${f(b.top)}, ${f(b.fade)}, position.y))
    * smoothstep(0.1, 0.18, position.z);
  transformed.y += uBrow * ${f(BROW_LIFT)} * zbW;
}
`
}

const FRAGMENT_PARS = /* glsl */ `
uniform float uBrow;
uniform float uEyeClose;
uniform float uEyeHappy;
uniform float uWinkL;
uniform float uWinkR;
uniform float uMouth;
varying vec3 vRest;
float zbArc(vec2 p, vec2 c, float r, float w, float up) {
  vec2 d = p - c;
  float ring = abs(length(d) - r);
  float side = up > 0.5 ? step(0.0, d.y) : step(d.y, 0.0);
  return (1.0 - smoothstep(w * 0.55, w, ring)) * side * (1.0 - smoothstep(r * 0.92, r * 1.02, abs(d.x)));
}
float zbBrowMask(vec3 p) {
  if (p.z < 0.1) return 0.0;
  float l = length((p.xy - ${v2(L.browL)}) / vec2(0.09, 0.05));
  float r = length((p.xy - ${v2(L.browR)}) / vec2(0.09, 0.05));
  return (1.0 - smoothstep(0.6, 1.0, min(l, r))) * smoothstep(${(L.rimTop + 0.002).toFixed(3)}, ${(L.rimTop + 0.014).toFixed(3)}, p.y);
}
`

// Replaces <map_fragment>: the brow region samples the texture a little lower,
// which lifts the painted brows. The shift is converted from model units to
// texture units with the screen-space derivatives of both.
const FRAGMENT_MAP = /* glsl */ `
#ifdef USE_MAP
  vec2 zbUv = vMapUv;
  if (${BROW_MESH ? 'false' : 'uBrow > 0.001'}) {
    float wb = zbBrowMask(vRest);
    if (wb > 0.0) {
      mat2 zbDr = mat2(dFdx(vRest.xy), dFdy(vRest.xy));
      if (abs(determinant(zbDr)) > 1e-14) {
        vec2 zbShift = mat2(dFdx(vMapUv), dFdy(vMapUv)) * inverse(zbDr) * vec2(0.0, uBrow * ${BROW_LIFT.toFixed(3)} * wb);
        float zbLen = length(zbShift);
        if (zbLen > 0.03) zbShift *= 0.03 / zbLen;
        zbUv -= zbShift;
      }
    }
  }
  vec4 sampledDiffuseColor = texture2D( map, zbUv );
  diffuseColor *= sampledDiffuseColor;
#endif
`

// The eye and mouth shapes were drawn on v6/v7's face; a model whose painted
// face is larger (v8) scales them with faceScale, and the bands they may touch
// follow the model's own eyes and mouth.
const FS = MODEL.faceScale || 1
const f = (n) => n.toFixed(4)
const EYE_Y = (L.eyeL[1] + L.eyeR[1]) / 2

const FRAGMENT_FACE = /* glsl */ `
if (vRest.z > 0.24 && vRest.y > ${f(EYE_Y - 0.086 * FS)} && vRest.y < ${f(EYE_Y + 0.114 * FS)}) {
  vec3 fur = ${v3(MODEL.fur || [0.905, 0.915, 0.93])};
  vec3 ink = vec3(0.03, 0.035, 0.05);
  for (int i = 0; i < 2; i++) {
    vec2 e = i == 0 ? ${v2(L.eyeL)} : ${v2(L.eyeR)};
    float wink = i == 0 ? uWinkL : uWinkR;
    float amount = max(max(uEyeClose, uEyeHappy), wink);
    if (amount <= 0.001) continue;
    vec2 d = (vRest.xy - e) / vec2(${f(0.056 * FS)}, ${f(0.078 * FS)});
    diffuseColor.rgb = mix(diffuseColor.rgb, fur, (1.0 - smoothstep(0.9, 1.06, length(d))) * amount);
    float happy = wink > 0.5 ? 0.0 : step(uEyeClose + 0.001, uEyeHappy);
    float up = zbArc(vRest.xy, e + vec2(0.0, ${f(-0.034 * FS)}), ${f(0.054 * FS)}, ${f(0.016 * FS)}, 1.0);
    float down = zbArc(vRest.xy, e + vec2(0.0, ${f(0.036 * FS)}), ${f(0.054 * FS)}, ${f(0.016 * FS)}, 0.0);
    diffuseColor.rgb = mix(diffuseColor.rgb, ink, mix(down, up, happy) * amount);
  }
}
if (uMouth > 0.001 && vRest.z > 0.3 && vRest.y > ${f(L.mouth[1] - 0.073 * FS)} && vRest.y < ${f(L.mouth[1] + 0.027 * FS)}) {
  vec2 m = ${v2(L.mouth)};
  vec2 d = (vRest.xy - (m + vec2(0.0, ${f(-0.01 * FS)} * uMouth))) / vec2(${f(0.04 * FS)} + ${f(0.012 * FS)} * uMouth, ${f(0.011 * FS)} + ${f(0.03 * FS)} * uMouth);
  float inside = (1.0 - smoothstep(0.92, 1.0, length(d))) * step(d.y, 0.35);
  float tongue = smoothstep(-0.2, -0.75, d.y) * (1.0 - smoothstep(0.55, 0.9, abs(d.x)));
  diffuseColor.rgb = mix(diffuseColor.rgb, mix(vec3(0.07, 0.07, 0.1), vec3(0.93, 0.45, 0.5), tongue), inside);
}
`

export function makeRigUniforms() {
  return {
    uArrow: { value: new THREE.Vector3(0, 0, 1) },
    uBrow: { value: 0 },
    uEyeClose: { value: 0 },
    uEyeHappy: { value: 0 },
    uWinkL: { value: 0 },
    uWinkR: { value: 0 },
    uMouth: { value: 0 },
  }
}

export function applyRig(material, uniforms) {
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms)
    shader.vertexShader = VERTEX_PARS + shader.vertexShader
      .replace('#include <beginnormal_vertex>', VERTEX_NORMAL)
      .replace('#include <begin_vertex>', VERTEX_POSITION)
    shader.fragmentShader = FRAGMENT_PARS + shader.fragmentShader
      .replace('#include <map_fragment>', FRAGMENT_MAP + FRAGMENT_FACE)
  }
  material.customProgramCacheKey = () => 'zinvest-bear-rig-v4'
  material.needsUpdate = true
}

/**
 * The compressed GLB stores positions quantized, and gltf-transform folds the
 * dequantization into the inverse bind matrices. Undo that once per load, so
 * the shader sees rest positions in model units. Returns the skinned mesh.
 */
export function prepareModel(gltfScene) {
  gltfScene.updateMatrixWorld(true)
  let mesh = null
  gltfScene.traverse((o) => { if (o.isSkinnedMesh && !mesh) mesh = o })
  if (!mesh) throw new Error('bear model has no skinned mesh')
  const skeleton = mesh.skeleton
  // At rest every bone matrix equals the dequantization transform.
  const dequant = new THREE.Matrix4().multiplyMatrices(skeleton.bones[0].matrixWorld, skeleton.boneInverses[0])
  const g = mesh.geometry
  for (const name of ['position', 'normal', 'tangent', 'uv']) {
    const a = g.attributes[name]
    if (!a) continue
    const out = new Float32Array(a.count * a.itemSize)
    for (let i = 0; i < a.count; i++) for (let k = 0; k < a.itemSize; k++) out[i * a.itemSize + k] = a.getComponent(i, k)
    g.setAttribute(name, new THREE.BufferAttribute(out, a.itemSize))
  }
  g.attributes.position.applyMatrix4(dequant)
  const back = dequant.clone().invert()
  for (const m of skeleton.boneInverses) m.multiply(back)
  g.computeBoundingBox()
  g.computeBoundingSphere()
  return mesh
}
