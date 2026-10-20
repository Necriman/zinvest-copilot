// Bridge the backend's coordinate-based lesson payload into clean semantic HTML
// for the Tiptap document editor. The payload shape is authored by our own seed
// (learning/management/commands/seed_learning.py), so this mapping is reliable:
//   text (big font) -> <h1>/<h2>,  "• …" text -> <ul><li>,  table -> <table>.
function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function fontSize(font) {
  const m = /(\d+)px/.exec(font || '')
  return m ? Number(m[1]) : 16
}

function renderTable(el) {
  const rows = el.rows || []
  let html = '<table>'
  rows.forEach((row, r) => {
    const tag = el.header && r === 0 ? 'th' : 'td'
    html += '<tr>' + row.map((c) => `<${tag}>${esc(c)}</${tag}>`).join('') + '</tr>'
  })
  return html + '</table>'
}

export function payloadToHtml(payload) {
  if (!payload || !Array.isArray(payload.elements)) return ''

  let html = ''
  let bullets = []
  const flush = () => {
    if (bullets.length) {
      html += '<ul>' + bullets.map((b) => `<li>${esc(b)}</li>`).join('') + '</ul>'
      bullets = []
    }
  }

  for (const el of payload.elements) {
    if (el.type === 'text') {
      const t = String(el.text ?? '').trim()
      if (!t) continue
      if (t.startsWith('•')) {
        bullets.push(t.replace(/^•\s*/, ''))
        continue
      }
      flush()
      const size = fontSize(el.font)
      if (size >= 26) html += `<h1>${esc(t)}</h1>`
      else if (size >= 18) html += `<h2>${esc(t)}</h2>`
      else html += `<p>${esc(t)}</p>`
    } else if (el.type === 'table') {
      flush()
      html += renderTable(el)
    }
    // rect / roundRect / line / image are decorative — skipped in the document view.
  }
  flush()
  return html
}
