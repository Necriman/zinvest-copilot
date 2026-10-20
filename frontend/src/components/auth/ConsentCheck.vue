<script setup>
/**
 * One sign-up consent: a real checkbox (keyboard, screen reader and focus ring
 * come with it) and a label that may hold links, given through the slot. Never
 * pre-ticked: the person ticks it themselves.
 */
const model = defineModel({ type: Boolean, default: false })
defineProps({
  invalid: { type: Boolean, default: false }, // tried to submit without it
})
</script>

<template>
  <label class="cc" :data-invalid="invalid || null">
    <input v-model="model" type="checkbox" class="cc__input" :aria-invalid="invalid || undefined" />
    <span class="cc__box" aria-hidden="true">
      <svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
    </span>
    <span class="cc__text"><slot /></span>
  </label>
</template>

<style scoped>
.cc {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  cursor: pointer;
  font-size: 0.85rem;
  line-height: 1.45;
  color: var(--text-muted);
}
.cc__input {
  position: absolute;
  opacity: 0;
  width: 1px;
  height: 1px;
}
.cc__box {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 1.25rem;
  height: 1.25rem;
  margin-top: 0.05rem;
  border-radius: 0.4rem;
  border: 2px solid var(--border);
  background: var(--surface);
  transition: background 0.15s ease, border-color 0.15s ease;
}
.cc__box svg {
  width: 0.85rem;
  height: 0.85rem;
  fill: none;
  stroke: #fff;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0;
}
.cc__input:checked + .cc__box {
  background: var(--brand-600);
  border-color: var(--brand-600);
}
.cc__input:checked + .cc__box svg {
  opacity: 1;
}
.cc__input:focus-visible + .cc__box {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
}
.cc[data-invalid] .cc__input:not(:checked) + .cc__box {
  border-color: #e5484d;
}
.cc__text :deep(a) {
  color: var(--brand-600);
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
