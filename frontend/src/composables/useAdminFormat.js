// Numbers and dates for the admin panel, in the interface language.
import { useI18n } from 'vue-i18n'

export function useAdminFormat() {
  const { locale, t, te } = useI18n()

  const parse = (iso) => {
    if (!iso) return null
    const d = new Date(iso)
    return Number.isNaN(d.getTime()) ? null : d
  }

  const num = (n) => new Intl.NumberFormat(locale.value).format(Number(n || 0))

  const compact = (n) =>
    new Intl.NumberFormat(locale.value, { notation: 'compact', maximumFractionDigits: 1 }).format(Number(n || 0))

  function date(iso) {
    const d = parse(iso)
    return d ? d.toLocaleDateString(locale.value, { day: 'numeric', month: 'short', year: 'numeric' }) : '—'
  }

  function dateTime(iso) {
    const d = parse(iso)
    return d
      ? d.toLocaleString(locale.value, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
      : '—'
  }

  function shortDate(iso) {
    const d = parse(iso)
    return d ? d.toLocaleDateString(locale.value, { day: 'numeric', month: 'short' }) : ''
  }

  /** "5 minutes ago", "yesterday"; a plain date after a month; "never" for none. */
  function ago(iso) {
    const d = parse(iso)
    if (!d) return t('admin.common.never')
    const seconds = Math.round((d.getTime() - Date.now()) / 1000)
    const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' })
    const abs = Math.abs(seconds)
    if (abs < 60) return rtf.format(0, 'second')
    if (abs < 3600) return rtf.format(Math.round(seconds / 60), 'minute')
    if (abs < 86400) return rtf.format(Math.round(seconds / 3600), 'hour')
    if (abs < 30 * 86400) return rtf.format(Math.round(seconds / 86400), 'day')
    return date(iso)
  }

  /** Security event kinds and audit actions in the interface language. */
  function eventLabel(kind, fallback = '') {
    const key = `admin.events.${kind}`
    return te(key) ? t(key) : fallback || kind
  }

  function actionLabel(action) {
    const key = `admin.actions.${String(action).replace(/\./g, '_')}`
    return te(key) ? t(key) : action
  }

  return { num, compact, date, dateTime, shortDate, ago, eventLabel, actionLabel }
}
