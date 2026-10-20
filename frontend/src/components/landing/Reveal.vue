<script setup>
/**
 * Fades + lifts its slot into view once, the first time it crosses the
 * viewport. Purely decorative: the content is in the DOM and readable from the
 * first paint, so a blocked observer or reduced-motion just means it's already
 * visible rather than missing.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  // Stagger within a group of siblings, in ms.
  delay: { type: Number, default: 0 },
  as: { type: String, default: 'div' },
})

const root = ref(null)
const shown = ref(false)
let observer = null

onMounted(() => {
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (reduced || typeof IntersectionObserver === 'undefined') {
    shown.value = true
    return
  }
  observer = new IntersectionObserver(
    ([entry]) => {
      if (!entry.isIntersecting) return
      shown.value = true
      observer.disconnect()
      observer = null
    },
    // Fire slightly before the element is fully on screen, so the motion has
    // finished by the time it's centred.
    { rootMargin: '0px 0px -12% 0px', threshold: 0.05 },
  )
  observer.observe(root.value)
})

onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <component
    :is="props.as"
    ref="root"
    class="zx-reveal"
    :class="shown ? 'zx-reveal-in' : ''"
    :style="{ transitionDelay: `${props.delay}ms` }"
  >
    <slot />
  </component>
</template>
