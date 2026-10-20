<script setup>
/**
 * The route, drawn the way it looks in a game: round nodes winding down the
 * page under coloured unit banners — done, the one you are on (with the bear
 * pointing at it), the ones ahead, and the unit test at the end.
 */
import BearSticker from '@/components/mascot/BearSticker.vue'
import Icon from '@/components/ui/Icon.vue'
import Reveal from '../Reveal.vue'
import Icon3d from './Icon3d.vue'

// x offset of each node, in rem: a gentle S down the column
const SWAY = [0, 3.5, 5, 3.5, 0, -3.5, -5, -3.5]

const UNITS = [
  {
    key: 'unit1',
    tone: 'purple',
    icon: 'book',
    nodes: [
      { state: 'done', title: 'v2.path.n1.title' },
      { state: 'done', title: 'v2.path.n2.title' },
      { state: 'now', title: 'v3.hero.chipLesson' },
      { state: 'ahead', title: 'v2.path.n3.title' },
      { state: 'test', title: 'v2.path.n4.title' },
    ],
  },
  {
    key: 'unit2',
    tone: 'blue',
    icon: 'growth',
    nodes: [
      { state: 'ahead', title: 'v2.path.n5.title' },
      { state: 'ahead', title: 'v2.path.n6.title' },
      { state: 'test', title: 'v2.path.n4.title' },
    ],
  },
]

const STATE_LABEL = { done: 'v3.path.done', now: 'v3.path.now', ahead: 'v3.path.ahead', test: 'v3.path.test' }
let n = 0
const sway = () => SWAY[n++ % SWAY.length]
const units = UNITS.map((u) => ({ ...u, nodes: u.nodes.map((node) => ({ ...node, x: sway() })) }))
</script>

<template>
  <section id="path" class="z3-section scroll-mt-24">
    <div class="z3-wrap zp">
      <div class="zp__copy">
        <p class="z3-eyebrow">{{ $t('v3.path.eyebrow') }}</p>
        <h2 class="z3-h2">{{ $t('v2.path.title') }}</h2>
        <p class="z3-lede">{{ $t('v2.path.body') }}</p>
        <ul class="zp__points">
          <li v-for="(p, i) in ['p1', 'p2', 'p3']" :key="p">
            <Icon3d :name="['target', 'growth', 'trophy'][i]" class="h-10 w-10 shrink-0" />
            {{ $t(`v3.path.${p}`) }}
          </li>
        </ul>
      </div>

      <div class="zp__route">
        <div v-for="u in units" :key="u.key" class="zp__unit">
          <Reveal>
            <div class="zp__banner" :data-tone="u.tone">
              <span>{{ $t(`v3.path.${u.key}`) }}</span>
              <Icon3d :name="u.icon" class="h-11 w-11" />
            </div>
          </Reveal>
          <ol class="zp__nodes">
            <li
              v-for="(node, i) in u.nodes"
              :key="i"
              class="zp__slot"
              :style="{ transform: `translateX(${node.x}rem)` }"
            >
              <Reveal :delay="i * 60">
                <div class="zp__node" :data-state="node.state" :title="$t(node.title)">
                  <span class="sr-only">{{ $t(STATE_LABEL[node.state]) }}: {{ $t(node.title) }}</span>
                  <Icon v-if="node.state === 'done'" name="check" class="h-8 w-8" />
                  <Icon v-else-if="node.state === 'now'" name="play" class="h-8 w-8" />
                  <Icon3d v-else-if="node.state === 'test'" name="trophy" class="h-12 w-12" />
                  <Icon v-else name="lock" class="h-7 w-7" />
                </div>
                <div v-if="node.state === 'now'" class="zp__bubble" aria-hidden="true">
                  <span class="zp__bubbleTitle">{{ $t(node.title) }}</span>
                  <span class="zp__bubbleGo">{{ $t('v3.path.start') }}</span>
                </div>
                <BearSticker v-if="node.state === 'now'" name="point" class="zp__bear" />
              </Reveal>
            </li>
          </ol>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zp {
  display: grid;
  gap: 3.5rem;
}
@media (min-width: 1024px) {
  .zp {
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1fr);
    gap: 4rem;
    align-items: start;
  }
  .zp__copy {
    position: sticky;
    top: 8rem;
  }
}
.zp__points {
  margin-top: 1.75rem;
  display: grid;
  gap: 0.9rem;
  font: 700 1.02rem/1.4 var(--z3-font);
  color: var(--z3-ink);
}
.zp__points li {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.zp__route {
  display: grid;
  gap: 2.5rem;
  max-width: 26rem;
  width: 100%;
  margin: 0 auto;
}
.zp__banner {
  --face: var(--z3-purple);
  --edge: var(--z3-purple-edge);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.9rem 1rem 0.9rem 1.25rem;
  border-radius: 1.1rem;
  background: var(--face);
  box-shadow: 0 5px 0 var(--edge);
  font: 900 1.1rem/1.2 var(--z3-font);
  color: #fff;
}
.zp__banner[data-tone='blue'] {
  --face: var(--z3-blue);
  --edge: var(--z3-blue-edge);
}
.zp__nodes {
  margin-top: 2rem;
  display: grid;
  justify-items: center;
  gap: 1.35rem;
}
.zp__slot {
  position: relative;
}
/* room above the current node for its "start" bubble */
.zp__slot:has(.zp__node[data-state='now']) {
  margin-top: 3.75rem;
}
.zp__node {
  --face: var(--z3-line);
  --edge: var(--z3-card-edge);
  --ink: var(--z3-muted);
  position: relative;
  display: flex;
  width: 4.75rem;
  height: 4.25rem;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--face);
  box-shadow: 0 7px 0 var(--edge);
  color: var(--ink);
}
.zp__node[data-state='done'] {
  --face: var(--z3-yellow);
  --edge: var(--z3-yellow-edge);
  --ink: #fff;
}
.zp__node[data-state='now'] {
  --face: var(--z3-purple);
  --edge: var(--z3-purple-edge);
  --ink: #fff;
  outline: 6px solid color-mix(in oklab, var(--z3-purple) 22%, transparent);
  outline-offset: 5px;
}
.zp__node[data-state='test'] {
  --face: var(--z3-yellow-soft);
  --edge: color-mix(in oklab, var(--z3-yellow) 50%, var(--z3-card-edge));
}
.zp__bubble {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 1.1rem);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  padding: 0.55rem 1rem;
  border-radius: 0.9rem;
  background: var(--z3-card);
  border: 2px solid var(--z3-card-edge);
  box-shadow: 0 4px 0 var(--z3-card-edge);
  white-space: nowrap;
  transform: translateX(-50%);
  animation: zp-bob 1.6s ease-in-out infinite;
}
.zp__bubble::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 100%;
  width: 0.9rem;
  height: 0.9rem;
  background: var(--z3-card);
  border-right: 2px solid var(--z3-card-edge);
  border-bottom: 2px solid var(--z3-card-edge);
  transform: translate(-50%, -45%) rotate(45deg);
}
.zp__bubbleTitle {
  font: 800 0.85rem/1.2 var(--z3-font);
  color: var(--z3-muted);
}
.zp__bubbleGo {
  font: 900 0.95rem/1.2 var(--z3-font);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--z3-purple);
}
.zp__bear {
  position: absolute;
  right: calc(100% + 0.5rem);
  top: 50%;
  width: 7.5rem;
  height: 7.5rem;
  transform: translateY(-55%) scaleX(1);
}
@keyframes zp-bob {
  0%, 100% { transform: translate(-50%, 0); }
  50% { transform: translate(-50%, -5px); }
}
@media (prefers-reduced-motion: reduce) {
  .zp__bubble {
    animation: none;
  }
}
</style>
