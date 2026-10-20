// Parse / serialize helpers for the diagram types that get a visual (form) builder:
// pie, gantt, class. (Flowchart lives in mermaidFlowchart.js — it's a node graph.)
// Each parseX is best-effort for common mermaid; serializeX writes clean output.
import { isFlowchart } from './mermaidFlowchart'

// --- type detection + starter templates ------------------------------------
export function detectType(code) {
  const t = String(code || '').trim()
  if (!t) return 'empty'
  if (isFlowchart(t)) return 'flowchart'
  if (/^classDiagram\b/i.test(t)) return 'class'
  if (/^pie\b/i.test(t)) return 'pie'
  if (/^gantt\b/i.test(t)) return 'gantt'
  return 'other'
}

// Types that have a visual builder (used to enable the Visual tab + type selector).
export const VISUAL_TYPES = ['flowchart', 'class', 'pie', 'gantt']

export const STARTERS = {
  flowchart: 'flowchart TD\n    A["Start"] --> B["End"]',
  class: 'classDiagram\n    class Account {\n        +String owner\n        +deposit(amount)\n    }',
  pie: 'pie title Budget\n    "Rent" : 40\n    "Food" : 30\n    "Savings" : 30',
  gantt: 'gantt\n    title Plan\n    dateFormat YYYY-MM-DD\n    section Phase 1\n    Research :2024-01-01, 10d\n    Build :2024-01-11, 20d',
}

// --- pie -------------------------------------------------------------------
export function parsePie(code) {
  let title = ''
  const slices = []
  for (const raw of String(code || '').split('\n')) {
    const line = raw.trim()
    if (!line) continue
    const h = line.match(/^pie(?:\s+showData)?(?:\s+title\s+(.*))?$/i)
    if (h) {
      if (h[1]) title = h[1].trim()
      continue
    }
    const s = line.match(/^(?:"([^"]*)"|([^:]+?))\s*:\s*([\d.]+)$/)
    if (s) slices.push({ label: (s[1] ?? s[2] ?? '').trim(), value: parseFloat(s[3]) || 0 })
  }
  return { title, slices }
}
export function serializePie({ title, slices }) {
  const lines = [title ? `pie title ${title}` : 'pie']
  for (const s of slices || []) lines.push(`    "${String(s.label || '').replace(/"/g, '')}" : ${Number(s.value) || 0}`)
  return lines.join('\n')
}

// --- gantt -----------------------------------------------------------------
export function parseGantt(code) {
  let title = ''
  let section = ''
  const tasks = []
  for (const raw of String(code || '').split('\n')) {
    const line = raw.trim()
    if (!line || /^(gantt|dateFormat|axisFormat|excludes|todayMarker)\b/i.test(line)) continue
    const tm = line.match(/^title\s+(.*)$/i)
    if (tm) {
      title = tm[1].trim()
      continue
    }
    const sm = line.match(/^section\s+(.*)$/i)
    if (sm) {
      section = sm[1].trim()
      continue
    }
    const km = line.match(/^(.*?)\s*:\s*(.*)$/)
    if (km) {
      const name = km[1].trim()
      let start = ''
      let duration = ''
      for (const tok of km[2].split(',').map((s) => s.trim())) {
        if (/^\d+[dhwmy]$/i.test(tok)) duration = tok
        else if (/^\d{4}-\d{2}-\d{2}$/.test(tok) || /^after\s+/i.test(tok)) { if (!start) start = tok }
      }
      tasks.push({ section, name, start, duration })
    }
  }
  return { title, tasks }
}
export function serializeGantt({ title, tasks }) {
  const lines = ['gantt']
  if (title) lines.push(`    title ${title}`)
  lines.push('    dateFormat YYYY-MM-DD')
  let cur = null
  for (const t of tasks || []) {
    const sec = t.section || ''
    if (sec !== cur) {
      if (sec) lines.push(`    section ${sec}`)
      cur = sec
    }
    const meta = [t.start, t.duration || '1d'].filter(Boolean).join(', ')
    lines.push(`    ${t.name || 'Task'} :${meta}`)
  }
  return lines.join('\n')
}

// --- class -----------------------------------------------------------------
export const CLASS_RELATIONS = [
  { type: 'inheritance', op: '<|--', label: 'Inheritance' },
  { type: 'realization', op: '..|>', label: 'Realization' },
  { type: 'composition', op: '*--', label: 'Composition' },
  { type: 'aggregation', op: 'o--', label: 'Aggregation' },
  { type: 'association', op: '-->', label: 'Association' },
  { type: 'dependency', op: '..>', label: 'Dependency' },
  { type: 'link', op: '--', label: 'Link' },
]
const REL_BY_OP = CLASS_RELATIONS.map((r) => [r.op, r.type]) // longest-first already
const REL_OP = Object.fromEntries(CLASS_RELATIONS.map((r) => [r.type, r.op]))

export function parseClass(code) {
  const classes = new Map()
  const relations = []
  const ensure = (name) => {
    if (!classes.has(name)) classes.set(name, { name, members: [] })
    return classes.get(name)
  }
  let current = null
  for (const raw of String(code || '').split('\n')) {
    const line = raw.trim()
    if (!line || /^classDiagram/i.test(line)) continue
    if (current) {
      if (line === '}') {
        current = null
      } else {
        ensure(current).members.push(line)
      }
      continue
    }
    let m = line.match(/^class\s+([A-Za-z0-9_]+)\s*\{$/)
    if (m) {
      current = m[1]
      ensure(current)
      continue
    }
    m = line.match(/^class\s+([A-Za-z0-9_]+)\s*$/)
    if (m) {
      ensure(m[1])
      continue
    }
    // relation: A OP B [: label]
    let matched = false
    for (const [op, type] of REL_BY_OP) {
      const idx = line.indexOf(op)
      if (idx > 0) {
        let left = line.slice(0, idx).trim()
        let right = line.slice(idx + op.length).trim()
        let rel = ''
        const lm = right.match(/^(.*?)\s*:\s*(.*)$/)
        if (lm) {
          right = lm[1].trim()
          rel = lm[2].trim()
        }
        const from = left.split(/\s+/)[0]
        const to = right.split(/\s+/)[0]
        if (from && to) {
          ensure(from)
          ensure(to)
          relations.push({ from, to, type, label: rel })
          matched = true
        }
        break
      }
    }
    if (matched) continue
    // colon member form: Class : +member
    m = line.match(/^([A-Za-z0-9_]+)\s*:\s*(.+)$/)
    if (m) ensure(m[1]).members.push(m[2].trim())
  }
  return { classes: [...classes.values()], relations }
}
export function serializeClass({ classes, relations }) {
  const lines = ['classDiagram']
  for (const c of classes || []) {
    const members = (c.members || []).filter((m) => String(m).trim())
    if (members.length) {
      lines.push(`    class ${c.name} {`)
      for (const m of members) lines.push(`        ${String(m).trim()}`)
      lines.push('    }')
    } else {
      lines.push(`    class ${c.name}`)
    }
  }
  for (const r of relations || []) {
    if (!r.from || !r.to) continue
    const op = REL_OP[r.type] || '-->'
    lines.push(`    ${r.from} ${op} ${r.to}${r.label ? ` : ${r.label}` : ''}`)
  }
  return lines.join('\n')
}
