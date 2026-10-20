<script setup>
/**
 * The hero, rebuilt for the narrative page.
 *
 * Same headline, same bear, same three supporting lines as the version it
 * replaces — what changes is what comes after it. The old hero ended with a
 * full app screenshot, which answered every question before the page had
 * asked one. Here it ends with a single line down to the question the rest of
 * the page is an answer to, so the scroll starts with a reason.
 */
import { computed } from 'vue'

import AppButton from '@/components/ui/AppButton.vue'
import Icon from '@/components/ui/Icon.vue'
import HeroStage from '../HeroStage.vue'
import Reveal from '../Reveal.vue'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const startTo = computed(() => (auth.isAuthenticated ? { name: 'dashboard' } : { name: 'register' }))

const INCLUDES = [
  { key: 'plan', icon: 'map' },
  { key: 'lessons', icon: 'target' },
  { key: 'progress', icon: 'flame' },
]
</script>

<template>
  <div class="relative z-10 mx-auto w-full max-w-6xl px-6">
    <div
      class="flex flex-col items-center gap-8 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,0.92fr)] lg:grid-rows-[auto_auto] lg:items-center lg:gap-x-10 lg:gap-y-8"
    >
      <!-- The headline, the promise and the buttons are on screen from the first
           paint, without a reveal: on a slow phone a staggered fade-in read as
           "the site is not loading". Only the bear and the small print below
           animate in. -->
      <div class="order-1 w-full text-center lg:col-start-1 lg:row-start-1 lg:text-left">
        <h1
          class="text-[2.4rem] font-extrabold leading-[1.04] tracking-[-0.03em] text-slate-900 sm:text-6xl sm:leading-[0.96] lg:text-[3.5rem] lg:leading-[0.96] xl:text-[4.25rem] xl:leading-[0.94] dark:text-white"
        >
          {{ $t('landing.titlePre') }}<br />
          <span class="text-brand-600 dark:text-brand-400">{{ $t('landing.titleAccent') }}</span>
        </h1>

        <p
          class="mx-auto mt-5 max-w-[34ch] text-base leading-[1.65] text-slate-500 sm:mt-7 sm:text-lg lg:mx-0 dark:text-slate-400"
        >
          {{ $t('landing.subtitle') }}
        </p>

        <div
          class="mt-8 flex flex-col items-stretch justify-center gap-3 sm:mt-9 sm:flex-row sm:items-center lg:justify-start"
        >
          <AppButton :to="startTo" size="lg" icon-right="arrowRight" class="w-full sm:w-auto">
            {{ $t('landing.startPreparation') }}
          </AppButton>
          <!-- Points at the interactive demo, not at a feature list: the
               strongest thing this page has is something you can do. -->
          <AppButton href="#try" variant="ghost" size="lg" icon="play" class="w-full sm:w-auto">
            {{ $t('v2.hero.secondary') }}
          </AppButton>
        </div>
      </div>

      <Reveal
        :delay="140"
        class="order-2 h-[19rem] w-[19rem] shrink-0 sm:h-[23rem] sm:w-[23rem] lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:h-[34rem] lg:w-full"
      >
        <HeroStage />
      </Reveal>

      <Reveal :delay="240" class="order-3 w-full lg:col-start-1 lg:row-start-2">
        <ul class="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 lg:justify-start">
          <li
            v-for="item in INCLUDES"
            :key="item.key"
            class="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 transition-colors duration-200 hover:text-slate-700 sm:text-sm dark:text-slate-400 dark:hover:text-slate-200"
          >
            <Icon :name="item.icon" class="h-3.5 w-3.5 shrink-0 text-brand-600/70 sm:h-4 sm:w-4 dark:text-brand-400/70" />
            {{ $t(`landing.includes.${item.key}`) }}
          </li>
        </ul>
      </Reveal>
    </div>

    <!-- The bridge. The old hero ended with a full app screenshot, which
         answered everything before the page had asked anything; this instead
         names the next beat and hands the scroll a reason. It is also the one
         piece of the hero that says "keep going" without a tooltip. -->
    <Reveal :delay="320" class="mt-12 flex justify-center sm:mt-16 lg:justify-start">
      <a href="#why" class="zh__next">
        <span class="zh__rule" aria-hidden="true" />
        <span class="zh__label">
          {{ $t('v2.problem.eyebrow') }}
          <Icon name="chevronDown" class="zh__chevron h-3.5 w-3.5" />
        </span>
      </a>
    </Reveal>
  </div>
</template>

<style scoped>
.zh__next {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 0.7rem;
}
@media (min-width: 1024px) {
  .zh__next {
    align-items: flex-start;
  }
}

/* A hairline that keeps falling: the line itself is the invitation. */
.zh__rule {
  width: 1px;
  height: 2.75rem;
  background: linear-gradient(to bottom, transparent, var(--color-hairline) 30%, var(--brand-500));
}

.zh__label {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  transition: color 200ms ease;
}
.zh__next:hover .zh__label {
  color: var(--color-ink);
}
.zh__chevron {
  color: var(--brand-600);
  animation: zh-drop 2.6s var(--ease-in-out) infinite;
}
.dark .zh__chevron {
  color: var(--brand-400);
}
@keyframes zh-drop {
  0%,
  55%,
  100% {
    transform: translateY(0);
  }
  72% {
    transform: translateY(3px);
  }
}
.zh__next:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 4px;
  border-radius: 0.5rem;
}

@media (prefers-reduced-motion: reduce) {
  .zh__chevron {
    animation: none;
  }
}
</style>
