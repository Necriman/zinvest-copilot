<script setup>
/**
 * The cookie notice. Zinvest sets only the cookies sign-in needs (no ads, no
 * analytics), so there is nothing to opt in or out of: the notice says so,
 * links the Cookie Policy, and goes away for good once dismissed. No "Accept
 * all" button, because there is nothing more to accept.
 */
import { onMounted, ref } from 'vue'

const KEY = 'zinvest.cookieNotice'
const open = ref(false)

onMounted(() => {
  try {
    open.value = localStorage.getItem(KEY) !== 'seen'
  } catch {
    open.value = true
  }
})

function dismiss() {
  open.value = false
  try {
    localStorage.setItem(KEY, 'seen')
  } catch {
    /* private mode: it shows again next visit */
  }
}
</script>

<template>
  <Transition name="ck">
    <section v-if="open" class="ck" role="region" :aria-label="$t('cookies.label')">
      <p>
        {{ $t('cookies.text') }}
        <RouterLink :to="{ name: 'legal', params: { doc: 'cookies' } }">{{ $t('cookies.more') }}</RouterLink>
      </p>
      <button type="button" class="ck__ok" @click="dismiss">{{ $t('cookies.ok') }}</button>
    </section>
  </Transition>
</template>

<style scoped>
.ck {
  position: fixed;
  left: 1rem;
  right: 1rem;
  bottom: 1rem;
  z-index: 150;
  display: flex;
  align-items: center;
  gap: 1rem;
  max-width: 30rem;
  padding: 0.9rem 1rem 0.9rem 1.1rem;
  border-radius: 1.1rem;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  box-shadow: 0 12px 40px -12px rgba(15, 14, 20, 0.35);
  font-size: 0.85rem;
  line-height: 1.5;
}
.ck a {
  color: var(--brand-600);
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.ck__ok {
  flex-shrink: 0;
  min-height: 2.75rem;
  padding: 0 1.1rem;
  border-radius: 0.8rem;
  background: var(--brand-600);
  color: #fff;
  font-weight: 700;
  transition: background 0.15s ease;
}
.ck__ok:hover {
  background: var(--brand-700);
}
.ck__ok:focus-visible,
.ck a:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
}
.ck-enter-active,
.ck-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.ck-enter-from,
.ck-leave-to {
  opacity: 0;
  transform: translateY(0.75rem);
}
@media (prefers-reduced-motion: reduce) {
  .ck-enter-active,
  .ck-leave-active {
    transition: opacity 0.2s ease;
  }
  .ck-enter-from,
  .ck-leave-to {
    transform: none;
  }
}
</style>
