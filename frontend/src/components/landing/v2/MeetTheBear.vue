<script setup>
/**
 * The guide.
 *
 * This is the only section where the mascot is the subject rather than the
 * host, so he gets the room — and he gets it by being live and pokeable, not
 * by being large. Three lines beside him say where he actually turns up in
 * the product, which is what makes him a character instead of a logo.
 */
import BearMascot from '@/components/mascot/BearMascot.vue'
import Reveal from '../Reveal.vue'

// `interactive` already picks its own reaction on each tap and never repeats
// the last one, so there is nothing to add here.
const WHERE = ['w1', 'w2', 'w3']
</script>

<template>
  <section class="px-6 py-20 sm:py-28">
    <div class="mx-auto grid max-w-6xl items-center gap-10 sm:gap-14 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1fr)]">
      <Reveal class="order-2 lg:order-1">
        <!-- Live, centred, and reacting when touched: the invitation is the
             behaviour itself, which is why there is no tooltip asking for a tap. -->
        <div class="zmb__stage">
          <div class="zmb__glow" aria-hidden="true" />
          <!-- "Your guide": a paw on the chest and a small bow. -->
          <BearMascot mood="introduce" interactive class="zmb__bear" />
        </div>
      </Reveal>

      <div class="order-1 lg:order-2">
        <Reveal>
          <p class="text-xs font-bold uppercase tracking-[0.18em] text-brand-600 dark:text-brand-400">
            {{ $t('v2.bear.eyebrow') }}
          </p>
          <h2
            class="mt-4 max-w-[14ch] text-[2rem] font-extrabold leading-[1.08] tracking-[-0.03em] text-slate-900 sm:text-[2.6rem] dark:text-white"
          >
            {{ $t('v2.bear.title') }}
          </h2>
          <p class="mt-5 max-w-[40ch] text-base leading-[1.7] text-slate-500 dark:text-slate-400">
            {{ $t('v2.bear.body') }}
          </p>
        </Reveal>

        <Reveal :delay="120">
          <ul class="zmb__where">
            <li v-for="key in WHERE" :key="key">{{ $t(`v2.bear.${key}`) }}</li>
          </ul>
        </Reveal>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zmb__stage {
  position: relative;
  width: 100%;
  max-width: 24rem;
  margin-inline: auto;
  aspect-ratio: 1;
}
.zmb__glow {
  position: absolute;
  inset: 4% 0 0;
  pointer-events: none;
  background: radial-gradient(
    52% 44% at 50% 46%,
    color-mix(in oklab, var(--brand-500) 15%, transparent),
    transparent 70%
  );
  filter: blur(8px);
}
.dark .zmb__glow {
  opacity: 0.9;
}
.zmb__bear {
  position: absolute;
  inset: 0;
}

.zmb__where {
  display: grid;
  gap: 0.55rem;
  margin-top: 1.85rem;
  border-top: 1px solid var(--color-hairline);
  padding-top: 1.35rem;
}
.zmb__where li {
  position: relative;
  padding-left: 1.1rem;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--color-ink-muted);
}
.zmb__where li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.62rem;
  width: 0.32rem;
  aspect-ratio: 1;
  border-radius: 999px;
  background: color-mix(in oklab, var(--brand-500) 70%, transparent);
}
</style>
