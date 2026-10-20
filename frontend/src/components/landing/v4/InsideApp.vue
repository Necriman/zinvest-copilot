<script setup>
/**
 * Inside Zinvest: four chapters scroll on the left while one phone holds
 * still on the right and changes its screen to match (the path, the AI
 * mentor, the Telegram bot, progress). On phones the device is not sticky:
 * each chapter carries its own small screen inline.
 *
 * The first two chapters are the navbar's #path and #zinvest-ai anchors.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { vIn, vLive } from './inView'

const CHAPTERS = [
  { key: 'c1', id: 'path', screen: 'path' },
  { key: 'c2', id: 'zinvest-ai', screen: 'ai' },
  { key: 'c3', id: 'telegram', screen: 'tg' },
  { key: 'c4', id: 'progress', screen: 'progress' },
]
const LESSONS = [
  { key: 'l1', state: 'done' },
  { key: 'l2', state: 'done' },
  { key: 'l3', state: 'now' },
  { key: 'l4', state: 'ahead' },
  { key: 'l5', state: 'test' },
]
const LEAGUE = [
  { name: 'Aziz', pts: 540 },
  { name: null, pts: 420 },
  { name: 'Malika', pts: 385 },
  { name: 'Timur', pts: 310 },
]

const active = ref(0)
const chapterEls = []
const setChapter = (i) => (el) => {
  chapterEls[i] = el
}
let io = null

onMounted(() => {
  if (typeof IntersectionObserver === 'undefined') return
  // A chapter takes the phone once it crosses the middle band of the screen.
  io = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) active.value = Number(e.target.dataset.index)
      }
    },
    { rootMargin: '-45% 0px -45% 0px', threshold: 0 },
  )
  chapterEls.forEach((el) => el && io.observe(el))
})
onBeforeUnmount(() => io?.disconnect())
</script>

<template>
  <section v-in class="z4-section zi">
    <div class="z4-wrap">
      <header class="zi__head">
        <p class="z4-kicker" data-in>{{ $t('v4.app.eyebrow') }}</p>
        <h2 class="z4-h2 zi__title" data-in style="--i: 1">{{ $t('v4.app.title') }}</h2>
      </header>

      <div class="zi__grid">
        <div class="zi__chapters">
          <article
            v-for="(c, i) in CHAPTERS"
            :id="c.id"
            :key="c.key"
            :ref="setChapter(i)"
            :data-index="i"
            class="zi__chapter scroll-mt-24"
            :class="{ 'is-active': active === i }"
          >
            <p class="zi__index">{{ String(i + 1).padStart(2, '0') }} / 04 · {{ $t(`v4.app.${c.key}.kicker`) }}</p>
            <h3 class="zi__ctitle">{{ $t(`v4.app.${c.key}.title`) }}</h3>
            <p class="zi__cbody">{{ $t(`v4.app.${c.key}.body`) }}</p>

            <!-- Phones: this chapter's own screen -->
            <div class="zi__inline" aria-hidden="true">
              <div class="zi__phone zi__phone--small">
                <div class="zi__screen">
                  <div class="zi__view is-shown">
                    <template v-if="c.screen === 'path'">
                      <p class="zi__unit">{{ $t('v4.app.path.unit') }}</p>
                      <ul class="zi__lessons">
                        <li v-for="l in LESSONS" :key="l.key" :data-state="l.state">
                          <span class="zi__dot" />
                          <span class="zi__lname">{{ $t(`v4.app.path.${l.key}`) }}</span>
                          <span v-if="l.state === 'now'" class="zi__pill">{{ $t('v4.app.path.now') }}</span>
                        </li>
                      </ul>
                    </template>
                    <template v-else-if="c.screen === 'ai'">
                      <p class="zi__ctx">{{ $t('v4.app.ai.context') }}</p>
                      <p class="zi__msg zi__msg--me">{{ $t('v4.app.ai.q') }}</p>
                      <div class="zi__mentor-row">
                        <span class="zi__av">Z</span>
                        <p class="zi__msg zi__msg--mentor">{{ $t('v4.app.ai.a') }}</p>
                      </div>
                    </template>
                    <template v-else-if="c.screen === 'tg'">
                      <p class="zi__msg zi__msg--me">{{ $t('v4.app.tg.u1') }}</p>
                      <p class="zi__msg zi__msg--bot">{{ $t('v4.app.tg.b1') }}</p>
                      <p class="zi__msg zi__msg--bot">{{ $t('v4.app.tg.b2') }}</p>
                    </template>
                    <template v-else>
                      <p class="zi__big">7</p>
                      <p class="zi__biglabel">{{ $t('v4.app.progress.streak') }}</p>
                      <p class="zi__coins"><b>420</b> {{ $t('v4.app.progress.coins') }}</p>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>

        <!-- Wide screens: one phone that holds still -->
        <div class="zi__device" aria-hidden="true">
          <div v-live class="zi__phone">
            <div class="zi__notch" />
            <div class="zi__screen">
              <!-- 1. The path -->
              <div class="zi__view" :class="{ 'is-shown': active === 0 }">
                <p class="zi__appbar">Zinvest</p>
                <p class="zi__unit">{{ $t('v4.app.path.unit') }}</p>
                <ul class="zi__lessons">
                  <li v-for="l in LESSONS" :key="l.key" :data-state="l.state">
                    <span class="zi__dot" />
                    <span class="zi__lname">{{ $t(`v4.app.path.${l.key}`) }}</span>
                    <span v-if="l.state === 'done'" class="zi__lstate">{{ $t('v4.app.path.done') }}</span>
                    <span v-else-if="l.state === 'now'" class="zi__pill">{{ $t('v4.app.path.now') }}</span>
                    <span v-else-if="l.state === 'ahead'" class="zi__lstate">{{ $t('v4.app.path.ahead') }}</span>
                  </li>
                </ul>
              </div>

              <!-- 2. The AI mentor -->
              <div class="zi__view" :class="{ 'is-shown': active === 1 }">
                <p class="zi__appbar">Zinvest AI</p>
                <p class="zi__ctx">{{ $t('v4.app.ai.context') }}</p>
                <p class="zi__msg zi__msg--me">{{ $t('v4.app.ai.q') }}</p>
                <div class="zi__mentor-row">
                  <span class="zi__av">Z</span>
                  <p class="zi__msg zi__msg--mentor">{{ $t('v4.app.ai.a') }}</p>
                </div>
                <div class="zi__chips">
                  <span>{{ $t('v4.app.ai.chip1') }}</span>
                  <span>{{ $t('v4.app.ai.chip2') }}</span>
                  <span>{{ $t('v4.app.ai.chip3') }}</span>
                </div>
              </div>

              <!-- 3. The Telegram bot -->
              <div class="zi__view zi__view--tg" :class="{ 'is-shown': active === 2 }">
                <p class="zi__appbar">
                  Zinvest <small>{{ $t('v4.app.tg.status') }}</small>
                </p>
                <p class="zi__msg zi__msg--me">{{ $t('v4.app.tg.u1') }}</p>
                <p class="zi__msg zi__msg--bot">{{ $t('v4.app.tg.b1') }}</p>
                <p class="zi__msg zi__msg--bot">{{ $t('v4.app.tg.b2') }}</p>
                <div class="zi__poll">
                  <p class="zi__poll-t">{{ $t('v4.app.tg.quizTitle') }}</p>
                  <p class="zi__poll-q">{{ $t('v4.app.tg.quizQ') }}</p>
                  <p class="zi__poll-a is-right">{{ $t('v4.app.tg.quizA1') }}</p>
                  <p class="zi__poll-a">{{ $t('v4.app.tg.quizA2') }}</p>
                </div>
              </div>

              <!-- 4. Progress -->
              <div class="zi__view" :class="{ 'is-shown': active === 3 }">
                <p class="zi__appbar">{{ $t('v4.app.c4.kicker') }}</p>
                <div class="zi__streak">
                  <p class="zi__big">7</p>
                  <p class="zi__biglabel">{{ $t('v4.app.progress.streak') }}</p>
                  <div class="zi__week">
                    <span v-for="(d, i) in $t('v4.app.progress.days').split(',')" :key="d" :class="{ 'is-today': i === 6 }">{{ d }}</span>
                  </div>
                </div>
                <p class="zi__coins"><b>420</b> {{ $t('v4.app.progress.coins') }}</p>
                <p class="zi__league-t">{{ $t('v4.app.progress.league') }}</p>
                <ol class="zi__league">
                  <li v-for="(r, i) in LEAGUE" :key="i" :class="{ 'is-you': !r.name }">
                    <span class="zi__rank">{{ i + 1 }}</span>
                    <span class="zi__who">{{ r.name || $t('v4.app.progress.you') }}</span>
                    <span class="zi__pts">{{ r.pts }} {{ $t('v4.app.progress.pts') }}</span>
                  </li>
                </ol>
              </div>
            </div>
          </div>
          <div class="zi__dots">
            <i v-for="(c, i) in CHAPTERS" :key="c.key" :class="{ 'is-on': active === i }" />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.zi__head {
  max-width: 44rem;
}
.zi__grid {
  margin-top: 2rem;
  display: grid;
}
@media (min-width: 1024px) {
  .zi__grid {
    grid-template-columns: minmax(0, 1fr) minmax(0, 0.85fr);
    gap: 4rem;
  }
}

/* ---- chapters ----------------------------------------------------------- */
.zi__chapter {
  padding: 3rem 0;
  border-top: 1px solid var(--z4-line);
}
@media (min-width: 1024px) {
  .zi__chapter {
    min-height: 78vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 0;
    border-top: 0;
    opacity: 0.32;
    transition: opacity 0.6s var(--z4-ease);
  }
  .zi__chapter.is-active {
    opacity: 1;
  }
}
.zi__index {
  font: 500 0.76rem/1.2 var(--z4-mono);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--z4-violet-2);
}
.zi__ctitle {
  margin-top: 1rem;
  max-width: 16ch;
  font: 650 clamp(2rem, 1.3rem + 2.2vw, 3.2rem) / 1.04 var(--z4-display);
  font-variation-settings: 'SHRP' 60;
  letter-spacing: -0.03em;
  color: var(--z4-text);
  text-wrap: balance;
}
.zi__cbody {
  margin-top: 1.1rem;
  max-width: 40ch;
  font: 400 1.1rem/1.6 var(--z4-body);
  color: var(--z4-text-2);
}
.zi__inline {
  margin-top: 2rem;
}
@media (min-width: 1024px) {
  .zi__inline {
    display: none;
  }
}

/* ---- the device --------------------------------------------------------- */
.zi__device {
  display: none;
}
@media (min-width: 1024px) {
  .zi__device {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.25rem;
    position: sticky;
    top: 11vh;
    height: 78vh;
    align-self: start;
    justify-content: center;
  }
}
.zi__phone {
  position: relative;
  width: min(21rem, 100%);
  height: min(40rem, 70vh);
  padding: 0.7rem;
  border-radius: 2.8rem;
  background: linear-gradient(160deg, #24222e, #121118);
  border: 1px solid rgba(220, 214, 255, 0.22);
  box-shadow:
    0 50px 90px -40px rgba(4, 2, 16, 0.95),
    0 0 0 1px rgba(0, 0, 0, 0.4) inset;
}
.zi__phone::before {
  /* a slow glow behind the device, only while it is on screen */
  content: '';
  position: absolute;
  inset: 12% -18% 8%;
  z-index: -1;
  border-radius: 50%;
  background: radial-gradient(closest-side, rgba(111, 85, 224, 0.35), transparent);
  opacity: 0.6;
}
.zi__phone.live::before {
  animation: zi-breathe 7s ease-in-out infinite -2s;
}
@keyframes zi-breathe {
  0%,
  100% {
    opacity: 0.45;
  }
  50% {
    opacity: 0.85;
  }
}
.zi__phone--small {
  width: 100%;
  max-width: 22rem;
  height: auto;
  border-radius: 1.8rem;
}
.zi__notch {
  position: absolute;
  left: 50%;
  top: 1.2rem;
  z-index: 2;
  width: 5.5rem;
  height: 1.4rem;
  margin-left: -2.75rem;
  border-radius: 99px;
  background: #08080b;
}
.zi__screen {
  position: relative;
  height: 100%;
  border-radius: 2.2rem;
  background: linear-gradient(to bottom, #17161e, #111016);
  overflow: hidden;
}
.zi__phone--small .zi__screen {
  border-radius: 1.3rem;
}
.zi__view {
  position: absolute;
  inset: 0;
  padding: 3.4rem 1.1rem 1.2rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  opacity: 0;
  transform: translateY(14px) scale(0.985);
  transition:
    opacity 0.45s var(--z4-ease),
    transform 0.6s var(--z4-ease);
  pointer-events: none;
}
.zi__view.is-shown {
  opacity: 1;
  transform: none;
}
.zi__phone--small .zi__view {
  position: static;
  padding: 1.1rem;
}
.zi__appbar {
  font: 600 1rem/1.2 var(--z4-display);
  color: var(--z4-text);
}
.zi__appbar small {
  margin-left: 0.35rem;
  font: 500 0.72rem/1 var(--z4-mono);
  color: var(--z4-text-3);
}
.zi__unit {
  margin-top: 0.3rem;
  font: 500 0.72rem/1.3 var(--z4-mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--z4-violet-2);
}
.zi__lessons {
  display: grid;
  gap: 0.5rem;
}
.zi__lessons li {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-height: 3rem;
  padding: 0.55rem 0.8rem;
  border-radius: 0.9rem;
  background: rgba(220, 214, 255, 0.06);
  border: 1px solid rgba(220, 214, 255, 0.1);
  font: 500 0.9rem/1.25 var(--z4-body);
  color: var(--z4-text-2);
}
.zi__lessons li[data-state='now'] {
  background: rgba(230, 190, 106, 0.08);
  border-color: rgba(230, 190, 106, 0.45);
  color: var(--z4-text);
}
.zi__lessons li[data-state='ahead'],
.zi__lessons li[data-state='test'] {
  color: var(--z4-text-3);
}
.zi__dot {
  width: 0.7rem;
  height: 0.7rem;
  flex-shrink: 0;
  border-radius: 50%;
  border: 2px solid var(--z4-edge);
}
[data-state='done'] .zi__dot {
  background: var(--z4-aurora);
  border-color: var(--z4-aurora);
}
[data-state='now'] .zi__dot {
  border-color: var(--z4-gold);
  box-shadow: 0 0 0 4px rgba(230, 190, 106, 0.18);
}
[data-state='test'] .zi__dot {
  border-radius: 3px;
  transform: rotate(45deg);
}
.zi__lname {
  flex: 1;
  min-width: 0;
}
.zi__lstate {
  font: 500 0.66rem/1 var(--z4-mono);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--z4-text-3);
}
.zi__pill {
  padding: 0.3rem 0.55rem;
  border-radius: 99px;
  background: var(--z4-gold);
  color: var(--z4-gold-ink);
  font: 600 0.68rem/1 var(--z4-body);
}

.zi__ctx {
  font: 500 0.7rem/1.3 var(--z4-mono);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--z4-text-3);
}
.zi__msg {
  max-width: 88%;
  padding: 0.65rem 0.85rem;
  border-radius: 1rem;
  font: 400 0.88rem/1.5 var(--z4-body);
}
.zi__msg--me {
  align-self: flex-end;
  border-bottom-right-radius: 0.3rem;
  background: var(--z4-violet);
  color: #fff;
}
.zi__msg--mentor,
.zi__msg--bot {
  align-self: flex-start;
  border-bottom-left-radius: 0.3rem;
  background: rgba(220, 214, 255, 0.1);
  color: var(--z4-text);
}
.zi__mentor-row {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
}
.zi__mentor-row .zi__msg {
  max-width: none;
}
/* The mentor's mark: a monogram, not a mascot. */
.zi__av {
  display: grid;
  place-items: center;
  width: 1.9rem;
  height: 1.9rem;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--z4-text);
  color: var(--z4-canvas);
  font: 700 0.8rem/1 var(--z4-display);
}
.zi__chips {
  margin-top: auto;
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.zi__chips span {
  padding: 0.45rem 0.75rem;
  border-radius: 99px;
  border: 1px solid var(--z4-edge);
  font: 500 0.78rem/1 var(--z4-body);
  color: var(--z4-text-2);
}
.zi__poll {
  margin-top: 0.3rem;
  padding: 0.85rem;
  border-radius: 1rem;
  background: rgba(220, 214, 255, 0.07);
  border: 1px solid rgba(220, 214, 255, 0.12);
}
.zi__poll-t {
  font: 500 0.68rem/1.2 var(--z4-mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--z4-violet-2);
}
.zi__poll-q {
  margin-top: 0.35rem;
  font: 500 0.88rem/1.4 var(--z4-body);
  color: var(--z4-text);
}
.zi__poll-a {
  margin-top: 0.45rem;
  padding: 0.5rem 0.7rem;
  border-radius: 0.7rem;
  border: 1px solid var(--z4-line);
  font: 400 0.84rem/1.3 var(--z4-body);
  color: var(--z4-text-2);
}
.zi__poll-a.is-right {
  border-color: rgba(134, 207, 176, 0.5);
  color: var(--z4-aurora);
}

.zi__streak {
  padding: 1rem;
  border-radius: 1.1rem;
  background: radial-gradient(120% 120% at 0% 0%, rgba(230, 190, 106, 0.16), rgba(220, 214, 255, 0.06) 60%);
  border: 1px solid rgba(230, 190, 106, 0.25);
}
.zi__big {
  font: 700 3.4rem/1 var(--z4-display);
  font-variation-settings: 'SHRP' 60;
  color: var(--z4-gold);
}
.zi__biglabel {
  margin-top: 0.2rem;
  font: 500 0.9rem/1.3 var(--z4-body);
  color: var(--z4-text);
}
.zi__week {
  margin-top: 0.8rem;
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0.25rem;
}
.zi__week span {
  display: grid;
  place-items: center;
  height: 1.7rem;
  border-radius: 0.5rem;
  background: rgba(230, 190, 106, 0.2);
  font: 500 0.62rem/1 var(--z4-mono);
  color: var(--z4-text);
}
.zi__week span.is-today {
  background: var(--z4-gold);
  color: var(--z4-gold-ink);
}
.zi__coins {
  font: 400 0.9rem/1.3 var(--z4-body);
  color: var(--z4-text-2);
}
.zi__coins b {
  font: 600 1.1rem/1 var(--z4-mono);
  color: var(--z4-text);
}
.zi__league-t {
  font: 500 0.68rem/1.2 var(--z4-mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--z4-text-3);
}
.zi__league {
  display: grid;
  gap: 0.3rem;
}
.zi__league li {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.45rem 0.6rem;
  border-radius: 0.7rem;
  font: 400 0.84rem/1.2 var(--z4-body);
  color: var(--z4-text-2);
}
.zi__league li.is-you {
  background: rgba(111, 85, 224, 0.16);
  color: var(--z4-text);
}
.zi__rank {
  width: 1rem;
  font: 500 0.78rem/1 var(--z4-mono);
  color: var(--z4-text-3);
}
.zi__who {
  flex: 1;
}
.zi__pts {
  font: 500 0.78rem/1 var(--z4-mono);
}

.zi__dots {
  display: flex;
  gap: 0.45rem;
}
.zi__dots i {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 99px;
  background: var(--z4-edge);
  transition: width 0.4s var(--z4-ease), background-color 0.4s var(--z4-ease);
}
.zi__dots i.is-on {
  width: 1.4rem;
  background: var(--z4-text);
}
</style>
