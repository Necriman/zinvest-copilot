// Formatting helpers shared across finance widgets.

/**
 * Short "time ago" label for note/comment timestamps, falling back to a plain
 * date once something is more than a week old.
 */
export function relativeTime(iso) {
  if (!iso) return ''
  const then = new Date(iso)
  if (Number.isNaN(then.getTime())) return ''
  const mins = Math.round((Date.now() - then.getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days}d ago`
  return then.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

/** Intl locale for an app locale code (Uzbek is written in Latin script). */
export const intlLocale = (code) => (code === 'uz' ? 'uz-Latn' : code || undefined)

// Chrome ships no Uzbek month names (Intl prints "2026 M12"), so Uzbek months
// are named here, in the CLDR pattern ("dekabr, 2026").
const UZ_MONTHS = {
  long: ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'],
  short: ['yan', 'fev', 'mar', 'apr', 'may', 'iyn', 'iyl', 'avg', 'sen', 'okt', 'noy', 'dek'],
}
const YM = /^(\d{4})-(\d{2})$/
const parseYm = (value) => {
  const m = YM.exec(String(value ?? '').trim())
  if (!m || Number(m[2]) < 1 || Number(m[2]) > 12) return null
  return { y: Number(m[1]), m: Number(m[2]) - 1 }
}
const monthFormat = (locale, month) => new Intl.DateTimeFormat(intlLocale(locale), { month, year: 'numeric', timeZone: 'UTC' })

/**
 * "2026-12" -> "December 2026" (or "Dec 2026" with `month: 'short'`) in the
 * given app locale. Anything that is not a YYYY-MM month comes back unchanged,
 * so free text the AI wrote ("Month 3") is shown as written.
 */
export function monthLabel(value, locale, month = 'long') {
  const d = parseYm(value)
  if (!d) return value ?? ''
  if (locale === 'uz') return `${UZ_MONTHS[month === 'short' ? 'short' : 'long'][d.m]}, ${d.y}`
  try {
    return monthFormat(locale, month).format(new Date(Date.UTC(d.y, d.m, 1)))
  } catch {
    return value
  }
}

const pad2 = (n) => String(n).padStart(2, '0')

/**
 * A date and time in the app locale: `short` is "18.10, 13:09" (day and month
 * only), `long` is "18 October 2026, 13:09". Uzbek is spelled out by hand, as
 * Chrome would print "10-18 13:09" / "2026 M10 18".
 */
export function dateTime(value, locale, style = 'short') {
  const d = value instanceof Date ? value : new Date(value)
  if (!value || Number.isNaN(d.getTime())) return ''
  if (locale === 'uz') {
    const time = `${pad2(d.getHours())}:${pad2(d.getMinutes())}`
    return style === 'long'
      ? `${d.getDate()}-${UZ_MONTHS.long[d.getMonth()]}, ${d.getFullYear()}, ${time}`
      : `${pad2(d.getDate())}.${pad2(d.getMonth() + 1)}, ${time}`
  }
  const opts = style === 'long' ? { dateStyle: 'long', timeStyle: 'short' } : { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }
  return new Intl.DateTimeFormat(intlLocale(locale), opts).format(d)
}

/** "2026-07".."2026-09" -> "July – September 2026" (a range of whole months). */
export function monthRange(from, to, locale) {
  const a = parseYm(from)
  const b = parseYm(to)
  if (!a || !b) return [from, to].filter(Boolean).join(' – ')
  if (locale === 'uz') {
    return a.y === b.y
      ? `${UZ_MONTHS.long[a.m]} – ${UZ_MONTHS.long[b.m]}, ${b.y}`
      : `${monthLabel(from, locale)} – ${monthLabel(to, locale)}`
  }
  try {
    return monthFormat(locale, 'long').formatRange(new Date(Date.UTC(a.y, a.m, 1)), new Date(Date.UTC(b.y, b.m, 1)))
  } catch {
    return `${monthLabel(from, locale)} – ${monthLabel(to, locale)}`
  }
}

/** True for a plain number or a string holding only one ("60000000", "1250.5"). */
export const isNumeric = (value) =>
  typeof value === 'number' ? Number.isFinite(value) : /^-?\d+(\.\d+)?$/.test(String(value ?? '').trim())

export function money(value, currency = 'USD') {
  const n = Number(value || 0)
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(n)
  } catch {
    return `$${n.toFixed(0)}`
  }
}
