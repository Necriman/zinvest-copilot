<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import BearMascot from '@/components/mascot/BearMascot.vue'
import AppButton from '@/components/ui/AppButton.vue'
import Reveal from './Reveal.vue'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const startTo = computed(() => (auth.isAuthenticated ? { name: 'dashboard' } : { name: 'register' }))
</script>

<template>
  <section class="px-6 pb-16 pt-8 sm:pb-24">
    <Reveal class="mx-auto max-w-5xl">
      <div
        class="relative overflow-hidden rounded-3xl bg-[#1e2a44] px-6 pb-16 pt-6 text-center sm:px-8 sm:pb-20 dark:bg-surface-2"
      >
        <div class="relative mx-auto max-w-xl">
          <!-- Beckons you in: the last gesture on the page is an invitation.
               Sized for the v8 bear, which is shorter and broader than the
               model this box was first cut for. -->
          <div class="mx-auto h-52 w-40 sm:h-64 sm:w-48">
            <BearMascot mood="invite" :decorations="false" />
          </div>
          <h2 class="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            {{ $t('landing.cta.title') }}
          </h2>
          <p class="mt-4 text-base leading-relaxed text-slate-300">
            {{ $t('landing.cta.subtitle') }}
          </p>

          <div class="mt-9 flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
            <AppButton :to="startTo" size="lg" icon-right="arrowRight" class="w-full sm:w-auto">
              {{ $t('landing.cta.primary') }}
            </AppButton>
            <!-- Not AppButton: every variant it offers is built for a light
                 surface, and this panel is dark in both themes. -->
            <RouterLink
              v-if="!auth.isAuthenticated"
              :to="{ name: 'login' }"
              class="pill w-full justify-center border border-white/25 px-7 py-3.5 text-base font-semibold text-white transition hover:border-white/40 hover:bg-white/10 sm:w-auto"
            >
              {{ $t('landing.cta.secondary') }}
            </RouterLink>
          </div>

          <p class="mt-6 text-xs font-medium text-slate-400">{{ $t('landing.cta.note') }}</p>
        </div>
      </div>
    </Reveal>
  </section>
</template>
