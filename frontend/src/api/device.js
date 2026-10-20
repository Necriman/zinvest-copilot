// A stable per-browser identifier. This is NOT a secret — it labels a device so
// the backend can bind a token family to it and flag anomalies. Safe in
// localStorage; never used as an authentication factor.
const KEY = 'auth.device_id'

// A v4 UUID that works in ANY context. crypto.randomUUID() is only defined in a
// secure context (HTTPS or localhost) — over plain HTTP on a custom host like
// http://zinvest.loc it's undefined and would throw. crypto.getRandomValues IS
// available everywhere, so derive the UUID from it; fall back to Math.random as
// a last resort (this is only a device label, never a secret).
function uuidv4() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  const bytes = new Uint8Array(16)
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    crypto.getRandomValues(bytes)
  } else {
    for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256)
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40 // version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80 // variant 10xx
  const hex = [...bytes].map((b) => b.toString(16).padStart(2, '0'))
  return `${hex.slice(0, 4).join('')}-${hex.slice(4, 6).join('')}-${hex.slice(6, 8).join('')}-${hex.slice(8, 10).join('')}-${hex.slice(10, 16).join('')}`
}

export function getDeviceId() {
  let id = localStorage.getItem(KEY)
  if (!id) {
    id = uuidv4()
    localStorage.setItem(KEY, id)
  }
  return id
}
