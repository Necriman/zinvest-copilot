<script setup>
/**
 * What the lessons are about, as a band that keeps moving (the first list is
 * the one read aloud; the copy that makes the loop seamless is hidden). It
 * stops on hover and does not move at all with reduced motion.
 */
const TOPICS = [
  { key: 'budget', icon: 'coins' },
  { key: 'emergency', icon: 'shield' },
  { key: 'investing', icon: 'growth' },
  { key: 'credit', icon: 'card' },
  { key: 'goals', icon: 'target' },
  { key: 'startup', icon: 'rocket' },
  { key: 'inflation', icon: 'flame' },
  { key: 'saving', icon: 'piggy' },
]
</script>

<template>
  <section class="zt" :aria-label="$t('v3.topics.label')">
    <div class="zt__track">
      <ul v-for="copy in 2" :key="copy" class="zt__list" :aria-hidden="copy === 2 ? 'true' : undefined">
        <li v-for="t in TOPICS" :key="t.key" class="zt__item">
          <img :src="`/icons3d/${t.icon}.webp`" alt="" class="zt__icon" width="256" height="256" loading="lazy" decoding="async" />
          {{ $t(`v3.topics.${t.key}`) }}
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.zt {
  position: relative;
  background: var(--z3-purple);
  color: #fff;
  overflow: hidden;
  padding: 1.1rem 0;
  box-shadow: inset 0 -6px 0 var(--z3-purple-edge);
}
.zt__track {
  display: flex;
  width: max-content;
  animation: zt-slide 38s linear infinite;
}
.zt:hover .zt__track {
  animation-play-state: paused;
}
.zt__list {
  display: flex;
  flex-shrink: 0;
}
.zt__item {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0 1.75rem;
  font: 800 1.15rem/1 var(--z3-font);
  white-space: nowrap;
}
.zt__icon {
  width: 2.4rem;
  height: 2.4rem;
  object-fit: contain;
  filter: drop-shadow(0 4px 6px rgba(20, 5, 60, 0.3));
}
@keyframes zt-slide {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
@media (prefers-reduced-motion: reduce) {
  .zt__track {
    animation: none;
    width: auto;
    flex-wrap: wrap;
    justify-content: center;
  }
  .zt__list {
    flex-wrap: wrap;
    justify-content: center;
    row-gap: 0.75rem;
  }
  .zt__list[aria-hidden='true'] {
    display: none;
  }
}
</style>
