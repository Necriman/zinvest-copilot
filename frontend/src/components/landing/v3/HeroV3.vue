<script setup>
/**
 * Hero: the promise on the left, on screen from the first paint (no reveal),
 * and the live bear on a podium on the right, presenting it, with the app's
 * own rewards (streak, coins, today's lesson) floating around him.
 */
import { computed } from 'vue'

import BearMascot from '@/components/mascot/BearMascot.vue'
import Icon from '@/components/ui/Icon.vue'
import { useAuthStore } from '@/store/auth'
import Icon3d from './Icon3d.vue'
import ZButton from './ZButton.vue'

const auth = useAuthStore()
const startTo = computed(() => (auth.isAuthenticated ? { name: 'dashboard' } : { name: 'register' }))
const TRUST = ['trust1', 'trust2', 'trust3']
</script>

<template>
  <section class="zh">
    <div class="zh__sky" aria-hidden="true">
      <span class="zh__blob zh__blob--a" />
      <span class="zh__blob zh__blob--b" />
    </div>

    <div class="z3-wrap zh__grid">
      <div class="zh__copy">
        <p class="zh__badge">
          <Icon3d name="book" class="h-6 w-6" />
          {{ $t('v3.hero.badge') }}
        </p>
        <h1 class="zh__title">
          {{ $t('v3.hero.title') }}
          <span class="zh__accent">{{ $t('v3.hero.accent') }}</span>
        </h1>
        <p class="zh__body">{{ $t('v3.hero.body') }}</p>

        <div class="zh__ctas">
          <ZButton :to="startTo">{{ $t('v3.hero.start') }}</ZButton>
          <ZButton v-if="!auth.isAuthenticated" :to="{ name: 'login' }" variant="secondary">
            {{ $t('v3.hero.login') }}
          </ZButton>
        </div>

        <ul class="zh__trust">
          <li v-for="key in TRUST" :key="key">
            <span class="zh__tick"><Icon name="check" class="h-3 w-3" /></span>
            {{ $t(`v3.hero.${key}`) }}
          </li>
        </ul>
      </div>

      <div class="zh__stage">
        <span class="zh__podium" aria-hidden="true" />
        <div class="zh__bear">
          <BearMascot mood="present" interactive />
        </div>

        <Icon3d name="coins" class="zh__deco zh__deco--coins z3-float" />
        <Icon3d name="growth" class="zh__deco zh__deco--growth z3-float" />
        <Icon3d name="shield" class="zh__deco zh__deco--shield z3-float" />

        <div class="zh__chip zh__chip--streak z3-float" aria-hidden="true">
          <Icon3d name="flame" class="h-8 w-8" />
          <span>{{ $t('v3.hero.chipStreak') }}</span>
        </div>
        <div class="zh__chip zh__chip--coins z3-float" aria-hidden="true">
          <Icon3d name="coins" class="h-7 w-7" />
          <span>{{ $t('v3.hero.chipCoins') }}</span>
        </div>
        <div class="zh__chip zh__chip--lesson z3-float" aria-hidden="true">
          <span class="zh__chipLabel">{{ $t('v3.hero.chipLessonLabel') }}</span>
          <span class="zh__chipTitle">{{ $t('v3.hero.chipLesson') }}</span>
          <span class="zh__bar"><i /></span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zh {
  position: relative;
  padding: 7.5rem 1.5rem 4.5rem;
  background: linear-gradient(180deg, var(--z3-purple-soft) 0%, var(--z3-bg) 100%);
  overflow: hidden;
}
@media (min-width: 1024px) {
  .zh {
    padding: 9rem 1.5rem 6rem;
  }
}
.zh__sky {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.zh__blob {
  position: absolute;
  border-radius: 999px;
  filter: blur(2px);
  opacity: 0.55;
}
.zh__blob--a {
  width: 26rem;
  height: 26rem;
  right: -6rem;
  top: 4rem;
  background: radial-gradient(circle at 40% 40%, color-mix(in oklab, var(--z3-yellow) 45%, transparent), transparent 70%);
}
.zh__blob--b {
  width: 22rem;
  height: 22rem;
  left: -8rem;
  bottom: -6rem;
  background: radial-gradient(circle at 50% 50%, color-mix(in oklab, var(--z3-blue) 30%, transparent), transparent 70%);
}
.zh__grid {
  position: relative;
  display: grid;
  gap: 2.5rem;
  align-items: center;
}
@media (min-width: 1024px) {
  .zh__grid {
    grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
    gap: 3rem;
  }
}
.zh__copy {
  text-align: center;
}
@media (min-width: 1024px) {
  .zh__copy {
    text-align: left;
  }
}
.zh__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.9rem 0.35rem 0.45rem;
  border-radius: 999px;
  background: var(--z3-card);
  border: 2px solid var(--z3-line);
  font: 800 0.85rem/1.2 var(--z3-font);
  color: var(--z3-purple);
}
.zh__title {
  margin-top: 1.25rem;
  font: 900 clamp(2.4rem, 1.5rem + 3.8vw, 4.1rem) / 1.02 var(--z3-font);
  letter-spacing: -0.025em;
  color: var(--z3-ink);
  text-wrap: balance;
}
.zh__accent {
  display: block;
  color: var(--z3-purple);
}
.zh__body {
  margin: 1.25rem auto 0;
  max-width: 36ch;
  font: 600 1.15rem/1.6 var(--z3-font);
  color: var(--z3-muted);
}
@media (min-width: 1024px) {
  .zh__body {
    margin-left: 0;
  }
}
.zh__ctas {
  margin-top: 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  max-width: 22rem;
  margin-inline: auto;
}
.zh__ctas > * {
  width: 100%;
}
@media (min-width: 640px) {
  .zh__ctas {
    flex-direction: row;
    max-width: none;
    justify-content: center;
  }
  .zh__ctas > * {
    width: auto;
  }
}
@media (min-width: 1024px) {
  .zh__ctas {
    justify-content: flex-start;
  }
}
.zh__trust {
  margin-top: 1.6rem;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.6rem 1.25rem;
  font: 700 0.9rem/1.2 var(--z3-font);
  color: var(--z3-muted);
}
@media (min-width: 1024px) {
  .zh__trust {
    justify-content: flex-start;
  }
}
.zh__trust li {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}
.zh__tick {
  display: inline-flex;
  width: 1.25rem;
  height: 1.25rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--z3-green);
  color: #fff;
}

/* --- the stage --- */
.zh__stage {
  position: relative;
  height: 22rem;
  max-width: 30rem;
  width: 100%;
  margin: 0 auto;
}
@media (min-width: 640px) {
  .zh__stage {
    height: 28rem;
  }
}
@media (min-width: 1024px) {
  .zh__stage {
    height: 34rem;
  }
}
.zh__podium {
  position: absolute;
  left: 50%;
  bottom: 4%;
  width: 62%;
  height: 12%;
  transform: translateX(-50%);
  border-radius: 50%;
  background: radial-gradient(ellipse at 50% 35%, color-mix(in oklab, var(--z3-purple) 30%, var(--z3-card)), var(--z3-purple-soft) 70%);
  box-shadow: 0 10px 0 color-mix(in oklab, var(--z3-purple) 25%, transparent);
}
.zh__bear {
  position: absolute;
  inset: 0 12% 5% 12%;
}
.zh__deco {
  position: absolute;
  width: 4.5rem;
  height: 4.5rem;
  filter: drop-shadow(0 10px 14px rgba(40, 20, 90, 0.18));
}
@media (min-width: 1024px) {
  .zh__deco {
    width: 5.5rem;
    height: 5.5rem;
  }
}
.zh__deco--coins {
  left: 0;
  top: 10%;
  --z3-rot: -10deg;
  animation-delay: -1.2s;
}
.zh__deco--growth {
  right: 0;
  top: 2%;
  --z3-rot: 8deg;
  animation-delay: -2.6s;
}
.zh__deco--shield {
  left: 4%;
  bottom: 18%;
  width: 3.5rem;
  height: 3.5rem;
  --z3-rot: -6deg;
  animation-delay: -0.4s;
}
.zh__chip {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.9rem 0.5rem 0.55rem;
  border-radius: 1rem;
  background: var(--z3-card);
  border: 2px solid var(--z3-line);
  box-shadow: 0 4px 0 var(--z3-card-edge);
  font: 800 0.9rem/1.1 var(--z3-font);
  color: var(--z3-ink);
  white-space: nowrap;
}
.zh__chip--streak {
  right: -2%;
  top: 34%;
  animation-delay: -1.8s;
}
.zh__chip--coins {
  left: -4%;
  top: 42%;
  color: #a46a00;
  animation-delay: -3.1s;
}
.dark .zh__chip--coins {
  color: var(--z3-yellow);
}
.zh__chip--lesson {
  right: 2%;
  bottom: 10%;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.3rem;
  padding: 0.65rem 0.9rem;
  animation-delay: -0.9s;
}
.zh__chipLabel {
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--z3-muted);
}
.zh__chipTitle {
  font-size: 0.95rem;
}
.zh__bar {
  display: block;
  width: 9rem;
  height: 0.6rem;
  border-radius: 999px;
  background: var(--z3-line);
  overflow: hidden;
}
.zh__bar i {
  display: block;
  width: 62%;
  height: 100%;
  border-radius: inherit;
  background: var(--z3-green);
}
@media (max-width: 639px) {
  .zh__chip--lesson {
    display: none;
  }
}
</style>
