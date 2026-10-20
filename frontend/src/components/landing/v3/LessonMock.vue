<script setup>
/**
 * A lesson you can play on the landing: three questions from real lessons, the
 * Duolingo loop of pick → check → feedback sheet → continue, and the bear
 * beside it reacting. The explanation after each answer is the point: that is
 * what Zinvest does differently, so the demo shows it rather than claims it.
 */
import { computed, ref } from 'vue'

import BearSticker from '@/components/mascot/BearSticker.vue'
import Icon from '@/components/ui/Icon.vue'
import { useAuthStore } from '@/store/auth'
import Icon3d from './Icon3d.vue'
import ZButton from './ZButton.vue'

// index of the right answer per question (the strings live in v3.lesson.qN)
const QUESTIONS = [
  { key: 'q1', right: 1 },
  { key: 'q2', right: 2 },
  { key: 'q3', right: 0 },
]
const TOTAL = QUESTIONS.length

const auth = useAuthStore()
const startTo = computed(() => (auth.isAuthenticated ? { name: 'dashboard' } : { name: 'register' }))

const index = ref(0)
const picked = ref(null)
const checked = ref(false)
const score = ref(0)
const done = ref(false)

const q = computed(() => QUESTIONS[index.value])
const correct = computed(() => checked.value && picked.value === q.value.right)
const progress = computed(() => (done.value ? 1 : (index.value + (checked.value ? 1 : 0)) / TOTAL))
const bear = computed(() => {
  if (done.value) return 'celebrate'
  if (!checked.value) return picked.value === null ? 'think' : 'eager'
  return correct.value ? 'happy' : 'confused'
})

function pick(i) {
  if (!checked.value) picked.value = i
}
function check() {
  if (picked.value === null) return
  checked.value = true
  if (picked.value === q.value.right) score.value++
}
function next() {
  if (index.value + 1 >= TOTAL) {
    done.value = true
    return
  }
  index.value++
  picked.value = null
  checked.value = false
}
function restart() {
  index.value = 0
  picked.value = null
  checked.value = false
  score.value = 0
  done.value = false
}
function optionState(i) {
  if (!checked.value) return picked.value === i ? 'picked' : ''
  if (i === q.value.right) return 'right'
  return picked.value === i ? 'wrong' : 'dim'
}
</script>

<template>
  <section id="try" class="z3-section zl scroll-mt-24">
    <div class="z3-wrap zl__grid">
      <div class="zl__copy">
        <p class="z3-eyebrow">{{ $t('v3.lesson.eyebrow') }}</p>
        <h2 class="z3-h2">{{ $t('v3.lesson.title') }}</h2>
        <p class="z3-lede">{{ $t('v3.lesson.body') }}</p>
        <ul class="zl__points">
          <li v-for="p in ['p1', 'p2', 'p3']" :key="p">
            <span class="zl__tick"><Icon name="check" class="h-3.5 w-3.5" /></span>
            {{ $t(`v3.lesson.${p}`) }}
          </li>
        </ul>
        <BearSticker :name="bear" :key="bear" pop class="zl__bear" />
      </div>

      <div class="zl__card">
        <!-- top bar: restart and progress -->
        <div class="zl__top">
          <button type="button" class="zl__x" :aria-label="$t('v3.lesson.close')" @click="restart">
            <Icon name="x" class="h-5 w-5" />
          </button>
          <div
            class="zl__progress"
            role="progressbar"
            :aria-valuenow="Math.round(progress * 100)"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="$t('v3.lesson.progress', { n: Math.min(index + 1, TOTAL), total: TOTAL })"
          >
            <i :style="{ width: `${progress * 100}%` }" />
          </div>
          <span class="zl__coins"><Icon3d name="coins" class="h-6 w-6" />{{ score * 10 }}</span>
        </div>

        <!-- finished -->
        <div v-if="done" class="zl__done">
          <Icon3d name="trophy" class="zl__trophy" />
          <h3 class="zl__doneTitle">{{ $t('v3.lesson.doneTitle') }}</h3>
          <p class="zl__doneBody">{{ $t('v3.lesson.doneBody', { n: score, total: TOTAL }) }}</p>
          <div class="zl__doneActions">
            <ZButton :to="startTo" block>{{ $t('v3.lesson.cta') }}</ZButton>
            <ZButton variant="secondary" block @click="restart">{{ $t('v3.lesson.again') }}</ZButton>
          </div>
        </div>

        <!-- a question -->
        <template v-else>
          <div class="zl__body">
            <p class="zl__pick">{{ $t('v3.lesson.pick') }}</p>
            <h3 class="zl__q">{{ $t(`v3.lesson.${q.key}.q`) }}</h3>
            <div class="zl__options" role="radiogroup" :aria-label="$t(`v3.lesson.${q.key}.q`)">
              <button
                v-for="(n, i) in 3"
                :key="`${q.key}-${i}`"
                type="button"
                role="radio"
                :aria-checked="picked === i"
                class="zl__opt"
                :data-state="optionState(i)"
                :disabled="checked"
                @click="pick(i)"
              >
                <span class="zl__key">{{ n }}</span>
                {{ $t(`v3.lesson.${q.key}.a${n}`) }}
              </button>
            </div>
          </div>

          <div class="zl__foot" :data-state="checked ? (correct ? 'right' : 'wrong') : ''" aria-live="polite">
            <div v-if="checked" class="zl__verdict">
              <span class="zl__badge"><Icon :name="correct ? 'check' : 'x'" class="h-5 w-5" /></span>
              <div>
                <p class="zl__verdictTitle">{{ $t(correct ? 'v3.lesson.right' : 'v3.lesson.wrong') }}</p>
                <p class="zl__why">{{ $t(`v3.lesson.${q.key}.why`) }}</p>
              </div>
            </div>
            <ZButton v-if="!checked" variant="green" block :disabled="picked === null" @click="check">
              {{ $t('v3.lesson.check') }}
            </ZButton>
            <ZButton v-else :variant="correct ? 'green' : 'primary'" block @click="next">
              {{ $t('v3.lesson.next') }}
            </ZButton>
          </div>
        </template>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zl {
  background: var(--z3-blue-soft);
}
.zl__grid {
  display: grid;
  gap: 3rem;
  align-items: center;
}
@media (min-width: 1024px) {
  .zl__grid {
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1fr);
    gap: 4rem;
  }
}
.zl__points {
  margin-top: 1.5rem;
  display: grid;
  gap: 0.75rem;
  font: 700 1.02rem/1.4 var(--z3-font);
  color: var(--z3-ink);
}
.zl__points li {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}
.zl__tick {
  display: inline-flex;
  flex-shrink: 0;
  width: 1.6rem;
  height: 1.6rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--z3-blue);
  color: #fff;
}
.zl__bear {
  display: none;
  width: 11rem;
  height: 11rem;
  margin-top: 1.5rem;
}
@media (min-width: 1024px) {
  .zl__bear {
    display: block;
  }
}

/* --- the lesson card --- */
.zl__card {
  display: flex;
  flex-direction: column;
  min-height: 34rem;
  border-radius: 1.75rem;
  background: var(--z3-card);
  border: 2px solid var(--z3-card-edge);
  box-shadow: 0 8px 0 var(--z3-card-edge);
  overflow: hidden;
}
.zl__top {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem 1.5rem 0.5rem;
}
.zl__x {
  display: inline-flex;
  width: 2.75rem;
  height: 2.75rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 0.8rem;
  color: var(--z3-muted);
  transition: background 0.15s;
}
.zl__x:hover {
  background: var(--z3-line);
}
.zl__progress {
  flex: 1;
  height: 1rem;
  border-radius: 999px;
  background: var(--z3-line);
  overflow: hidden;
}
.zl__progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--z3-green);
  box-shadow: inset 0 -4px 0 rgba(0, 0, 0, 0.08), inset 0 3px 0 rgba(255, 255, 255, 0.35);
  transition: width 0.45s cubic-bezier(0.34, 1.4, 0.64, 1);
}
.zl__coins {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font: 900 1rem/1 var(--z3-font);
  color: #b27a00;
  min-width: 3.2rem;
}
.dark .zl__coins {
  color: var(--z3-yellow);
}
.zl__body {
  flex: 1;
  padding: 1rem 1.5rem 1.5rem;
}
.zl__pick {
  display: inline-block;
  padding: 0.3rem 0.7rem;
  border-radius: 0.6rem;
  background: var(--z3-purple-soft);
  font: 800 0.78rem/1 var(--z3-font);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--z3-purple);
}
.zl__q {
  margin-top: 0.9rem;
  font: 800 1.35rem/1.35 var(--z3-font);
  color: var(--z3-ink);
}
.zl__options {
  margin-top: 1.4rem;
  display: grid;
  gap: 0.75rem;
}
.zl__opt {
  --b: var(--z3-card-edge);
  --bg: var(--z3-card);
  --c: var(--z3-ink);
  display: flex;
  align-items: center;
  gap: 0.85rem;
  width: 100%;
  min-height: 3.5rem;
  padding: 0.8rem 1rem;
  border-radius: 1rem;
  border: 2px solid var(--b);
  background: var(--bg);
  box-shadow: 0 4px 0 var(--b);
  font: 700 1.02rem/1.35 var(--z3-font);
  color: var(--c);
  text-align: left;
  cursor: pointer;
  transition: transform 0.08s, box-shadow 0.08s, background 0.15s, border-color 0.15s;
}
.zl__opt:hover:not(:disabled) {
  background: color-mix(in oklab, var(--z3-card) 90%, var(--z3-blue));
}
.zl__opt:active:not(:disabled) {
  transform: translateY(3px);
  box-shadow: 0 1px 0 var(--b);
}
.zl__opt:focus-visible {
  outline: 3px solid var(--z3-blue);
  outline-offset: 3px;
}
.zl__opt:disabled {
  cursor: default;
}
.zl__opt[data-state='picked'] {
  --b: var(--z3-blue);
  --bg: var(--z3-blue-soft);
  --c: var(--z3-blue-edge);
}
.dark .zl__opt[data-state='picked'] {
  --c: #8cc8ff;
}
.zl__opt[data-state='right'] {
  --b: var(--z3-green);
  --bg: var(--z3-green-soft);
  --c: var(--z3-green-ink);
}
.zl__opt[data-state='wrong'] {
  --b: var(--z3-coral);
  --bg: var(--z3-coral-soft);
  --c: var(--z3-coral-ink);
}
.zl__opt[data-state='dim'] {
  opacity: 0.55;
}
.zl__key {
  display: inline-flex;
  flex-shrink: 0;
  width: 1.9rem;
  height: 1.9rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.55rem;
  border: 2px solid var(--b);
  font: 900 0.85rem/1 var(--z3-font);
  color: var(--c);
}

/* --- footer: check, then the feedback sheet --- */
.zl__foot {
  padding: 1.25rem 1.5rem 1.5rem;
  border-top: 2px solid var(--z3-line);
  transition: background 0.2s;
}
.zl__foot[data-state='right'] {
  background: var(--z3-green-soft);
  border-top-color: transparent;
}
.zl__foot[data-state='wrong'] {
  background: var(--z3-coral-soft);
  border-top-color: transparent;
}
.zl__verdict {
  display: flex;
  gap: 0.85rem;
  margin-bottom: 1rem;
  animation: zl-up 0.28s cubic-bezier(0.34, 1.4, 0.64, 1);
}
.zl__badge {
  display: inline-flex;
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--z3-green);
  color: #fff;
}
.zl__foot[data-state='wrong'] .zl__badge {
  background: var(--z3-coral);
}
.zl__verdictTitle {
  font: 900 1.25rem/1.2 var(--z3-font);
  color: var(--z3-green-ink);
}
.zl__foot[data-state='wrong'] .zl__verdictTitle {
  color: var(--z3-coral-ink);
}
.zl__why {
  margin-top: 0.3rem;
  font: 600 0.98rem/1.5 var(--z3-font);
  color: var(--z3-ink);
}
@keyframes zl-up {
  from { transform: translateY(10px); opacity: 0; }
  to { transform: none; opacity: 1; }
}

/* --- done --- */
.zl__done {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1.75rem 2.25rem;
  text-align: center;
}
.zl__trophy {
  width: 8rem;
  height: 8rem;
  animation: zl-pop 0.5s cubic-bezier(0.34, 1.6, 0.64, 1);
}
.zl__doneTitle {
  margin-top: 1rem;
  font: 900 2rem/1.1 var(--z3-font);
  color: var(--z3-ink);
}
.zl__doneBody {
  margin-top: 0.6rem;
  max-width: 30ch;
  font: 600 1.05rem/1.5 var(--z3-font);
  color: var(--z3-muted);
}
.zl__doneActions {
  margin-top: 1.75rem;
  display: grid;
  gap: 0.9rem;
  width: 100%;
  max-width: 20rem;
}
@keyframes zl-pop {
  from { transform: scale(0.4) rotate(-12deg); opacity: 0; }
  to { transform: none; opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .zl__verdict,
  .zl__trophy {
    animation: none;
  }
  .zl__progress i {
    transition: none;
  }
}
</style>
