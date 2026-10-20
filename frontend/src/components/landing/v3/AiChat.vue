<script setup>
/**
 * Zinvest AI on a dark brand band: a real question, the bear's answer, and the
 * three things a learner asks next. The chips work — each one rewrites the
 * answer after a short typing beat, and "test me" answers back.
 */
import { computed, onBeforeUnmount, ref } from 'vue'

import BearSticker from '@/components/mascot/BearSticker.vue'
import Icon from '@/components/ui/Icon.vue'
import Reveal from '../Reveal.vue'
import Icon3d from './Icon3d.vue'

const MODES = [
  { key: 'simpler', icon: 'sparkles' },
  { key: 'example', icon: 'chart' },
  { key: 'quiz', icon: 'target' },
]
const mode = ref(null)
const thinking = ref(false)
const guess = ref(null)
let timer = null
const answerKey = computed(() => (mode.value ? `v2.ai.a_${mode.value}` : 'v2.ai.a'))

function ask(key) {
  if (mode.value === key || thinking.value) return
  clearTimeout(timer)
  guess.value = null
  thinking.value = true
  timer = setTimeout(() => {
    mode.value = key
    thinking.value = false
  }, 650)
}
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <section id="zinvest-ai" class="z3-section za scroll-mt-24">
    <Icon3d name="book" class="za__deco za__deco--a z3-float" />
    <Icon3d name="growth" class="za__deco za__deco--b z3-float" />

    <div class="z3-wrap za__grid">
      <div>
        <p class="z3-eyebrow za__eyebrow">{{ $t('v2.ai.eyebrow') }}</p>
        <h2 class="z3-h2 za__title">{{ $t('v2.ai.title') }}</h2>
        <p class="z3-lede za__lede">{{ $t('v2.ai.body') }}</p>
        <BearSticker name="think" class="za__bear" />
      </div>

      <Reveal :delay="100">
        <div class="za__chat">
          <div class="za__head">
            <img src="/mascot/ai-avatar-96.webp" alt="" class="za__avatar" width="96" height="96" />
            <div class="min-w-0">
              <p class="za__name">{{ $t('v2.ai.eyebrow') }}</p>
              <p class="za__ctx">{{ $t('v2.ai.context') }}</p>
            </div>
          </div>

          <div class="za__log" aria-live="polite">
            <p class="za__msg za__msg--me">{{ $t('v2.ai.q') }}</p>
            <div class="za__row">
              <img src="/mascot/ai-avatar-96.webp" alt="" class="za__mini" width="96" height="96" />
              <div class="za__msg za__msg--bear">
                <p v-if="thinking" class="za__typing" :aria-label="$t('v2.ai.thinking')"><i /><i /><i /></p>
                <template v-else>
                  <p :key="answerKey" class="za__a">{{ $t(answerKey) }}</p>
                  <div v-if="mode === 'quiz'" class="za__quiz">
                    <button
                      v-for="n in 2"
                      :key="n"
                      type="button"
                      class="za__opt"
                      :data-state="guess === n ? (n === 2 ? 'right' : 'wrong') : undefined"
                      @click="guess = n"
                    >
                      {{ $t(`v2.ai.quizOpt${n}`) }}
                    </button>
                  </div>
                  <p v-if="mode === 'quiz' && guess" class="za__verdict" :data-state="guess === 2 ? 'right' : 'wrong'">
                    <Icon :name="guess === 2 ? 'checkCircle' : 'alert'" class="h-4 w-4 shrink-0" />
                    {{ $t(guess === 2 ? 'v2.ai.quizRight' : 'v2.ai.quizWrong') }}
                  </p>
                </template>
              </div>
            </div>
          </div>

          <p class="za__nudge">{{ $t('v2.ai.nudge') }}</p>
          <div class="za__chips">
            <button
              v-for="m in MODES"
              :key="m.key"
              type="button"
              class="za__chip"
              :aria-pressed="mode === m.key"
              @click="ask(m.key)"
            >
              <Icon :name="m.icon" class="h-4 w-4" />
              {{ $t(`v2.ai.chip.${m.key}`) }}
            </button>
          </div>
        </div>
      </Reveal>
    </div>
  </section>
</template>

<style scoped>
.za {
  background: radial-gradient(120% 90% at 85% 0%, #3b2a8f 0%, #231a5c 45%, #17123d 100%);
  color: #fff;
  overflow: hidden;
}
.za__deco {
  position: absolute;
  width: 4.5rem;
  height: 4.5rem;
  opacity: 0.9;
  pointer-events: none;
}
.za__deco--a {
  right: 3%;
  top: 1.5rem;
  --z3-rot: -12deg;
}
.za__deco--b {
  left: 36%;
  bottom: 2.5rem;
  --z3-rot: 10deg;
  animation-delay: -2s;
}
@media (max-width: 767px) {
  .za__deco {
    display: none;
  }
}
.za__grid {
  position: relative;
  display: grid;
  gap: 3rem;
  align-items: center;
}
@media (min-width: 1024px) {
  .za__grid {
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1fr);
    gap: 4rem;
  }
}
.za__eyebrow {
  color: var(--z3-yellow);
}
.za__title {
  color: #fff;
}
.za__lede {
  color: #cfc8f5;
}
.za__bear {
  display: none;
  width: 10rem;
  height: 10rem;
  margin-top: 1.5rem;
}
@media (min-width: 1024px) {
  .za__bear {
    display: block;
  }
}
.za__chat {
  border-radius: 1.75rem;
  background: var(--z3-card);
  color: var(--z3-ink);
  border: 2px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 8px 0 rgba(0, 0, 0, 0.35);
  padding: 1.25rem 1.25rem 1.4rem;
}
.za__head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid var(--z3-line);
}
.za__avatar {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 999px;
  background: var(--z3-purple-soft);
}
.za__name {
  font: 900 1rem/1.2 var(--z3-font);
}
.za__ctx {
  font: 700 0.82rem/1.2 var(--z3-font);
  color: var(--z3-muted);
}
.za__log {
  display: grid;
  gap: 0.9rem;
  padding: 1.1rem 0 0.4rem;
}
.za__msg {
  max-width: 88%;
  padding: 0.8rem 1rem;
  border-radius: 1.2rem;
  font: 600 1rem/1.55 var(--z3-font);
}
.za__msg--me {
  justify-self: end;
  background: var(--z3-purple);
  color: #fff;
  border-bottom-right-radius: 0.35rem;
  font-weight: 700;
}
.za__row {
  display: flex;
  align-items: flex-end;
  gap: 0.55rem;
}
.za__mini {
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;
  border-radius: 999px;
  background: var(--z3-purple-soft);
}
.za__msg--bear {
  background: var(--z3-purple-soft);
  border-bottom-left-radius: 0.35rem;
  color: var(--z3-ink);
}
.za__a {
  animation: za-in 0.25s ease-out;
}
@keyframes za-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: none; }
}
.za__typing {
  display: flex;
  gap: 0.3rem;
  padding: 0.35rem 0.1rem;
}
.za__typing i {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 999px;
  background: var(--z3-purple);
  animation: za-dot 0.9s ease-in-out infinite;
}
.za__typing i:nth-child(2) { animation-delay: 0.15s; }
.za__typing i:nth-child(3) { animation-delay: 0.3s; }
@keyframes za-dot {
  0%, 100% { opacity: 0.3; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(-3px); }
}
.za__quiz {
  margin-top: 0.75rem;
  display: grid;
  gap: 0.5rem;
}
.za__opt {
  min-height: 2.75rem;
  padding: 0.55rem 0.85rem;
  border-radius: 0.85rem;
  border: 2px solid var(--z3-card-edge);
  background: var(--z3-card);
  box-shadow: 0 3px 0 var(--z3-card-edge);
  font: 800 0.95rem/1.3 var(--z3-font);
  text-align: left;
  color: var(--z3-ink);
}
.za__opt[data-state='right'] {
  border-color: var(--z3-green);
  background: var(--z3-green-soft);
  color: var(--z3-green-ink);
}
.za__opt[data-state='wrong'] {
  border-color: var(--z3-coral);
  background: var(--z3-coral-soft);
  color: var(--z3-coral-ink);
}
.za__verdict {
  margin-top: 0.6rem;
  display: flex;
  gap: 0.45rem;
  font: 700 0.92rem/1.45 var(--z3-font);
  color: var(--z3-green-ink);
}
.za__verdict[data-state='wrong'] {
  color: var(--z3-coral-ink);
}
.za__nudge {
  margin-top: 0.9rem;
  font: 700 0.85rem/1.4 var(--z3-font);
  color: var(--z3-muted);
}
.za__chips {
  margin-top: 0.6rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}
.za__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 2.75rem;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  border: 2px solid var(--z3-card-edge);
  background: var(--z3-card);
  box-shadow: 0 3px 0 var(--z3-card-edge);
  font: 800 0.92rem/1 var(--z3-font);
  color: var(--z3-purple);
  transition: transform 0.08s, box-shadow 0.08s;
}
.za__chip:active {
  transform: translateY(3px);
  box-shadow: none;
}
.za__chip[aria-pressed='true'] {
  background: var(--z3-purple);
  border-color: var(--z3-purple);
  box-shadow: 0 3px 0 var(--z3-purple-edge);
  color: #fff;
}
.za__chip:focus-visible,
.za__opt:focus-visible {
  outline: 3px solid var(--z3-blue);
  outline-offset: 3px;
}
@media (prefers-reduced-motion: reduce) {
  .za__a,
  .za__typing i {
    animation: none;
  }
}
</style>
