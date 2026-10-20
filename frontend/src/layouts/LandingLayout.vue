<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import SiteFooter from '@/components/landing/SiteFooter.vue'
import FloatingNavbar from '@/components/nav/FloatingNavbar.vue'

// The main landing (V4) is one dark graphite world from the video down to
// the footer, so its chrome renders dark whatever the app theme is. The older
// landings kept at /v2, /v3 and /old still follow the theme.
const route = useRoute()
const polar = computed(() => Boolean(route.meta.polar))
</script>

<template>
  <div
    class="min-h-screen bg-canvas text-slate-900 dark:bg-canvas dark:text-ink"
    :class="polar ? 'dark polar-world' : ''"
  >
    <FloatingNavbar />
    <!-- No top padding here on purpose: the hero paints its own backdrop from
         y=0 so the grid and glows run *behind* the floating navbar. Padding
         here would start them below it, and that edge showed through the
         translucent bar as a line across the header. -->
    <main id="main" tabindex="-1">
      <router-view />
    </main>
    <SiteFooter />
  </div>
</template>

<style>
/* The app's dark tokens, re-tinted toward the hero footage's graphite so the
   navbar and footer sit in the same night as the page. */
.polar-world {
  --bg: #0f0e14;
  --surface: #16151d;
  --surface-2: #1f1d29;
  --border: #2e2b3b;
  --text: #f2f0ea;
  --text-muted: #b6b3c1;
  --text-faint: #908d9e;
  /* The dark theme's electric blue belongs to the app; this world is violet,
     so the navbar's button and active link take the brand purple. */
  --brand-50: #f5f1fd;
  --brand-100: #ece5fb;
  --brand-200: #d9ccf6;
  --brand-300: #c9b8ff;
  --brand-400: #b7a6ff;
  --brand-500: #7d57d6;
  --brand-600: #6943cc;
  --brand-700: #5332a8;
  --brand-800: #432a86;
  --brand-900: #34216a;
}
/* Overscroll past either end shows the body, not the wrapper. */
body:has(.polar-world) {
  background-color: #0f0e14;
}
</style>
