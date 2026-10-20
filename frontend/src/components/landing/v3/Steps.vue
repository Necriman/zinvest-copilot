<script setup>
/**
 * How it works: three cards, each with the bear climbing out of its top edge in
 * the pose of that step (reading, rubbing his paws before trying, presenting
 * the answer). The cards are chunky and coloured; the words are the headline.
 */
import BearSticker from '@/components/mascot/BearSticker.vue'
import Reveal from '../Reveal.vue'

const STEPS = [
  { key: 's1', sticker: 'book', tone: 'purple' },
  { key: 's2', sticker: 'eager', tone: 'yellow' },
  { key: 's3', sticker: 'present', tone: 'green' },
]
</script>

<template>
  <section id="how-it-works" class="z3-section scroll-mt-24">
    <div class="z3-wrap">
      <div class="text-center">
        <p class="z3-eyebrow">{{ $t('v3.steps.eyebrow') }}</p>
        <h2 class="z3-h2 mx-auto max-w-[20ch]">{{ $t('v3.steps.title') }}</h2>
      </div>

      <ol class="zst">
        <Reveal v-for="(s, i) in STEPS" :key="s.key" as="li" :delay="i * 90" class="zst__item">
          <article class="zst__card" :data-tone="s.tone">
            <BearSticker :name="s.sticker" class="zst__bear" />
            <span class="zst__num">{{ i + 1 }}</span>
            <h3 class="zst__word">{{ $t(`v3.steps.${s.key}.word`) }}</h3>
            <p class="zst__body">{{ $t(`v3.steps.${s.key}.body`) }}</p>
          </article>
        </Reveal>
      </ol>
    </div>
  </section>
</template>

<style scoped>
.zst {
  margin-top: 6rem;
  display: grid;
  gap: 6.5rem;
}
@media (min-width: 768px) {
  .zst {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1.5rem;
  }
}
.zst__item {
  display: flex;
}
.zst__card {
  --tint: var(--z3-purple-soft);
  --ink: var(--z3-purple);
  --edge: color-mix(in oklab, var(--z3-purple) 22%, var(--z3-card-edge));
  position: relative;
  flex: 1;
  padding: 5.5rem 1.75rem 2rem;
  border-radius: 1.75rem;
  background: var(--tint);
  border: 2px solid var(--edge);
  box-shadow: 0 6px 0 var(--edge);
  text-align: center;
}
.zst__card[data-tone='yellow'] {
  --tint: var(--z3-yellow-soft);
  --ink: #b47c00;
  --edge: color-mix(in oklab, var(--z3-yellow) 45%, var(--z3-card-edge));
}
.dark .zst__card[data-tone='yellow'] {
  --ink: var(--z3-yellow);
}
.zst__card[data-tone='green'] {
  --tint: var(--z3-green-soft);
  --ink: var(--z3-green-ink);
  --edge: color-mix(in oklab, var(--z3-green) 35%, var(--z3-card-edge));
}
.zst__bear {
  position: absolute;
  left: 50%;
  top: 0;
  width: 9.5rem;
  height: 9.5rem;
  transform: translate(-50%, -58%);
  filter: drop-shadow(0 10px 12px rgba(40, 20, 90, 0.15));
}
.zst__num {
  position: absolute;
  left: 1.25rem;
  top: 1.25rem;
  display: inline-flex;
  width: 2.25rem;
  height: 2.25rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--z3-card);
  border: 2px solid var(--edge);
  font: 900 1rem/1 var(--z3-font);
  color: var(--ink);
}
.zst__word {
  font: 900 clamp(1.9rem, 1.4rem + 1.5vw, 2.4rem) / 1.05 var(--z3-font);
  letter-spacing: -0.02em;
  color: var(--ink);
}
.zst__body {
  margin-top: 0.8rem;
  font: 600 1.02rem/1.6 var(--z3-font);
  color: var(--z3-muted);
}
</style>
