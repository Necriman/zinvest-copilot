// Meshy export (35 MB, 200k tris, 4K PNG) -> a web GLB like zinvest-bear-v6:
// simplified mesh, 1024px WebP textures, quantized + meshopt-compressed.
//   node build-web.mjs in.glb out.glb [ratio]
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'
import { dedup, meshopt, prune, quantize, resample, simplify, textureCompress, weld } from '@gltf-transform/functions'
import { MeshoptDecoder, MeshoptEncoder, MeshoptSimplifier } from 'meshoptimizer'
import sharp from 'sharp'

await MeshoptDecoder.ready
await MeshoptEncoder.ready
await MeshoptSimplifier.ready
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder })

const [input, output, ratio = '0.17'] = process.argv.slice(2)
const doc = await io.read(input)

// Some exports (v8) come out fully metallic with no metal/roughness map and the
// colour texture repeated as emission: the bear then glows its own colour,
// ignores the lights and reads flat and grey. A plush bear is matte and does
// not glow, so those two cases are reset; a model with a real metal/roughness
// map (v7) is left as it is.
for (const m of doc.getRoot().listMaterials()) {
  if (!m.getMetallicRoughnessTexture() && m.getMetallicFactor() > 0) {
    m.setMetallicFactor(0).setRoughnessFactor(0.78)
    console.log('material', m.getName(), ': metallic 1 without a map -> matte')
  }
  const emissive = m.getEmissiveTexture()
  if (emissive && emissive === m.getBaseColorTexture()) {
    m.setEmissiveTexture(null).setEmissiveFactor([0, 0, 0])
    console.log('material', m.getName(), ': colour texture used as emission -> none')
  }
  for (const ext of m.listExtensions()) {
    if (['KHR_materials_specular', 'KHR_materials_ior'].includes(ext.extensionName)) m.setExtension(ext.extensionName, null)
  }
}
const tris = () => doc.getRoot().listMeshes().flatMap((m) => m.listPrimitives()).reduce((n, p) => n + (p.getIndices()?.getCount() || 0) / 3, 0)
console.log('before', Math.round(tris()), 'tris')
await doc.transform(
  dedup(),
  weld(),
  simplify({ simplifier: MeshoptSimplifier, ratio: Number(ratio), error: 0.0008 }),
  resample(),
  prune(),
  textureCompress({ encoder: sharp, targetFormat: 'webp', resize: [1024, 1024], quality: 88 }),
)
console.log('after ', Math.round(tris()), 'tris')
await doc.transform(quantize(), meshopt({ encoder: MeshoptEncoder, level: 'medium' }))
await io.write(output, doc)
console.log('written', output)
