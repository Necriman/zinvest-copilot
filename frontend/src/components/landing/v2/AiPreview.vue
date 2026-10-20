<script setup>
/**
 * Zinvest AI, shown by what it does rather than by the fact that it exists.
 *
 * One real question, one real answer, and then the three things a learner
 * actually asks next: say it simpler, show me an example, test me. Those are
 * live — pressing one rewrites the answer, with the same short thinking beat
 * the app has, because the claim being made is "it adapts to you", and a
 * static screenshot cannot make that claim honestly.
 */
import { computed, onBeforeUnmount, ref } from 'vue'

import AiAvatar from '@/components/ai/AiAvatar.vue'
import Icon from '@/components/ui/Icon.vue'
import Reveal from '../Reveal.vue'

const MODES = [
  { key: 'simpler', icon: 'sparkles' },
  { key: 'example', icon: 'chart' },
  { key: 'quiz', icon: 'target' },
]

// null = the original answer.
const mode = ref(null)
const thinking = ref(false)
const guess = ref(null)
let timer = null

const answerKey = computed(() => (mode.value ? `v2.ai.a_${mode.value}` : 'v2.ai.a'))

function ask(key) {
  if (mode.value === key) return
  clearTimeout(timer)
  guess.value = null
  thinking.value = true
  // Long enough to register as a response, short enough not to be a wait.
  timer = setTimeout(() => {
    mode.value = key
    thinking.value = false
  }, 520)
}

onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <section id="zinvest-ai" class="scroll-mt-28 px-6 py-20 sm:py-28">
    <div class="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1fr)] lg:items-center lg:gap-16">
      <div>
        <Reveal>
          <p class="text-xs font-bold uppercase tracking-[0.18em] text-brand-600 dark:text-brand-400">
            {{ $t('v2.ai.eyebrow') }}
          </p>
          <h2
            class="mt-4 max-w-[16ch] text-[2rem] font-extrabold leading-[1.08] tracking-[-0.03em] text-slate-900 sm:text-[2.6rem] dark:text-white"
          >
            {{ $t('v2.ai.title') }}
          </h2>
          <p class="mt-5 max-w-[40ch] text-base leading-[1.7] text-slate-500 dark:text-slate-400">
            {{ $t('v2.ai.body') }}
          </p>
        </Reveal>

      </div>

      <Reveal :delay="120">
        <div class="zai">
          <div class="zai__head">
            <AiAvatar class="h-8 w-8" />
            <span class="zai__name">{{ $t('v2.ai.eyebrow') }}</span>
            <span class="zai__unit">{{ $t('v2.ai.context') }}</span>
          </div>

          <p class="zai__q">{{ $t('v2.ai.q') }}</p>

          <div class="zai__reply">
            <AiAvatar class="mt-0.5 h-7 w-7 shrink-0" />

            <div class="min-w-0 flex-1">
              <p v-if="thinking" class="zai__typing" :aria-label="$t('v2.ai.thinking')">
                <span /><span /><span />
              </p>

              <template v-else>
                <p :key="answerKey" class="zai__a">{{ $t(answerKey) }}</p>

                <!-- Quiz mode answers back, so "test me" is not a promise. -->
                <div v-if="mode === 'quiz'" class="zai__quiz">
                  <button
                    v-for="n in 2"
                    :key="n"
                    type="button"
                    class="zai__opt"
                    :class="guess === n ? 'zai__opt--picked' : ''"
                    @click="guess = n"
                  >
                    {{ $t(`v2.ai.quizOpt${n}`) }}
                  </button>
                </div>
                <p v-if="mode === 'quiz' && guess" class="zai__verdict">
                  <Icon :name="guess === 2 ? 'checkCircle' : 'alert'" class="h-3.5 w-3.5 shrink-0" />
                  {{ $t(guess === 2 ? 'v2.ai.quizRight' : 'v2.ai.quizWrong') }}
                </p>
              </template>
            </div>
          </div>

          <!-- The invitation sits where the buttons are. On the far side of
               the section nobody read it: the eye is already in the panel. -->
          <p class="zai__nudge">{{ $t('v2.ai.nudge') }}</p>

          <div class="zai__chips">
            <button
              v-for="m in MODES"
              :key="m.key"
              type="button"
              class="zai__chip"
              :class="mode === m.key ? 'zai__chip--on' : ''"
              @click="ask(m.key)"
            >
              <Icon :name="m.icon" class="h-3.5 w-3.5" />
              {{ $t(`v2.ai.chip.${m.key}`) }}
            </button>
          </div>
        </div>
      </Reveal>
    </div>
  </section>
</template>

<style scoped>
.zai {
  border-radius: 1.5rem;
  border: 1px solid var(--color-hairline);
  background-color: color-mix(in oklab, var(--surface) 92%, transparent);
  padding: 1.15rem 1.25rem 1.25rem;
  box-shadow: 0 24px 60px -40px rgb(15 23 42 / 0.45);
}

.zai__head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding-bottom: 0.9rem;
  border-bottom: 1px solid var(--color-hairline);
}
.zai__name {
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--color-ink);
}
.zai__unit {
  margin-left: auto;
  border-radius: 999px;
  background: var(--surface-2);
  padding: 0.2rem 0.6rem;
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--color-ink-muted);
}

.zai__q {
  width: fit-content;
  max-width: 88%;
  margin-left: auto;
  margin-top: 1.1rem;
  border-radius: 1rem 1rem 0.3rem 1rem;
  background: var(--brand-600);
  padding: 0.6rem 0.9rem;
  font-size: 0.88rem;
  line-height: 1.5;
  color: #fff;
}

.zai__reply {
  display: flex;
  gap: 0.6rem;
  margin-top: 0.9rem;
  min-height: 5.5rem;
}
.zai__a {
  border-radius: 1rem 1rem 1rem 0.3rem;
  background: var(--surface-2);
  padding: 0.7rem 0.95rem;
  font-size: 0.88rem;
  line-height: 1.65;
  color: var(--color-ink);
  animation: zai-in 280ms var(--ease-out) both;
}
@keyframes zai-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
}

.zai__typing {
  display: inline-flex;
  gap: 0.25rem;
  border-radius: 1rem 1rem 1rem 0.3rem;
  background: var(--surface-2);
  padding: 0.85rem 0.95rem;
}
.zai__typing span {
  width: 0.33rem;
  aspect-ratio: 1;
  border-radius: 999px;
  background: var(--color-ink-faint);
  animation: zai-blink 1.1s ease-in-out infinite;
}
.zai__typing span:nth-child(2) {
  animation-delay: 0.16s;
}
.zai__typing span:nth-child(3) {
  animation-delay: 0.32s;
}
@keyframes zai-blink {
  0%,
  60%,
  100% {
    opacity: 0.3;
  }
  30% {
    opacity: 1;
  }
}

.zai__quiz {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.55rem;
}
.zai__opt {
  border-radius: 0.7rem;
  border: 1px solid var(--color-hairline);
  background: var(--surface);
  padding: 0.4rem 0.75rem;
  font-size: 0.8rem;
  color: var(--color-ink);
  transition:
    border-color 200ms ease,
    background-color 200ms ease;
}
.zai__opt:hover {
  border-color: color-mix(in oklab, var(--brand-500) 50%, transparent);
}
.zai__opt--picked {
  border-color: var(--brand-500);
  background: color-mix(in oklab, var(--brand-500) 10%, transparent);
}
.zai__opt:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
}
.zai__verdict {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  margin-top: 0.55rem;
  font-size: 0.8rem;
  line-height: 1.55;
  color: var(--color-ink-muted);
}

.zai__nudge {
  margin-top: 1.1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-hairline);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-ink-muted);
}

.zai__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.7rem;
}
.zai__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border-radius: 999px;
  border: 1px solid var(--color-hairline);
  padding: 0.42rem 0.85rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-ink-muted);
  transition:
    color 200ms ease,
    border-color 200ms ease,
    background-color 200ms ease,
    transform 200ms var(--ease-out);
}
.zai__chip:hover {
  transform: translateY(-1px);
  color: var(--color-ink);
  border-color: color-mix(in oklab, var(--brand-500) 50%, transparent);
}
.zai__chip--on {
  color: #fff;
  background: var(--brand-600);
  border-color: var(--brand-600);
}
.zai__chip--on:hover {
  color: #fff;
}
.zai__chip:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .zai__a {
    animation: none;
  }
  .zai__typing span {
    animation: none;
    opacity: 0.6;
  }
  .zai__chip:hover {
    transform: none;
  }
}
</style>
