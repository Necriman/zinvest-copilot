<script setup>
/**
 * The last word: a big purple slab, the live bear beckoning, the rewards
 * floating around him, and the one button that matters in the arrow's yellow.
 */
import { computed } from 'vue'

import BearMascot from '@/components/mascot/BearMascot.vue'
import { useAuthStore } from '@/store/auth'
import Icon3d from './Icon3d.vue'
import ZButton from './ZButton.vue'

const auth = useAuthStore()
const startTo = computed(() => (auth.isAuthenticated ? { name: 'dashboard' } : { name: 'register' }))
</script>

<template>
  <section class="z3-section zc">
    <div class="z3-wrap">
      <div class="zc__slab">
        <Icon3d name="gift" class="zc__deco zc__deco--gift z3-float" />
        <Icon3d name="rocket" class="zc__deco zc__deco--rocket z3-float" />
        <Icon3d name="coins" class="zc__deco zc__deco--coins z3-float" />

        <div class="zc__bear">
          <BearMascot mood="invite" :decorations="false" />
        </div>
        <div class="zc__copy">
          <h2 class="zc__title">{{ $t('v3.cta.title') }}</h2>
          <p class="zc__body">{{ $t('v3.cta.body') }}</p>
          <div class="zc__ctas">
            <ZButton :to="startTo" variant="yellow">{{ $t('v3.hero.start') }}</ZButton>
            <ZButton v-if="!auth.isAuthenticated" :to="{ name: 'login' }" variant="secondary">
              {{ $t('v3.hero.login') }}
            </ZButton>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zc {
  padding-top: 2rem;
}
.zc__slab {
  position: relative;
  display: grid;
  gap: 1rem;
  align-items: center;
  padding: 2.5rem 1.5rem 3rem;
  border-radius: 2.25rem;
  background: radial-gradient(120% 120% at 20% 0%, #8a66ff 0%, var(--z3-purple) 45%, #4b2cc0 100%);
  box-shadow: 0 10px 0 var(--z3-purple-edge);
  color: #fff;
  overflow: hidden;
  text-align: center;
}
@media (min-width: 768px) {
  .zc__slab {
    grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr);
    padding: 3rem 3.5rem;
    text-align: left;
  }
}
.zc__bear {
  height: 16rem;
  width: 12rem;
  margin: 0 auto;
}
@media (min-width: 768px) {
  .zc__bear {
    height: 20rem;
    width: 15rem;
  }
}
.zc__title {
  font: 900 clamp(2rem, 1.3rem + 2.4vw, 3rem) / 1.05 var(--z3-font);
  letter-spacing: -0.02em;
  text-wrap: balance;
}
.zc__body {
  margin-top: 1rem;
  font: 600 1.15rem/1.55 var(--z3-font);
  color: #e6defe;
  max-width: 36ch;
}
@media (max-width: 767px) {
  .zc__body {
    margin-inline: auto;
  }
}
.zc__ctas {
  margin-top: 2rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
  justify-content: center;
}
@media (min-width: 768px) {
  .zc__ctas {
    justify-content: flex-start;
  }
}
.zc__deco {
  position: absolute;
  width: 5rem;
  height: 5rem;
  pointer-events: none;
  filter: drop-shadow(0 10px 14px rgba(20, 5, 60, 0.35));
}
.zc__deco--gift {
  right: 5%;
  top: 8%;
  --z3-rot: 10deg;
}
.zc__deco--rocket {
  left: 4%;
  bottom: 8%;
  --z3-rot: -8deg;
  animation-delay: -1.6s;
}
.zc__deco--coins {
  right: 3%;
  bottom: 8%;
  width: 3.75rem;
  height: 3.75rem;
  animation-delay: -3s;
}
@media (max-width: 767px) {
  .zc__deco--rocket,
  .zc__deco--coins {
    display: none;
  }
}
</style>
