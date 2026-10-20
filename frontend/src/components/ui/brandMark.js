// The Zinvest mark: a Z with a stem through the top and bottom bars, read as
// a currency sign. One source for the app logo, the favicon and the textures
// on the mascot's props. Stroke-based on a 64 x 64 grid.
export const MARK_VIEWBOX = '0 0 64 64'
export const MARK_STROKE = 7
export const MARK_PATHS = ['M17 19H47L17 45H47', 'M32 8V19', 'M32 45V56']

/** Draw the mark on a 2D canvas context, centred at (cx, cy), `size` px wide. */
export function drawMark(ctx, cx, cy, size, color) {
  const s = size / 64
  ctx.save()
  ctx.translate(cx - size / 2, cy - size / 2)
  ctx.scale(s, s)
  ctx.strokeStyle = color
  ctx.lineWidth = MARK_STROKE
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  for (const d of MARK_PATHS) ctx.stroke(new Path2D(d))
  ctx.restore()
}
