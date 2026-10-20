<script setup>
import { ref } from 'vue'

// The inner `stage` is sized to the exact grid-cell DOM box so a future Rive
// canvas + <audio> can mount into it with correct dimensions. Exposed for that.
const stage = ref(null)
defineExpose({ stage })
</script>

<template>
  <div class="relative flex h-full w-full items-center justify-center overflow-hidden bg-gradient-to-b from-brand-500 to-brand-700">
    <div ref="stage" class="relative flex h-full w-full flex-col items-center justify-center gap-6 p-8 text-center text-white">
      <!-- Whale -->
      <svg viewBox="0 0 24 24" class="h-24 w-24 opacity-95" fill="currentColor" aria-hidden="true">
        <path
          d="M2 12c2.5 0 3-2 3-2s1 3 4 3c2.5 0 3.5-1.8 3.5-1.8S15 15 18 15c2.5 0 3-2.5 3-2.5.6.9 1 2 1 2s-1.2 4.5-6 4.5c-2.6 0-4-1.3-4-1.3S13.6 21 9 21c-4.2 0-7-3.5-7-7 0-.7.2-1.4.5-2H2z"
        />
        <circle cx="17.5" cy="10.5" r="0.9" fill="#0f172a" />
        <path d="M18 6c1.5-1.5 4-1 4-1s.2 2.4-1.4 3.6" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
      </svg>

      <div class="space-y-2">
        <p class="text-lg font-bold">{{ $t('avatar.comingSoon') }}</p>
        <p class="max-w-xs text-sm text-white/80">{{ $t('avatar.subtitle') }}</p>
      </div>

      <span class="pill bg-white/15 px-4 py-1.5 text-xs font-semibold text-white backdrop-blur">
        {{ $t('common.soon') }}
      </span>
    </div>
  </div>
</template>
