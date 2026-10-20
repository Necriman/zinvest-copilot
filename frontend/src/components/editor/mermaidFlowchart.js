// Bridge between a visual node/edge model and mermaid `flowchart` text.
//   model = { direction: 'TD'|'LR'|…, nodes: [{id,label,shape,x,y}], edges: [{id,source,target,label}] }
// serialize() writes the mermaid source; parseFlowchart() reads it back (best-effort
// for the subset the visual editor produces + common hand-written flowcharts);
// autoLayout() assigns reasonable positions when none are stored.

// shape → the mermaid bracket pair that wraps the node label.
const SHAPE_WRAP = {
  rect: ['[', ']'],
  round: ['(', ')'],
  stadium: ['([', '])'],
  circle: ['((', '))'],
  diamond: ['{', '}'],
  hexagon: ['{{', '}}'],
}
// Longest-first so `((` is tried before `(` when parsing.
const SHAPE_MATCH = [
  { shape: 'circle', open: '((', close: '))' },
  { shape: 'stadium', open: '([', close: '])' },
  { shape: 'hexagon', open: '{{', close: '}}' },
  { shape: 'rect', open: '[', close: ']' },
  { shape: 'round', open: '(', close: ')' },
  { shape: 'diamond', open: '{', close: '}' },
]

const DIRECTIONS = ['TD', 'TB', 'BT', 'LR', 'RL']

function quote(label) {
  return '"' + String(label ?? '').replace(/"/g, '&quot;') + '"'
}
function cleanLabel(raw) {
  return String(raw ?? '')
    .trim()
    .replace(/^"(.*)"$/s, '$1')
    .replace(/&quot;/g, '"')
    .trim()
}

// --- serialize -------------------------------------------------------------
export function serializeFlowchart(model) {
  const direction = DIRECTIONS.includes(model?.direction) ? model.direction : 'TD'
  const nodes = model?.nodes || []
  const edges = model?.edges || []
  const lines = [`flowchart ${direction}`]
  for (const n of nodes) {
    const [o, c] = SHAPE_WRAP[n.shape] || SHAPE_WRAP.rect
    lines.push(`    ${n.id}${o}${quote(n.label ?? n.id)}${c}`)
  }
  for (const e of edges) {
    const lbl = e.label ? `|${quote(e.label)}|` : ''
    lines.push(`    ${e.source} -->${lbl} ${e.target}`)
  }
  return lines.join('\n')
}

// --- parse -----------------------------------------------------------------
// Pull `id` + optional shape/label off one endpoint token, registering the node.
function parseEndpoint(token, nodes) {
  const t = (token || '').trim()
  const m = t.match(/^([A-Za-z0-9_]+)\s*(.*)$/s)
  if (!m) return null
  const id = m[1]
  const rest = m[2].trim()
  let label = null
  let shape = null
  if (rest) {
    for (const s of SHAPE_MATCH) {
      if (rest.startsWith(s.open) && rest.endsWith(s.close) && rest.length >= s.open.length + s.close.length) {
        label = cleanLabel(rest.slice(s.open.length, rest.length - s.close.length))
        shape = s.shape
        break
      }
    }
  }
  const existing = nodes.get(id)
  if (existing) {
    if (label != null) existing.label = label
    if (shape != null) existing.shape = shape
  } else {
    nodes.set(id, { id, label: label != null ? label : id, shape: shape || 'rect' })
  }
  return id
}

// Split a statement on arrow operators (keeping them), then wire consecutive
// endpoints. A `|label|` prefix on an endpoint is the label of the edge into it.
const ARROW_RE = /\s*(-\.->|-\.-|==+>|--+>|--+|===+)\s*/

function parseStatement(stmt, nodes, edges) {
  const line = stmt.trim()
  if (!line || line.startsWith('%%')) return
  if (!ARROW_RE.test(line)) {
    parseEndpoint(line, nodes) // plain node definition
    return
  }
  const parts = line.split(ARROW_RE)
  const points = []
  for (let i = 0; i < parts.length; i += 2) {
    let tok = (parts[i] || '').trim()
    let label = ''
    const lm = tok.match(/^\|([^|]*)\|\s*(.*)$/s)
    if (lm) {
      label = cleanLabel(lm[1])
      tok = lm[2].trim()
    }
    if (!tok) continue
    const id = parseEndpoint(tok, nodes)
    points.push({ id, label })
  }
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i]
    const b = points[i + 1]
    if (!a?.id || !b?.id) continue
    edges.push({ id: `e-${a.id}-${b.id}-${edges.length}`, source: a.id, target: b.id, label: b.label || '' })
  }
}

// Returns a model, or null if `code` isn't a parseable flowchart.
export function parseFlowchart(code) {
  const text = String(code || '').trim()
  const header = text.match(/^(?:flowchart|graph)\s+(TD|TB|BT|LR|RL)\b/i)
  if (!header) return null
  const direction = header[1].toUpperCase() === 'TB' ? 'TD' : header[1].toUpperCase()
  const body = text.slice(text.indexOf('\n') + 1)
  const nodes = new Map()
  const edges = []
  // statements split on newlines and semicolons
  for (const raw of body.split(/[\n;]+/)) parseStatement(raw, nodes, edges)
  if (!nodes.size) return null
  return { direction, nodes: [...nodes.values()], edges }
}

export function isFlowchart(code) {
  return /^(?:flowchart|graph)\s+(TD|TB|BT|LR|RL)\b/i.test(String(code || '').trim())
}

// --- auto layout -----------------------------------------------------------
// Longest-path layering: rank each node by its deepest incoming path, then spread
// nodes within a rank. Positions flow down (TD/BT) or across (LR/RL).
export function autoLayout(model) {
  const nodes = model?.nodes || []
  const edges = model?.edges || []
  const horizontal = model?.direction === 'LR' || model?.direction === 'RL'
  const rank = new Map(nodes.map((n) => [n.id, 0]))
  const indeg = new Map(nodes.map((n) => [n.id, 0]))
  for (const e of edges) if (indeg.has(e.target)) indeg.set(e.target, indeg.get(e.target) + 1)
  // relax edges until stable (cycle-guarded)
  let changed = true
  let guard = 0
  const cap = nodes.length * nodes.length + 20
  while (changed && guard++ < cap) {
    changed = false
    for (const e of edges) {
      if (!rank.has(e.source) || !rank.has(e.target)) continue
      const want = rank.get(e.source) + 1
      if (rank.get(e.target) < want) {
        rank.set(e.target, want)
        changed = true
      }
    }
  }
  const byRank = new Map()
  for (const n of nodes) {
    const r = rank.get(n.id) || 0
    if (!byRank.has(r)) byRank.set(r, [])
    byRank.get(r).push(n)
  }
  const CROSS = 150
  const MAIN = 130
  for (const [r, group] of byRank) {
    group.forEach((n, i) => {
      const cross = i * CROSS - ((group.length - 1) * CROSS) / 2 + 320
      const main = r * MAIN + 40
      n.x = horizontal ? main : cross
      n.y = horizontal ? cross : main
    })
  }
  return model
}
