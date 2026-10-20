// Small helpers shared by the narrator and the voice-pack scripts.

/** Collapse whitespace and unify quotes so the same sentence always hashes the same. */
export function normalizeSpeech(text) {
  return String(text || '')
    .replace(/[‘’ʼʻ`]/g, "'")
    .replace(/[“”«»]/g, '"')
    .replace(/\s+/g, ' ')
    .trim()
}

/** 53-bit string hash (cyrb53), hex. Keys recorded clips by their exact text. */
export function speechKey(text) {
  const s = normalizeSpeech(text)
  let h1 = 0xdeadbeef, h2 = 0x41c6ce57
  for (let i = 0; i < s.length; i++) {
    const ch = s.charCodeAt(i)
    h1 = Math.imul(h1 ^ ch, 2654435761)
    h2 = Math.imul(h2 ^ ch, 1597334677)
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909)
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909)
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(16).padStart(14, '0')
}

const UZ_CYRILLIC = /[ўқғҳЎҚҒҲ]/
const UZ_LATIN = /[og][‘'ʻʼ`]|\b(va|bu|uchun|bilan|emas|qanday|nima|yoki|siz|kerak|bo[‘'ʻ]l|haqida|keyin)\b/i

/**
 * The language a text is written in: 'ru', 'uz' or 'en'. Lessons are in English
 * while the interface may be in Russian, so the voice follows the text itself.
 */
export function detectLang(text, fallback = 'en') {
  const s = String(text || '')
  const cyr = (s.match(/[Ѐ-ӿ]/g) || []).length
  const lat = (s.match(/[a-z]/gi) || []).length
  if (!cyr && !lat) return fallback
  if (cyr >= lat) return UZ_CYRILLIC.test(s) ? 'uz' : 'ru'
  return UZ_LATIN.test(s) ? 'uz' : 'en'
}
