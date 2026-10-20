// Prices the way the "Up or down?" game writes them: the unit in front, a
// no-break space between thousands (the narrow one is missing from the UI
// font), decimals only while a price is small enough to need them, and a
// real minus sign — oil did go below zero once.

export function formatPrice(value, unit = '') {
  const sign = value < 0 ? '−' : ''
  const abs = Math.abs(value)
  const text =
    abs >= 100
      ? Math.round(abs).toLocaleString('en-US').replace(/,/g, ' ')
      : String(Number(abs.toFixed(2)))
  return `${sign}${unit}${text}`
}

/** "+44%", or "" when the price crossed zero and a percentage means nothing. */
export function formatChange(start, end) {
  if (start <= 0 || end <= 0) return ''
  const pct = (100 * (end - start)) / start
  return `${pct >= 0 ? '+' : '−'}${Math.abs(pct).toFixed(0)}%`
}
