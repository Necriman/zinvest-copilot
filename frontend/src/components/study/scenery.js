// Each unit's own little world on the study map: three objects drawn from its
// lessons, in the same soft 3D style as the Zinvest bear, set in the margins
// either side of the path so they never sit on a stop.
//
// Keyed by unit slug, not by code or position, so renumbering units in the
// admin cannot hand a unit someone else's scenery. A unit with no entry simply
// has none, and keeps its icon.
//
// `at` places each object in the path's margin: side, how far down the unit
// (percent of its height), size in px, and a small tilt so the three never
// line up like icons in a row.

const place = [
  { side: 'left', top: 9, size: 124, tilt: -6 },
  { side: 'right', top: 40, size: 136, tilt: 5 },
  { side: 'left', top: 70, size: 116, tilt: 3 },
]

export const SCENERY = {
  // What money is, assets vs liabilities, budgeting.
  'finance-fundamentals': ['coins', 'scale', 'piggy'],
  // Stocks, diversification, index funds, risk and return, compounding.
  'investing-basics': ['sprout', 'chart', 'basket'],
  // The statements, ratios, runway and burn, unit economics.
  'financial-analysis': ['magnifier', 'hourglass', 'calculator'],
  // Paying yourself first, emergency funds, long-term wealth.
  'personal-finance-wealth': ['house', 'umbrella', 'jar'],

  // The course from the unit files (backend import_units).
  'what-is-finance': ['coins', 'scale', 'magnifier'],
  'time-value-of-money': ['hourglass', 'chart', 'sprout'],
  'personal-budgeting': ['calculator', 'basket', 'jar'],
  'saving-and-growing-money': ['piggy', 'sprout', 'jar'],
  'credit-and-debt': ['scale', 'calculator', 'house'],
  'banking-system': ['house', 'coins', 'umbrella'],
  'income-and-earning': ['coins', 'chart', 'basket'],
  'insurance-basics': ['umbrella', 'house', 'scale'],
  'taxes-for-beginners': ['calculator', 'magnifier', 'scale'],
  'financial-goal-setting': ['chart', 'hourglass', 'piggy'],
  'introduction-to-economics': ['basket', 'scale', 'chart'],
}

export function sceneryFor(slug) {
  const names = SCENERY[slug]
  if (!names) return null
  return {
    // The first object doubles as the unit's emblem in its header.
    emblem: `/scenery/${names[0]}.webp`,
    objects: names.map((name, i) => ({ name, src: `/scenery/${name}.webp`, ...place[i] })),
  }
}
