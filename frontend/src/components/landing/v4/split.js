/**
 * Headline splitting for the V4 entrances.
 *
 * Every "random" offset comes from a seeded generator, so a line assembles the
 * same way on every load and in every language switch. The pieces carry their
 * own custom properties; the CSS entrance reads them against the band's --k.
 */

export function rng(seed) {
  let s = seed >>> 0
  return () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296
}

/**
 * Words with per-character jitter, for a scatter entrance.
 * Returns [{ text, chars: [{ c, style }] }].
 */
export function scatter(text, seed = 7) {
  const r = rng(seed)
  return String(text)
    .split(' ')
    .filter(Boolean)
    .map((word) => ({
      text: word,
      chars: [...word].map((c) => ({
        c,
        style: {
          '--th': (r() * 0.55).toFixed(3),
          '--jx': `${Math.round((r() - 0.5) * 90)}px`,
          '--jy': `${Math.round(-20 - r() * 60)}px`,
          '--jr': `${Math.round((r() - 0.5) * 50)}deg`,
        },
      })),
    }))
}

/**
 * Words with thresholds in reading order, for the word-level entrances
 * (drift down, grow, rise). `spread` is how much of --k the stagger uses.
 */
export function ordered(text, spread = 0.5, seed = 11) {
  const r = rng(seed)
  const words = String(text).split(' ').filter(Boolean)
  const n = Math.max(1, words.length - 1)
  return words.map((word, i) => ({
    text: word,
    style: { '--th': ((i / n) * spread + r() * 0.04).toFixed(3) },
  }))
}

/**
 * Characters in reading order that drop a short way into place, each a beat
 * after the last, like coins set onto a stack. Same shape as scatter().
 */
export function dropIn(text, seed = 7) {
  const r = rng(seed)
  const words = String(text).split(' ').filter(Boolean)
  const total = Math.max(1, words.join('').length - 1)
  let n = 0
  return words.map((word) => ({
    text: word,
    chars: [...word].map((c) => ({
      c,
      style: {
        '--th': ((n++ / total) * 0.5 + r() * 0.03).toFixed(3),
        '--jx': '0px',
        '--jy': `${Math.round(-14 - r() * 10)}px`,
        '--jr': '0deg',
      },
    })),
  }))
}
