<script setup>
/**
 * The questions people ask right before signing up, in one narrow centred
 * column. Answers open one at a time; the panel animates grid rows 0fr → 1fr
 * so nothing is measured in JS and the text stays findable in-page.
 */
import { ref, useId } from 'vue'

import { vIn } from './inView'

const QUESTIONS = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6']
const uid = useId()
const open = ref('q1')
const toggle = (key) => (open.value = open.value === key ? '' : key)
</script>

<template>
  <section id="faq" v-in class="z4-section zf scroll-mt-24">
    <div class="z4-wrap zf__wrap">
      <header class="zf__head">
        <p class="z4-kicker" data-in>{{ $t('v4.faq.eyebrow') }}</p>
        <h2 class="z4-h2" data-in style="--i: 1">{{ $t('v4.faq.title') }}</h2>
      </header>

      <div class="zf__list" data-in style="--i: 2">
        <div v-for="key in QUESTIONS" :key="key" class="zf__item" :data-open="open === key ? 'true' : undefined">
          <h3>
            <button
              :id="`${uid}-${key}-b`"
              type="button"
              class="zf__q"
              :aria-expanded="open === key"
              :aria-controls="`${uid}-${key}`"
              @click="toggle(key)"
            >
              <span>{{ $t(`v4.faq.${key}.q`) }}</span>
              <span class="zf__plus" aria-hidden="true"><i /><i /></span>
            </button>
          </h3>
          <div :id="`${uid}-${key}`" role="region" :aria-labelledby="`${uid}-${key}-b`" class="zf__panel">
            <div>
              <p class="zf__a">{{ $t(`v4.faq.${key}.a`) }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zf__wrap {
  max-width: 50rem;
}
.zf__head {
  text-align: center;
}
.zf__list {
  margin-top: 3rem;
  border-top: 1px solid var(--z4-line);
}
.zf__item {
  border-bottom: 1px solid var(--z4-line);
}
.zf__q {
  display: flex;
  width: 100%;
  min-height: 4.25rem;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 1.1rem 0.25rem;
  font: 600 clamp(1.08rem, 1rem + 0.3vw, 1.25rem) / 1.35 var(--z4-display);
  color: var(--z4-text);
  text-align: left;
  cursor: pointer;
}
.zf__q:focus-visible {
  outline: 2px solid var(--z4-gold);
  outline-offset: 4px;
  border-radius: 0.5rem;
}
.zf__plus {
  position: relative;
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 50%;
  border: 1px solid var(--z4-edge);
  transition: background-color 0.35s var(--z4-ease), border-color 0.35s var(--z4-ease);
}
.zf__plus i {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 0.8rem;
  height: 2px;
  margin: -1px 0 0 -0.4rem;
  border-radius: 2px;
  background: var(--z4-text);
  transition: transform 0.4s var(--z4-ease), background-color 0.35s var(--z4-ease);
}
.zf__plus i:nth-child(2) {
  transform: rotate(90deg);
}
.zf__item[data-open] .zf__plus {
  background: var(--z4-text);
  border-color: var(--z4-text);
}
.zf__item[data-open] .zf__plus i {
  background: var(--z4-canvas);
}
.zf__item[data-open] .zf__plus i:nth-child(2) {
  transform: rotate(0deg);
}
.zf__panel {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.4s var(--z4-ease);
}
.zf__item[data-open] .zf__panel {
  grid-template-rows: 1fr;
}
.zf__panel > div {
  overflow: hidden;
}
.zf__a {
  padding: 0 3.5rem 1.5rem 0.25rem;
  max-width: 60ch;
  font: 400 1.02rem/1.65 var(--z4-body);
  color: var(--z4-text-2);
}
@media (prefers-reduced-motion: reduce) {
  .zf__panel,
  .zf__plus,
  .zf__plus i {
    transition: none;
  }
}
</style>
