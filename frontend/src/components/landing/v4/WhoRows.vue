<script setup>
/**
 * Who it is for, as an editorial list: four full-width rows, a mono index,
 * the title set large, the body beside it. No cards and no images: after the
 * phone the page goes quiet and typographic for a moment.
 */
import { vIn } from './inView'

const ROWS = ['w1', 'w2', 'w3', 'w4']
</script>

<template>
  <section id="who-its-for" v-in class="z4-section zw scroll-mt-24">
    <div class="z4-wrap">
      <header class="zw__head">
        <p class="z4-kicker" data-in>{{ $t('v4.who.eyebrow') }}</p>
        <h2 class="z4-h2 zw__title" data-in style="--i: 1">{{ $t('v4.who.title') }}</h2>
        <p class="z4-lede" data-in style="--i: 2">{{ $t('v4.who.subtitle') }}</p>
      </header>

      <ul class="zw__list">
        <li v-for="(key, i) in ROWS" :key="key" class="zw__row" data-in :style="{ '--i': i + 3 }">
          <span class="zw__n">{{ String(i + 1).padStart(2, '0') }}</span>
          <h3 class="zw__t">{{ $t(`v4.who.${key}.title`) }}</h3>
          <p class="zw__b">{{ $t(`v4.who.${key}.body`) }}</p>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.zw__head {
  display: grid;
  gap: 0;
}
@media (min-width: 960px) {
  .zw__head {
    grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
    column-gap: 4rem;
    align-items: end;
  }
  .zw__head .z4-kicker {
    grid-column: 1 / -1;
  }
  .zw__head .z4-lede {
    margin-top: 0;
    justify-self: end;
  }
}
.zw__title {
  max-width: 17ch;
}

.zw__list {
  margin-top: 3.5rem;
  border-top: 1px solid var(--z4-line);
}
.zw__row {
  position: relative;
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr);
  column-gap: 1rem;
  row-gap: 0.6rem;
  padding: 1.8rem 0;
  border-bottom: 1px solid var(--z4-line);
  align-items: baseline;
}
@media (min-width: 960px) {
  .zw__row {
    grid-template-columns: 5rem minmax(0, 1.1fr) minmax(0, 1fr);
    column-gap: 2rem;
    padding: 2.4rem 1rem;
  }
}
/* A soft light that follows the row under the pointer. */
.zw__row::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: 1.25rem;
  background: linear-gradient(90deg, rgba(111, 85, 224, 0.14), rgba(111, 85, 224, 0));
  opacity: 0;
  transition: opacity 0.45s var(--z4-ease);
}
.zw__row {
  isolation: isolate;
}
@media (hover: hover) {
  .zw__row:hover::before {
    opacity: 1;
  }
  .zw__row:hover .zw__t {
    transform: translateX(0.4rem);
  }
}
.zw__n {
  font: 500 0.85rem/1 var(--z4-mono);
  color: var(--z4-violet-2);
}
.zw__t {
  font: 650 clamp(1.6rem, 1.2rem + 1.5vw, 2.5rem) / 1.08 var(--z4-display);
  font-variation-settings: 'SHRP' 60;
  letter-spacing: -0.03em;
  color: var(--z4-text);
  transition: transform 0.5s var(--z4-ease);
}
.zw__b {
  grid-column: 2;
  max-width: 44ch;
  font: 400 1.02rem/1.6 var(--z4-body);
  color: var(--z4-text-2);
}
@media (min-width: 960px) {
  .zw__b {
    grid-column: 3;
  }
}
</style>
