<script setup>
/**
 * "Continue with Google". A plain link to the server's start of the OAuth
 * flow (accounts.google): no Google script runs on the page, and the server
 * brings the browser back signed in. It passes where we are (origin), where to
 * land afterwards (next) and this browser's device id for the session list.
 */
import { computed } from 'vue'

import { getDeviceId } from '@/api/device'

const props = defineProps({
  label: { type: String, required: true },
  next: { type: String, default: '' },
})

const href = computed(() => {
  const q = new URLSearchParams({ origin: window.location.origin, device: getDeviceId() })
  if (props.next) q.set('next', props.next)
  return `/api/auth/google/start?${q}`
})
</script>

<template>
  <a :href="href" class="gb">
    <svg class="gb__g" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
    <span>{{ label }}</span>
  </a>
</template>

<style scoped>
.gb {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.7rem;
  min-height: 3.25rem;
  padding: 0 1.25rem;
  border-radius: 1rem;
  border: 1.5px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-weight: 600;
  font-size: 0.97rem;
  text-decoration: none;
  transition:
    border-color 0.2s ease,
    background-color 0.2s ease,
    transform 0.15s ease;
}
.gb:hover {
  border-color: color-mix(in oklab, var(--brand-500) 35%, var(--border));
  background: var(--surface-2);
}
.gb:active {
  transform: scale(0.99);
}
.gb:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
}
.gb__g {
  width: 1.25rem;
  height: 1.25rem;
}
</style>
