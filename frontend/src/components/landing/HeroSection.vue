<script setup>
import { computed } from 'vue'

import AppButton from '@/components/ui/AppButton.vue'
import Icon from '@/components/ui/Icon.vue'
import AppPreview from './AppPreview.vue'
import HeroStage from './HeroStage.vue'
import Reveal from './Reveal.vue'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const startTo = computed(() => (auth.isAuthenticated ? { name: 'dashboard' } : { name: 'register' }))

// Three, not four. Each one answers a different question a first-time visitor
// has — is it mine, do I do anything, does it stick — so a fourth pill would
// only repeat one of them at the cost of the headline's weight.
const INCLUDES = [
  { key: 'plan', icon: 'map' },
  { key: 'lessons', icon: 'target' },
  { key: 'progress', icon: 'flame' },
]
</script>

<template>
  <div class="relative z-10 mx-auto w-full max-w-6xl px-6">
    <!-- On a phone the order is headline, words, action, the bear, then the
         quiet supporting pills. On a wide screen the same pieces become two
         columns, with the bear's scene spanning both rows on the right. -->
    <div
      class="flex flex-col items-center gap-8 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,0.92fr)] lg:grid-rows-[auto_auto] lg:items-center lg:gap-x-10 lg:gap-y-8"
    >
      <div class="order-1 w-full text-center lg:col-start-1 lg:row-start-1 lg:text-left">
        <Reveal :delay="60">
          <h1
            class="text-[2.7rem] font-extrabold leading-[1.02] tracking-[-0.03em] text-slate-900 sm:text-6xl sm:leading-[0.96] lg:text-[3.5rem] lg:leading-[0.96] xl:text-[4.25rem] xl:leading-[0.94] dark:text-white"
          >
            {{ $t('landing.titlePre') }}<br />
            <span class="text-brand-600 dark:text-brand-400">{{ $t('landing.titleAccent') }}</span>
          </h1>
        </Reveal>

        <Reveal :delay="120">
          <p
            class="mx-auto mt-5 max-w-[34ch] text-base leading-[1.65] text-slate-500 sm:mt-7 sm:text-lg lg:mx-0 dark:text-slate-400"
          >
            {{ $t('landing.subtitle') }}
          </p>
        </Reveal>

        <Reveal :delay="180">
          <div
            class="mt-8 flex flex-col items-stretch justify-center gap-3 sm:mt-9 sm:flex-row sm:items-center lg:justify-start"
          >
            <AppButton :to="startTo" size="lg" icon-right="arrowRight" class="w-full sm:w-auto">
              {{ $t('landing.startPreparation') }}
            </AppButton>
            <!-- Ghost, not outline: the second action should be findable, not
                 a second button competing with the first. -->
            <AppButton href="#how-it-works" variant="ghost" size="lg" icon="play" class="w-full sm:w-auto">
              {{ $t('landing.seePlatform') }}
            </AppButton>
          </div>
        </Reveal>
      </div>

      <!-- The bear, inside a small piece of the product. -->
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

    <Reveal :delay="300" class="mt-14 sm:mt-20">
      <AppPreview class="mx-auto max-w-4xl" />
    </Reveal>
  </div>
</template>
