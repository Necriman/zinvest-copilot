// Per-unit accent palettes for the study map.
//
// Each unit carries an `accent_color` key from the backend (brand / invest /
// risk / budget …). Without this every category rendered in the same blue and
// the four paths looked like copies of each other.
//
// Tailwind v4 needs whole class strings — never build these at runtime.
export const ACCENTS = {
  brand: {
    track: 'text-brand-600',
    trackSoft: 'text-brand-500/30',
    fill: 'bg-brand-600 shadow-brand-600/30',
    ring: 'ring-brand-500/40',
    pulse: 'bg-brand-400/40',
    ink: 'text-brand-600',
    soft: 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300',
  },
  invest: {
    track: 'text-sky-500',
    trackSoft: 'text-sky-500/30',
    fill: 'bg-sky-500 shadow-sky-500/30',
    ring: 'ring-sky-400/40',
    pulse: 'bg-sky-300/40',
    ink: 'text-sky-600',
    soft: 'bg-sky-50 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300',
  },
  risk: {
    track: 'text-violet-500',
    trackSoft: 'text-violet-500/30',
    fill: 'bg-violet-500 shadow-violet-500/30',
    ring: 'ring-violet-400/40',
    pulse: 'bg-violet-300/40',
    ink: 'text-violet-600',
    soft: 'bg-violet-50 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300',
  },
  budget: {
    track: 'text-amber-500',
    trackSoft: 'text-amber-500/35',
    fill: 'bg-amber-500 shadow-amber-500/30',
    ring: 'ring-amber-400/40',
    pulse: 'bg-amber-300/40',
    ink: 'text-amber-600',
    soft: 'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
  },
  cash: {
    track: 'text-emerald-500',
    trackSoft: 'text-emerald-500/30',
    fill: 'bg-emerald-500 shadow-emerald-500/30',
    ring: 'ring-emerald-400/40',
    pulse: 'bg-emerald-300/40',
    ink: 'text-emerald-600',
    soft: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300',
  },
  startup: {
    track: 'text-pink-500',
    trackSoft: 'text-pink-500/30',
    fill: 'bg-pink-500 shadow-pink-500/30',
    ring: 'ring-pink-400/40',
    pulse: 'bg-pink-300/40',
    ink: 'text-pink-600',
    soft: 'bg-pink-50 text-pink-700 dark:bg-pink-500/15 dark:text-pink-300',
  },
}

export const accentOf = (key) => ACCENTS[key] || ACCENTS.brand

/**
 * Weave shapes, chosen by unit index.
 *
 * `phase` decides which way the path leans first, `amp` how wide it swings and
 * `step` how far apart the stops sit — but the big differentiator is `curve`,
 * which changes how the track is actually *drawn* between two stops. Varying
 * only the placement still left every unit tracing the same kind of line.
 *
 *   wave  — gentle S, control points at the vertical midpoint
 *   arc   — a single belly bulging away from the centre line
 *   step  — squared-off route with rounded corners, board-game-ish
 *   swoop — exaggerated S that sweeps out before turning back
 */
export const WEAVES = [
  { phase: 0, amp: 0.3, step: 132, curve: 'wave', width: 8, dash: '2 16' },
  { phase: Math.PI, amp: 0.34, step: 146, curve: 'arc', width: 9, dash: '12 14' },
  { phase: Math.PI / 2, amp: 0.26, step: 128, curve: 'step', width: 7, dash: '4 11' },
  { phase: -Math.PI / 2, amp: 0.38, step: 154, curve: 'swoop', width: 10, dash: '1 15' },
]

export const weaveFor = (index) => WEAVES[((index % WEAVES.length) + WEAVES.length) % WEAVES.length]
