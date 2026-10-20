<script setup>
/**
 * The wait screen for the long jobs (a study plan, a market check): the bear
 * thinking, the steps of the job lighting up one after another, a running
 * bar, and a plain line about how long it usually takes. The steps follow a
 * clock, not the server (which reports nothing until it is done), so the last
 * one holds until the answer arrives instead of pretending to finish.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

import BearMascot from '@/components/mascot/BearMascot.vue'
import Icon from '@/components/ui/Icon.vue'

const props = defineProps({
  title: { type: String, required: true },
  steps: { type: Array, required: true }, // strings, in order
  note: { type: String, default: '' }, // "usually up to 20 seconds"
  stepMs: { type: Number, default: 3500 },
})

const at = ref(0)
let timer = null

onMounted(() => {
  timer = setInterval(() => {
    if (at.value < props.steps.length - 1) at.value++
    else clearInterval(timer)
  }, props.stepMs)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="bt" role="status" aria-live="polite">
    <div class="bt__bear" aria-hidden="true"><BearMascot mood="think" /></div>
    <h2 class="bt__title">{{ title }}</h2>
    <div class="bt__bar" aria-hidden="true"><span /></div>
    <ol class="bt__steps">
      <li v-for="(step, i) in steps" :key="i" :data-state="i < at ? 'done' : i === at ? 'now' : 'later'">
        <span class="bt__dot">
          <Icon v-if="i < at" name="check" class="h-3 w-3" />
          <i v-else-if="i === at" />
        </span>
        {{ step }}
      </li>
    </ol>
    <p v-if="note" class="bt__note">{{ note }}</p>
  </div>
</template>

<style scoped>
.bt {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem 1rem;
  text-align: center;
}
.bt__bear {
  width: 9rem;
  height: 11rem;
}
.bt__title {
  margin-top: 0.75rem;
  font-size: 1.2rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--text);
}
.bt__bar {
  position: relative;
  width: min(18rem, 100%);
  height: 0.4rem;
  margin-top: 1rem;
  border-radius: 99px;
  background: var(--surface-2);
  overflow: hidden;
}
.bt__bar span {
  position: absolute;
  inset: 0 auto 0 0;
  width: 40%;
  border-radius: inherit;
  background: linear-gradient(90deg, transparent, var(--brand-500), transparent);
  animation: bt-run 1.4s ease-in-out infinite;
}
@keyframes bt-run {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(250%);
  }
}
.bt__steps {
  margin-top: 1.25rem;
  display: grid;
  gap: 0.55rem;
  text-align: left;
}
.bt__steps li {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  font-size: 0.92rem;
  color: var(--text-faint);
  transition: color 0.3s ease;
}
.bt__steps li[data-state='done'] {
  color: var(--text-muted);
}
.bt__steps li[data-state='now'] {
  color: var(--text);
  font-weight: 600;
}
.bt__dot {
  display: grid;
  place-items: center;
  width: 1.3rem;
  height: 1.3rem;
  flex-shrink: 0;
  border-radius: 50%;
  border: 1.5px solid var(--border);
}
[data-state='done'] .bt__dot {
  border-color: transparent;
  background: var(--brand-600);
  color: #fff;
}
[data-state='now'] .bt__dot {
  border-color: var(--brand-500);
}
.bt__dot i {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--brand-500);
  animation: bt-pulse 1s ease-in-out infinite;
}
@keyframes bt-pulse {
  50% {
    transform: scale(0.5);
    opacity: 0.5;
  }
}
.bt__note {
  margin-top: 1.1rem;
  font-size: 0.8rem;
  color: var(--text-faint);
}
@media (prefers-reduced-motion: reduce) {
  .bt__bar span,
  .bt__dot i {
    animation: none;
  }
  .bt__bar span {
    width: 100%;
    opacity: 0.4;
  }
}
</style>
