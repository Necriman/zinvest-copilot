<script setup>
/**
 * The last word, over the hero's own resting frame: the tallest stack in warm
 * light, and the one button the whole page leads to in the dark space beside it.
 */
import { computed } from 'vue'

import { useAuthStore } from '@/store/auth'
import { vIn, vLive } from './inView'

const auth = useAuthStore()
const startTo = computed(() => (auth.isAuthenticated ? { name: 'dashboard' } : { name: 'register' }))
</script>

<template>
  <section v-in v-live class="zc">
    <div class="zc__bg" aria-hidden="true" />
    <div class="z4-wrap zc__copy">
      <h2 class="zc__title" data-in>{{ $t('v4.final.title') }}</h2>
      <p class="zc__body" data-in style="--i: 1">{{ $t('v4.final.body') }}</p>
      <div class="zc__ctas" data-in style="--i: 2">
        <RouterLink :to="startTo" class="z4-btn">{{ $t('v4.final.start') }}</RouterLink>
        <RouterLink v-if="!auth.isAuthenticated" :to="{ name: 'login' }" class="z4-btn z4-btn--ghost">
          {{ $t('v4.final.login') }}
        </RouterLink>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zc {
  position: relative;
  display: flex;
  align-items: center;
  min-height: min(52rem, 100vh);
  overflow: hidden;
  isolation: isolate;
}
.zc__bg {
  position: absolute;
  inset: 0;
  z-index: -1;
  background: var(--z4-canvas) url('/landing/v4/hero-end.jpg') 75% 50% / cover no-repeat;
  transform: scale(1.02);
}
.zc.live .zc__bg {
  animation: zc-drift 32s ease-in-out infinite alternate -8s;
}
@keyframes zc-drift {
  from {
    transform: scale(1.02) translateX(0);
  }
  to {
    transform: scale(1.07) translateX(-1%);
  }
}
.zc__bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(to bottom, var(--z4-canvas) 0%, rgba(15, 14, 20, 0) 22%),
    linear-gradient(to top, var(--z4-canvas) 0%, rgba(15, 14, 20, 0) 20%),
    linear-gradient(100deg, rgba(10, 9, 14, 0.8) 0%, rgba(10, 9, 14, 0.5) 38%, rgba(10, 9, 14, 0) 64%);
}
@media (max-width: 720px) {
  .zc__bg {
    background-image: url('/landing/v4/hero-end-portrait.jpg');
    background-position: 50% 100%;
  }
  .zc__bg::after {
    background:
      linear-gradient(to bottom, var(--z4-canvas) 0%, rgba(10, 9, 14, 0.72) 22%, rgba(10, 9, 14, 0.55) 50%, rgba(10, 9, 14, 0) 75%),
      linear-gradient(to top, var(--z4-canvas) 0%, rgba(15, 14, 20, 0) 20%);
  }
  .zc {
    align-items: flex-start;
    min-height: 44rem;
  }
}
.zc__copy {
  padding-block: 7rem;
  text-shadow: var(--z4-tshadow);
}
.zc__title {
  max-width: 14ch;
  font: 700 clamp(2.6rem, 1.5rem + 3.4vw, 4.8rem) / 1 var(--z4-display);
  font-variation-settings: 'SHRP' 60;
  letter-spacing: -0.035em;
  color: var(--z4-text);
  text-wrap: balance;
}
.zc__body {
  margin-top: 1.25rem;
  max-width: 34ch;
  font: 400 1.15rem/1.6 var(--z4-body);
  color: var(--z4-text-2);
}
.zc__ctas {
  margin-top: 2.25rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  text-shadow: none;
}
</style>
