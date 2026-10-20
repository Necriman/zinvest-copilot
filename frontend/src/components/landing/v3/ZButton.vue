<script setup>
/**
 * The chunky button: a solid face on a darker "edge" that it sinks into when
 * pressed, like a key. `to` makes a router link, `href` a plain link.
 */
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  to: { type: [String, Object], default: null },
  href: { type: String, default: '' },
  variant: { type: String, default: 'primary' }, // primary | secondary | yellow | green
  size: { type: String, default: 'lg' }, // md | lg
  block: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})

const tag = computed(() => (props.to ? RouterLink : props.href ? 'a' : 'button'))
const attrs = computed(() => {
  if (props.to) return { to: props.to }
  if (props.href) return { href: props.href }
  return { type: 'button', disabled: props.disabled }
})
</script>

<template>
  <component
    :is="tag"
    v-bind="attrs"
    class="zbtn"
    :class="[`zbtn--${variant}`, `zbtn--${size}`, { 'zbtn--block': block }]"
  >
    <slot />
  </component>
</template>

<style scoped>
.zbtn {
  --face: var(--z3-purple);
  --edge: var(--z3-purple-edge);
  --text: #fff;
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 3rem;
  border-radius: 1rem;
  background: var(--face);
  color: var(--text);
  font: 800 0.95rem/1.1 var(--z3-font);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  text-align: center;
  box-shadow: 0 5px 0 var(--edge);
  transform: translateY(0);
  transition: transform 0.08s ease-out, box-shadow 0.08s ease-out, filter 0.15s ease;
  cursor: pointer;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}
.zbtn:hover {
  filter: brightness(1.06);
}
.zbtn:active:not(:disabled) {
  transform: translateY(5px);
  box-shadow: 0 0 0 var(--edge);
}
.zbtn:focus-visible {
  outline: 3px solid var(--z3-blue);
  outline-offset: 4px;
}
.zbtn:disabled {
  cursor: not-allowed;
  --face: var(--z3-line);
  --edge: var(--z3-card-edge);
  --text: var(--z3-muted);
}
.zbtn--md {
  min-height: 2.75rem;
  padding: 0.7rem 1.25rem;
  font-size: 0.85rem;
}
.zbtn--lg {
  padding: 1rem 1.6rem;
}
.zbtn--block {
  display: flex;
  width: 100%;
}
.zbtn--secondary {
  --face: var(--z3-card);
  --edge: var(--z3-card-edge);
  --text: var(--z3-purple);
  border: 2px solid var(--z3-card-edge);
  box-shadow: 0 4px 0 var(--z3-card-edge);
}
.zbtn--secondary:active:not(:disabled) {
  transform: translateY(4px);
}
.zbtn--yellow {
  --face: var(--z3-yellow);
  --edge: var(--z3-yellow-edge);
  --text: #2a2107;
}
.zbtn--green {
  --face: var(--z3-green);
  --edge: var(--z3-green-edge);
  --text: #fff;
}
@media (prefers-reduced-motion: reduce) {
  .zbtn {
    transition: none;
  }
}
</style>
