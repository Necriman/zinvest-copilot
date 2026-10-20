<script setup>
/**
 * Learn → Practise → Understand → Apply.
 *
 * Four steps, no four cards. A single rule runs through all of them and each
 * step is marked on it, so the eye reads a sequence rather than a row of
 * equally weighted boxes. The rule fills as the section comes into view: the
 * only motion here, and it says the one thing the layout cannot — that these
 * happen in an order.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

import Icon from '@/components/ui/Icon.vue'
import Reveal from '../Reveal.vue'

const STEPS = [
  { key: 'learn', icon: 'book' },
  { key: 'practice', icon: 'target' },
  { key: 'understand', icon: 'bot' },
  { key: 'apply', icon: 'chart' },
]

const root = ref(null)
const drawn = ref(false)
let observer = null

onMounted(() => {
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (reduced || typeof IntersectionObserver === 'undefined') {
    drawn.value = true
    return
  }
  observer = new IntersectionObserver(
    ([entry]) => {
      if (!entry.isIntersecting) return
      drawn.value = true
      observer.disconnect()
      observer = null
    },
    { rootMargin: '0px 0px -20% 0px', threshold: 0.15 },
  )
  observer.observe(root.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <section id="how-it-works" ref="root" class="scroll-mt-28 px-6 py-20 sm:py-28">
    <div class="mx-auto max-w-6xl">
      <Reveal>
        <p class="text-xs font-bold uppercase tracking-[0.18em] text-brand-600 dark:text-brand-400">
          {{ $t('v2.flow.eyebrow') }}
        </p>
        <h2
          class="mt-4 max-w-[20ch] text-[2rem] font-extrabold leading-[1.08] tracking-[-0.03em] text-slate-900 sm:text-[2.6rem] dark:text-white"
        >
          {{ $t('v2.flow.title') }}
        </h2>
      </Reveal>

      <ol class="zf" :class="drawn ? 'zf--drawn' : ''">
        <Reveal v-for="(step, i) in STEPS" :key="step.key" as="li" :delay="i * 90" class="zf__step">
          <span class="zf__dot" aria-hidden="true">
            <Icon :name="step.icon" class="h-3.5 w-3.5" />
          </span>
          <p class="zf__n">{{ String(i + 1).padStart(2, '0') }}</p>
          <p class="zf__word">{{ $t(`v2.flow.${step.key}.word`) }}</p>
          <p class="zf__body">{{ $t(`v2.flow.${step.key}.body`) }}</p>
        </Reveal>
      </ol>
    </div>
  </section>
</template>

<style scoped>
.zf {
  position: relative;
  display: grid;
  gap: 2.25rem;
  margin-top: 3.5rem;
  padding-left: 2.25rem;
}
/* The rule: vertical while stacked, horizontal once the steps sit in a row. */
.zf::before,
.zf::after {
  content: '';
  position: absolute;
  left: 0.44rem;
  top: 0.4rem;
  bottom: 0.4rem;
  width: 1px;
}
.zf::before {
  background: var(--color-hairline);
}
.zf::after {
  background: color-mix(in oklab, var(--brand-500) 65%, transparent);
  transform: scaleY(0);
  transform-origin: top;
  transition: transform 1100ms var(--ease-out) 120ms;
}
.zf--drawn::after {
  transform: scaleY(1);
}

.zf__step {
  position: relative;
}
.zf__dot {
  position: absolute;
  left: -2.25rem;
  top: 0.05rem;
  display: grid;
  place-items: center;
  width: 1.55rem;
  aspect-ratio: 1;
  border-radius: 999px;
  border: 1px solid var(--color-hairline);
  background: var(--surface);
  color: var(--color-ink-muted);
  transform: translateX(-0.33rem);
  transition:
    color 300ms ease,
    border-color 300ms ease;
}
.zf--drawn .zf__dot {
  color: var(--brand-600);
  border-color: color-mix(in oklab, var(--brand-500) 45%, transparent);
}
.dark .zf--drawn .zf__dot {
  color: var(--brand-400);
}

.zf__n {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  color: var(--color-ink-faint);
}
.zf__word {
  margin-top: 0.3rem;
  font-size: clamp(1.35rem, 3.4vw, 1.75rem);
  font-weight: 800;
  letter-spacing: -0.025em;
  line-height: 1.1;
  color: var(--color-ink);
}
.zf__body {
  margin-top: 0.55rem;
  max-width: 34ch;
  font-size: 0.92rem;
  line-height: 1.65;
  color: var(--color-ink-muted);
}

@media (min-width: 900px) {
  .zf {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 2rem;
    padding-left: 0;
    padding-top: 2.75rem;
  }
  .zf::before,
  .zf::after {
    left: 0;
    right: 0;
    top: 0.44rem;
    bottom: auto;
    width: auto;
    height: 1px;
  }
  .zf::after {
    transform: scaleX(0);
    transform-origin: left;
  }
  .zf--drawn::after {
    transform: scaleX(1);
  }
  .zf__dot {
    left: 0;
    top: -2.75rem;
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .zf::after {
    transition: none;
  }
}
</style>
