/**
 * Two small directives for the V4 sections.
 *
 * v-in: adds `.in` once the element crosses into view, which starts its
 * choreographed entrance, then `.done` a beat later, which retires the
 * stagger delays so hovers on later siblings never lag behind the entrance.
 * With reduced motion both classes land at once and nothing moves.
 *
 * v-live: toggles `.live` while the element is on screen, so the section's
 * slow ambient loop runs only when someone can see it.
 */

const reduced = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

export const vIn = {
  mounted(el, binding) {
    const settle = binding.value?.settle ?? 1600
    if (reduced() || typeof IntersectionObserver === 'undefined') {
      el.classList.add('in', 'done')
      return
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return
        el.classList.add('in')
        el._z4done = setTimeout(() => el.classList.add('done'), settle)
        io.disconnect()
      },
      { rootMargin: '0px 0px -14% 0px', threshold: 0.05 },
    )
    io.observe(el)
    el._z4in = io
  },
  unmounted(el) {
    el._z4in?.disconnect()
    clearTimeout(el._z4done)
  },
}

export const vLive = {
  mounted(el) {
    if (typeof IntersectionObserver === 'undefined') {
      el.classList.add('live')
      return
    }
    const io = new IntersectionObserver(([entry]) => el.classList.toggle('live', entry.isIntersecting))
    io.observe(el)
    el._z4live = io
  },
  unmounted(el) {
    el._z4live?.disconnect()
  },
}
