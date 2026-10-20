<script setup>
/**
 * The Telegram bot, shown as a phone: a spend logged in one line, the streak
 * nudge and the daily question, arriving one after another when the phone
 * scrolls into view. What the bot says here is what the bot actually does.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

import Icon from '@/components/ui/Icon.vue'
import Icon3d from './Icon3d.vue'
import ZButton from './ZButton.vue'

const BOT_URL = 'https://t.me/ZinvestAI_bot'
const POINTS = [
  { key: 'p1', icon: 'coins' },
  { key: 'p2', icon: 'target' },
  { key: 'p3', icon: 'flame' },
]

const phone = ref(null)
const live = ref(false)
let io = null
onMounted(() => {
  if (typeof IntersectionObserver === 'undefined') {
    live.value = true
    return
  }
  io = new IntersectionObserver(([e]) => {
    if (e.isIntersecting) {
      live.value = true
      io.disconnect()
    }
  }, { threshold: 0.35 })
  if (phone.value) io.observe(phone.value)
})
onBeforeUnmount(() => io?.disconnect())
</script>

<template>
  <section class="z3-section">
    <div class="z3-wrap zg">
      <div class="zg__copy">
        <p class="z3-eyebrow">{{ $t('v3.telegram.eyebrow') }}</p>
        <h2 class="z3-h2">{{ $t('v3.telegram.title') }}</h2>
        <p class="z3-lede">{{ $t('v3.telegram.body') }}</p>
        <ul class="zg__points">
          <li v-for="p in POINTS" :key="p.key">
            <Icon3d :name="p.icon" class="h-10 w-10 shrink-0" />
            {{ $t(`v3.telegram.${p.key}`) }}
          </li>
        </ul>
        <div class="zg__cta">
          <ZButton :href="BOT_URL" target="_blank" rel="noopener" variant="secondary">
            <Icon3d name="plane" class="h-6 w-6" />
            {{ $t('v3.telegram.cta') }}
          </ZButton>
        </div>
      </div>

      <div class="zg__stage">
        <span class="zg__halo" aria-hidden="true" />
        <Icon3d name="plane" class="zg__plane z3-float" />
        <div ref="phone" class="zg__phone" :class="{ 'zg__phone--live': live }" aria-hidden="true">
          <div class="zg__bar">
            <img src="/mascot/ai-avatar-96.webp" alt="" class="zg__ava" width="96" height="96" />
            <div>
              <p class="zg__bot">{{ $t('v3.telegram.botName') }}</p>
              <p class="zg__status">{{ $t('v3.telegram.botStatus') }}</p>
            </div>
          </div>
          <div class="zg__chat">
            <p class="zg__m zg__m--me" style="--d: 0.1s">{{ $t('v3.telegram.u1') }}</p>
            <p class="zg__m zg__m--bot" style="--d: 0.7s">
              <Icon name="checkCircle" class="h-4 w-4 shrink-0 text-emerald-600" />
              {{ $t('v3.telegram.b1') }}
            </p>
            <p class="zg__m zg__m--bot" style="--d: 1.4s">
              <Icon3d name="flame" class="h-5 w-5 shrink-0" />
              {{ $t('v3.telegram.b2') }}
            </p>
            <div class="zg__m zg__m--bot zg__poll" style="--d: 2.1s">
              <p class="zg__pollTitle">{{ $t('v3.telegram.quizTitle') }}</p>
              <p class="zg__pollQ">{{ $t('v3.telegram.quizQ') }}</p>
              <p class="zg__opt"><i />{{ $t('v3.telegram.quizA1') }}</p>
              <p class="zg__opt"><i />{{ $t('v3.telegram.quizA2') }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zg {
  display: grid;
  gap: 3.5rem;
  align-items: center;
}
@media (min-width: 1024px) {
  .zg {
    grid-template-columns: minmax(0, 1fr) minmax(0, 0.95fr);
    gap: 4rem;
  }
}
.zg__points {
  margin-top: 1.75rem;
  display: grid;
  gap: 0.9rem;
  font: 700 1.02rem/1.4 var(--z3-font);
  color: var(--z3-ink);
}
.zg__points li {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.zg__cta {
  margin-top: 2rem;
}
.zg__stage {
  position: relative;
  display: flex;
  justify-content: center;
  padding: 1rem 0;
}
.zg__halo {
  position: absolute;
  left: 50%;
  top: 50%;
  width: min(30rem, 110%);
  aspect-ratio: 1;
  border-radius: 999px;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, color-mix(in oklab, var(--z3-blue) 30%, transparent) 0%, var(--z3-blue-soft) 45%, transparent 70%);
}
.zg__plane {
  position: absolute;
  right: 4%;
  top: 2%;
  width: 6rem;
  height: 6rem;
  --z3-rot: 8deg;
}
.zg__phone {
  position: relative;
  width: 19rem;
  border-radius: 2.6rem;
  padding: 0.6rem;
  background: #1c1934;
  box-shadow: 0 10px 0 #0f0d1f, 0 30px 60px -20px rgba(20, 10, 60, 0.45);
  transform: rotate(3deg);
}
.zg__bar {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.75rem 1rem;
  border-radius: 2rem 2rem 0 0;
  background: #fff;
  color: #111;
}
.zg__ava {
  width: 2.3rem;
  height: 2.3rem;
  border-radius: 999px;
  background: #efe9ff;
}
.zg__bot {
  font: 900 0.98rem/1.1 var(--z3-font);
}
.zg__status {
  font: 700 0.75rem/1.2 var(--z3-font);
  color: #6f86a6;
}
.zg__chat {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  min-height: 26rem;
  padding: 1rem 0.75rem 1.25rem;
  border-radius: 0 0 2rem 2rem;
  background: linear-gradient(160deg, #d6ecff 0%, #c8e4c4 100%);
}
.zg__m {
  max-width: 85%;
  padding: 0.55rem 0.8rem;
  border-radius: 1rem;
  font: 700 0.88rem/1.4 var(--z3-font);
  color: #10131a;
  box-shadow: 0 1px 1px rgba(0, 0, 0, 0.12);
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}
.zg__phone--live .zg__m {
  animation: zg-in 0.35s cubic-bezier(0.34, 1.4, 0.64, 1) forwards;
  animation-delay: var(--d);
}
.zg__m--me {
  align-self: flex-end;
  background: #e2ffc7;
  border-bottom-right-radius: 0.3rem;
}
.zg__m--bot {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  align-self: flex-start;
  background: #fff;
  border-bottom-left-radius: 0.3rem;
}
.zg__poll {
  flex-direction: column;
  gap: 0.35rem;
  width: 85%;
}
.zg__pollTitle {
  font: 900 0.72rem/1 var(--z3-font);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #2b8be6;
}
.zg__pollQ {
  font-weight: 800;
}
.zg__opt {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-weight: 600;
  color: #33415c;
}
.zg__opt i {
  width: 0.95rem;
  height: 0.95rem;
  flex-shrink: 0;
  border-radius: 999px;
  border: 2px solid #9ab1cc;
}
@keyframes zg-in {
  to { opacity: 1; transform: none; }
}
@media (prefers-reduced-motion: reduce) {
  .zg__m {
    opacity: 1;
    transform: none;
  }
  .zg__phone--live .zg__m {
    animation: none;
  }
}
</style>
