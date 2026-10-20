<script setup>
/**
 * Sign in ⇄ Sign up as one switch at the top of the form, with a pill that
 * slides between the two. Router links, so each door keeps its own URL and
 * the redirect query rides along.
 */
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()
const query = computed(() => (route.query.redirect ? { redirect: route.query.redirect } : {}))
const onRegister = computed(() => route.name === 'register')
</script>

<template>
  <nav class="at" :class="{ 'at--right': onRegister }" :aria-label="$t('auth.tabs.label')">
    <span class="at__pill" aria-hidden="true" />
    <RouterLink :to="{ name: 'login', query }" class="at__tab" :aria-current="!onRegister ? 'page' : undefined">
      {{ $t('auth.tabs.login') }}
    </RouterLink>
    <RouterLink :to="{ name: 'register', query }" class="at__tab" :aria-current="onRegister ? 'page' : undefined">
      {{ $t('auth.tabs.register') }}
    </RouterLink>
  </nav>
</template>

<style scoped>
.at {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 0.3rem;
  border-radius: 1rem;
  background: var(--surface-2);
  border: 1px solid var(--border);
}
.at__pill {
  position: absolute;
  top: 0.3rem;
  bottom: 0.3rem;
  left: 0.3rem;
  width: calc(50% - 0.3rem);
  border-radius: 0.75rem;
  background: var(--surface);
  box-shadow: 0 2px 10px -4px rgba(15, 23, 42, 0.25);
  transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}
.at--right .at__pill {
  transform: translateX(100%);
}
.at__tab {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 2.6rem;
  border-radius: 0.75rem;
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--text-muted);
  text-decoration: none;
  transition: color 0.2s ease;
}
.at__tab[aria-current='page'] {
  color: var(--text);
}
.at__tab:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 1px;
}
@media (prefers-reduced-motion: reduce) {
  .at__pill {
    transition: none;
  }
}
</style>
