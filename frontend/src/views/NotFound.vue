<script setup>
/**
 * Any address the router does not know. It used to bounce silently to the
 * landing, which left someone with a mistyped link wondering what happened.
 */
import { computed } from 'vue'

import BearSticker from '@/components/mascot/BearSticker.vue'
import AppButton from '@/components/ui/AppButton.vue'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const home = computed(() => (auth.isAuthenticated ? { name: 'dashboard' } : { name: 'landing' }))
</script>

<template>
  <section class="flex min-h-[80vh] items-center justify-center px-6 pb-16 pt-32">
    <div class="mx-auto max-w-md text-center">
      <BearSticker name="confused" class="mx-auto h-40 w-40 sm:h-48 sm:w-48" />
      <p class="mt-2 text-sm font-bold uppercase tracking-[0.14em] text-brand-600 dark:text-brand-400">404</p>
      <h1 class="mt-3 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl dark:text-white">
        {{ $t('notFound.title') }}
      </h1>
      <p class="mt-4 text-base leading-relaxed text-slate-500 dark:text-slate-400">
        {{ $t('notFound.body') }}
      </p>
      <div class="mt-8 flex justify-center">
        <AppButton :to="home" size="lg" icon-right="arrowRight">
          {{ $t(auth.isAuthenticated ? 'notFound.toApp' : 'notFound.toHome') }}
        </AppButton>
      </div>
    </div>
  </section>
</template>
