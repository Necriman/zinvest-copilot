// Serialized mermaid rendering — one render at a time, page-wide.
//
// `mermaid.render()` mutates shared module-level state and a temporary DOM node it
// creates to measure text (and, in strict mode, a sandbox). It is NOT safe to run
// concurrently: when a document opens with several diagrams, every MermaidView
// mounts and calls render in the same tick, their async calls interleave, and one
// call's cleanup removes a node another is mid-way through reading — mermaid then
// throws "Cannot read properties of null (reading 'firstChild')". Because it's a
// timing race it only shows up *sometimes*, and only with more than one diagram
// (a lone diagram in the editor modal always renders fine).
//
// Funnelling every render through a single promise chain (a mutex) means the
// diagrams render one after another instead of on top of each other, which
// removes the race. Both the document NodeView (MermaidView) and the modal/builder
// preview (MermaidPreview) go through here.

let mermaidPromise = null
function loadMermaid() {
  // One lazily-imported mermaid module shared by every caller — the ~large bundle
  // only loads when a document actually contains a diagram.
  if (!mermaidPromise) mermaidPromise = import('mermaid').then((m) => m.default)
  return mermaidPromise
}

const isDark = () => document.documentElement.classList.contains('dark')

let queue = Promise.resolve()
let uid = 0 // monotonic and never reused, so generated ids can't collide across calls

/**
 * Render mermaid `code` to an SVG string, serialized against every other call in
 * the app. Rejects with the parse/render error so the caller can show its
 * fallback. The returned SVG is a plain string — assign it with `innerHTML`.
 */
export function renderMermaid(code) {
  const run = async () => {
    const mermaid = await loadMermaid()
    const id = `zv-mermaid-${uid++}`
    // Safe to (re)initialize on each call now that renders never overlap; this
    // picks up the current light/dark theme. `strict` sanitizes labels and blocks
    // inline scripts, since the diagram source is user content.
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: isDark() ? 'dark' : 'default',
      fontFamily: 'inherit',
    })
    try {
      const { svg } = await mermaid.render(id, code)
      return svg
    } catch (e) {
      document.getElementById(id)?.remove() // stray node left by a failed render
      throw e
    } finally {
      document.getElementById(`d${id}`)?.remove() // mermaid's temp measuring node
    }
  }
  // Chain onto the queue whether the previous render resolved or rejected, and
  // keep the queue itself un-rejected so one bad diagram can't stall the rest.
  const result = queue.then(run, run)
  queue = result.then(
    () => {},
    () => {},
  )
  return result
}
