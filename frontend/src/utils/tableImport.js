/**
 * Turns a founder's spreadsheet export (CSV) or JSON file into plain row objects
 * keyed by our field names. Headers are matched loosely in English, Russian and
 * Uzbek so a file typed by hand in any of the app's languages still maps.
 */

export const IMPORT_FIELDS = {
  employees: {
    full_name: ['full_name', 'name', 'full name', 'employee', 'имя', 'фио', 'сотрудник', 'ism', 'ism familiya', 'xodim'],
    // The card's title ("Роль") and the free-text duties ("Чем занимается") are
    // separate fields; a plain "role" column is a job title.
    position: ['position', 'role', 'title', 'job title', 'job', 'должность', 'роль', 'lavozim', 'rol'],
    role: ['what they do', 'duties', 'responsibilities', 'description', 'обязанности', 'чем занимается', 'описание', 'vazifa', 'vazifalari', 'tavsif'],
    team: ['team', 'department', 'команда', 'отдел', 'jamoa', "bo'lim", 'bo‘lim'],
    salary: ['salary', 'pay', 'wage', 'зарплата', 'оклад', 'maosh', 'oylik'],
  },
  products: {
    name: ['name', 'product', 'item', 'title', 'dish', 'название', 'товар', 'блюдо', 'nomi', 'mahsulot', 'taom'],
    kind: ['kind', 'type', 'тип', 'вид', 'turi'],
    price: ['price', 'cost', 'цена', 'стоимость', 'narx', 'narxi'],
  },
}

const KIND_ALIASES = {
  product: ['product', 'goods', 'item', 'товар', 'продукт', 'mahsulot'],
  service: ['service', 'услуга', 'xizmat'],
  subscription: ['subscription', 'подписка', 'obuna'],
}

export const TEMPLATES = {
  employees: 'full_name,position,role,team,salary\nAziza Karimova,Head chef,Runs the kitchen and the menu,Kitchen,900\nBekzod Aliyev,Courier,Delivers orders across the city,Logistics,450\n',
  products: 'name,kind,price\nPlov,product,45000\nHome delivery,service,10000\nLunch plan,subscription,300000\n',
}

const norm = (s) => String(s ?? '').replace(/^\uFEFF/, '').trim().toLowerCase().replace(/[_\s]+/g, ' ')

/** RFC-4180-ish CSV: quoted fields, doubled quotes, CRLF, and ; or tab delimiters (Excel in RU/UZ locales saves with ;). */
export function parseCsv(text) {
  text = text.replace(/^\uFEFF/, '')
  const firstLine = text.split(/\r?\n/, 1)[0] || ''
  const delimiter = [',', ';', '\t'].map((d) => [d, firstLine.split(d).length]).sort((a, b) => b[1] - a[1])[0][0]
  const rows = []
  let row = [], field = '', quoted = false
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i++ }
      else if (ch === '"') quoted = false
      else field += ch
    } else if (ch === '"' && field === '') quoted = true
    else if (ch === delimiter) { row.push(field); field = '' }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++
      row.push(field); rows.push(row); row = []; field = ''
    } else field += ch
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row) }
  const nonEmpty = rows.filter((r) => r.some((c) => c.trim() !== ''))
  if (!nonEmpty.length) return []
  const [header, ...body] = nonEmpty
  return body.map((cells) => Object.fromEntries(header.map((h, i) => [h, cells[i] ?? ''])))
}

function parseJson(text) {
  const data = JSON.parse(text)
  if (Array.isArray(data)) return data
  if (data && typeof data === 'object') {
    const list = Object.values(data).find(Array.isArray)
    if (list) return list
  }
  throw new Error('json')
}

/** Money cells arrive as "45 000", "1,200.50" or "1 200,50"; keep digits and one decimal separator. */
function cleanNumber(value) {
  let s = String(value ?? '').replace(/[\s\u00a0]/g, '').replace(/[^\d.,-]/g, '')
  if (s.includes(',') && s.includes('.')) s = s.replace(/,/g, '')
  else if (/,\d{1,2}$/.test(s)) s = s.replace(',', '.')
  else s = s.replace(/,/g, '')
  return s
}

function mapKind(value) {
  const v = norm(value)
  if (!v) return 'product'
  return Object.entries(KIND_ALIASES).find(([, names]) => names.includes(v))?.[0] || v
}

/**
 * Parse a File into rows for `kind` ('employees' | 'products').
 * Throws Error('format') for unsupported files and Error('columns') when the
 * required name column cannot be found.
 */
export async function readImportFile(file, kind) {
  const text = await file.text()
  const ext = (file.name.split('.').pop() || '').toLowerCase()
  let raw
  if (ext === 'json') {
    try { raw = parseJson(text) } catch { throw new Error('format') }
  } else if (['csv', 'txt', 'tsv'].includes(ext)) raw = parseCsv(text)
  else throw new Error('format')

  const fields = IMPORT_FIELDS[kind]
  const required = kind === 'employees' ? 'full_name' : 'name'
  const rows = raw.filter((r) => r && typeof r === 'object').map((r) => {
    const byHeader = Object.fromEntries(Object.entries(r).map(([k, v]) => [norm(k), v]))
    const out = {}
    for (const [field, names] of Object.entries(fields)) {
      const hit = names.map(norm).find((n) => n in byHeader)
      if (hit !== undefined) out[field] = typeof byHeader[hit] === 'string' ? byHeader[hit].trim() : byHeader[hit]
    }
    if ('salary' in out) out.salary = cleanNumber(out.salary)
    if ('price' in out) out.price = cleanNumber(out.price)
    if (kind === 'products') out.kind = mapKind(out.kind)
    return out
  })
  if (rows.length && !rows.some((r) => r[required])) throw new Error('columns')
  return rows.filter((r) => Object.values(r).some((v) => v !== '' && v != null && v !== 'product'))
}
