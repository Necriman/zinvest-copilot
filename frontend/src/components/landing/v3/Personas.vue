<script setup>
/**
 * Who it is for: four starting points, each a card in its own colour with the
 * bear holding the thing that goes with it — the student's book, the first pay
 * packet's coin, the founder's tablet, the self-taught investor's phone. A
 * swipeable row on phones, four columns on wide screens.
 */
import BearSticker from '@/components/mascot/BearSticker.vue'
import Reveal from '../Reveal.vue'

const PEOPLE = [
  { key: 'w1', sticker: 'book', tone: 'purple' },
  { key: 'w2', sticker: 'coin', tone: 'yellow' },
  { key: 'w3', sticker: 'tablet', tone: 'blue' },
  { key: 'w4', sticker: 'phone', tone: 'green' },
]
</script>

<template>
  <section id="who-its-for" class="z3-section zw scroll-mt-24">
    <div class="z3-wrap">
      <div class="zw__head">
        <p class="z3-eyebrow">{{ $t('landing.who.eyebrow') }}</p>
        <h2 class="z3-h2 max-w-[18ch]">{{ $t('landing.who.title') }}</h2>
        <p class="z3-lede">{{ $t('landing.who.subtitle') }}</p>
      </div>

      <ul class="zw__row">
        <Reveal v-for="(p, i) in PEOPLE" :key="p.key" as="li" :delay="i * 70" class="zw__cell">
          <article class="zw__card" :data-tone="p.tone">
            <BearSticker :name="p.sticker" class="zw__bear" />
            <h3 class="zw__title">{{ $t(`landing.who.${p.key}.title`) }}</h3>
            <p class="zw__body">{{ $t(`landing.who.${p.key}.body`) }}</p>
          </article>
        </Reveal>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.zw {
  background: var(--z3-yellow-soft);
}
.zw__head {
  max-width: 40rem;
}
.zw__row {
  margin: 3rem -1.5rem 0;
  padding: 0.5rem 1.5rem 1.25rem;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(16rem, 78%);
  gap: 1.1rem;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scrollbar-width: none;
}
.zw__row::-webkit-scrollbar {
  display: none;
}
@media (min-width: 1024px) {
  .zw__row {
    margin: 3.5rem 0 0;
    padding: 0.5rem 0 0.5rem;
    grid-auto-flow: row;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    overflow: visible;
  }
}
.zw__cell {
  display: flex;
  scroll-snap-align: start;
}
.zw__card {
  --tint: var(--z3-purple);
  --edge: var(--z3-purple-edge);
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 1.25rem 1.4rem 1.6rem;
  border-radius: 1.75rem;
  background: var(--tint);
  box-shadow: 0 7px 0 var(--edge);
  color: #fff;
}
.zw__card[data-tone='yellow'] {
  --tint: var(--z3-yellow);
  --edge: var(--z3-yellow-edge);
  color: #2a2107;
}
.zw__card[data-tone='blue'] {
  --tint: var(--z3-blue);
  --edge: var(--z3-blue-edge);
  color: #0a2440; /* white on this blue is under 4.5:1 */
}
.zw__card[data-tone='green'] {
  --tint: var(--z3-green);
  --edge: var(--z3-green-edge);
  color: #06331a;
}
.zw__bear {
  width: 10rem;
  height: 10rem;
  margin: -0.25rem auto 0.25rem;
  filter: drop-shadow(0 8px 10px rgba(0, 0, 0, 0.18));
}
.zw__title {
  font: 900 1.35rem/1.2 var(--z3-font);
}
.zw__body {
  margin-top: 0.55rem;
  font: 600 0.98rem/1.55 var(--z3-font);
  opacity: 0.92;
}
</style>
