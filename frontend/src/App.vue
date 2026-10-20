<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AskSelection from '@/components/ai/AskSelection.vue'
import CookieNotice from '@/components/CookieNotice.vue'
import TopLoadingBar from '@/components/ui/TopLoadingBar.vue'
import { flushPendingScroll } from '@/router/navScroll'
import { useAuthStore } from '@/store/auth'

const route = useRoute()
const auth = useAuthStore()
// Select-to-ask lives on the signed-in pages only: the AI is a learner's tool,
// and the landing and sign-in screens have nobody to answer yet.
const canAsk = computed(() => auth.isAuthenticated && route.matched.some((r) => r.meta.requiresAuth))
</script>

<template>
  <!-- Crossfade between top-level shells (landing / app / lesson). Opacity only:
       these shells own the fixed navbar, sidebar and right rail, and a transform
       here would detach every one of them from the viewport for the length of
       the transition. The slide lives on the inner <router-view>s, whose content
       carries no fixed chrome.

       before-enter is where a route change's scroll-to-top happens: the outgoing
       view is gone and the incoming one has not been painted, so the jump never
       shows. Doing it when the router asks would move the page still on screen. -->
  <a href="#main" class="zx-skip print:hidden">{{ $t('a11y.skip') }}</a>
  <router-view v-slot="{ Component }">
    <Transition name="shell-fade" mode="out-in" @before-enter="flushPendingScroll">
      <component :is="Component" />
    </Transition>
  </router-view>

  <TopLoadingBar />
  <CookieNotice />
  <AskSelection v-if="canAsk" />
</template>
