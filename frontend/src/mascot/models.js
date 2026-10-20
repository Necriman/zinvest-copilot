/**
 * Everything about the bear that depends on which model file is loaded.
 *
 * The engine turns bones and the rig draws the face and spins the arrow on top
 * of the painted texture, so both need the model's own numbers: where the arms
 * start (scripts/mascot/arms.mjs), where the painted eyes, brows, glasses rim
 * and mouth are and where the floating arrow begins (scripts/mascot/measure.html).
 * All in the model's frame: feet at y = 0, facing +z.
 *
 * Switching models is one line — `MODEL` at the bottom. Keep the old entry
 * until the new one has been looked at in every mood.
 */

export const MODELS = {
  // Meshy mascot, A-pose with straight arms; reskinned by scripts/mascot/reskin.mjs.
  v6: {
    url: '/models/zinvest-bear-v6.glb',
    height: 1.7, // with the arrow
    faceX: -0.006, // the painted face is this far off the model's centre line
    // Upper arms and forearms from straight down, in degrees (arms.mjs).
    aPose: { armR: 46.0, armL: 37.5, foreR: 55.4, foreL: 53.8 },
    landmarks: {
      arrowY: 1.515, // everything above is the floating arrow
      arrow: [-0.008, 1.614, -0.047],
      eyeL: [-0.125, 1.163],
      eyeR: [0.114, 1.161],
      browL: [-0.136, 1.34],
      browR: [0.117, 1.34],
      // Where the top of the glasses rim ends. The brow lift must start above it:
      // anything lower drags the rim up too and the bear looks like he is wincing.
      rimTop: 1.315,
      mouth: [-0.013, 0.995],
    },
    // How far the brows can travel: it has to stay inside the gap between the
    // rim and the brows, or the lift samples the rim and prints it as a brow.
    browLift: 0.018,
  },
  // Meshy mascot "glasses, a biped" (2026-09-26): arms hang in a soft A-pose
  // with the elbows bent. Built with reskin.mjs, then the arrow was lifted
  // 2 cm clear of the ears (they touched) so the height cut can tell them apart,
  // then repainted: one clean black for the glasses, flat charcoal brows, and
  // the blue Meshy leaves between UV islands replaced by edge padding.
  v7: {
    url: '/models/zinvest-bear-v7.glb',
    height: 1.72,
    faceX: 0,
    aPose: { armR: 35.3, armL: 31.4, foreR: 8.1, foreL: 14.4 },
    landmarks: {
      arrowY: 1.522,
      arrow: [-0.001, 1.626, 0.025],
      eyeL: [-0.125, 1.156],
      eyeR: [0.124, 1.156],
      browL: [-0.136, 1.327],
      browR: [0.135, 1.327],
      rimTop: 1.308,
      mouth: [0.001, 0.993],
    },
    // The brows here are bumps in the mesh with a UV seam along their lower
    // edge: shifting the texture (v6's way) left the bump behind as a second,
    // paler brow and pulled blue in from the next island. So the rig lifts the
    // brow's vertices instead, fading to nothing at the top of the frame.
    // Measured by scripts/mascot/repaint.mjs: the painted brows span
    // x ±0.078..±0.196, y 1.306..1.346; the frame ends at 1.288.
    browMesh: { rim: 1.29, bottom: 1.304, top: 1.35, fade: 1.385, halfWidth: 0.065 },
    browLift: 0.016,
    // The painted fur (sRGB 251, 251, 253) in linear light: what the rig
    // paints over the eyes when they close. v6's greyer default showed as a patch.
    fur: [0.965, 0.965, 0.982],
  },
  // Meshy "Polar Bear Character, biped" (2026-09-29): a smaller head, arms in
  // the same soft A-pose, 10k triangles, no finger bones. Exported fully
  // metallic with its colours doubled as emission (build-web.mjs resets both),
  // and painted in a grey fur and a mustard arrow (repaint.mjs lifts them).
  // Face numbers come from the texture itself (scratchpad face-map: every texel
  // at its model position, frontmost wins), which reproduces v7's to 2 mm.
  v8: {
    url: '/models/zinvest-bear-v8.glb',
    height: 1.941,
    faceX: 0,
    aPose: { armR: 33.7, armL: 33.0, foreR: 11.0, foreL: 15.4 },
    landmarks: {
      arrowY: 1.714,
      arrow: [0.006, 1.832, -0.037],
      eyeL: [-0.15, 1.329],
      eyeR: [0.148, 1.329],
      browL: [-0.161, 1.524],
      browR: [0.162, 1.524],
      rimTop: 1.485,
      mouth: [0, 1.141],
    },
    // The painted eyes and mouth are this much larger than v6/v7's, which the
    // face shader's shapes were drawn for.
    faceScale: 1.17,
    // Brows are bumps again, 1.2 cm above the frame (x ±0.091..±0.233,
    // y 1.497..1.548).
    browMesh: { rim: 1.49, bottom: 1.5, top: 1.548, fade: 1.59, halfWidth: 0.077 },
    browLift: 0.018,
    fur: [0.965, 0.965, 0.982],
  },
}

export const MODEL = MODELS.v8
