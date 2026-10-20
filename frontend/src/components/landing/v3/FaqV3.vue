<script setup>
/**
 * The questions people ask right before signing up: a puzzled bear and the
 * title on one side, chunky cards that open one at a time on the other. The
 * panel animates grid rows 0fr → 1fr, so the answer stays findable in-page.
 */
import { ref, useId } from 'vue'

import BearSticker from '@/components/mascot/BearSticker.vue'
import Icon from '@/components/ui/Icon.vue'

const QUESTIONS = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6']
const uid = useId()
const open = ref('q1')
const toggle = (key) => (open.value = open.value === key ? '' : key)
</script>

<template>
  <section id="faq" class="z3-section scroll-mt-24">
    <div class="z3-wrap zf">
      <div class="zf__side">
        <p class="z3-eyebrow">{{ $t('landing.faq.eyebrow') }}</p>
        <h2 class="z3-h2">{{ $t('landing.faq.title') }}</h2>
        <BearSticker name="confused" class="zf__bear" />
      </div>

      <div class="zf__list">
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
              <span>{{ $t(`landing.faq.${key}.q`) }}</span>
              <span class="zf__chev"><Icon name="chevronDown" class="h-5 w-5" /></span>
            </button>
          </h3>
          <div :id="`${uid}-${key}`" role="region" :aria-labelledby="`${uid}-${key}-b`" class="zf__panel">
            <div>
              <p class="zf__a">{{ $t(`landing.faq.${key}.a`) }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zf {
  display: grid;
  gap: 2.5rem;
}
@media (min-width: 1024px) {
  .zf {
    grid-template-columns: minmax(0, 0.7fr) minmax(0, 1fr);
    gap: 4rem;
    align-items: start;
  }
  .zf__side {
    position: sticky;
    top: 8rem;
  }
}
.zf__bear {
  display: none;
  width: 12rem;
  height: 12rem;
  margin-top: 1.5rem;
}
@media (min-width: 1024px) {
  .zf__bear {
    display: block;
  }
}
.zf__list {
  display: grid;
  gap: 0.9rem;
}
.zf__item {
  border-radius: 1.25rem;
  background: var(--z3-card);
  border: 2px solid var(--z3-card-edge);
  box-shadow: 0 5px 0 var(--z3-card-edge);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.zf__item[data-open] {
  border-color: color-mix(in oklab, var(--z3-purple) 45%, var(--z3-card-edge));
  box-shadow: 0 5px 0 color-mix(in oklab, var(--z3-purple) 45%, var(--z3-card-edge));
}
.zf__q {
  display: flex;
  width: 100%;
  min-height: 3.75rem;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  font: 800 1.05rem/1.35 var(--z3-font);
  color: var(--z3-ink);
  text-align: left;
  cursor: pointer;
}
.zf__q:focus-visible {
  outline: 3px solid var(--z3-blue);
  outline-offset: 3px;
  border-radius: 1.1rem;
}
.zf__chev {
  display: inline-flex;
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.75rem;
  background: var(--z3-purple-soft);
  color: var(--z3-purple);
  transition: transform 0.25s ease, background 0.15s;
}
.zf__item[data-open] .zf__chev {
  transform: rotate(180deg);
  background: var(--z3-purple);
  color: #fff;
}
.zf__panel {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.28s ease;
}
.zf__item[data-open] .zf__panel {
  grid-template-rows: 1fr;
}
.zf__panel > div {
  overflow: hidden;
}
.zf__a {
  padding: 0 1.25rem 1.25rem;
  font: 600 1rem/1.6 var(--z3-font);
  color: var(--z3-muted);
}
@media (prefers-reduced-motion: reduce) {
  .zf__panel,
  .zf__chev {
    transition: none;
  }
}
</style>
