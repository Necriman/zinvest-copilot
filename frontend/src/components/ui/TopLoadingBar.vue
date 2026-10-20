<script setup>
// The loading bar along the top edge; loadingBar decides when it shows.
import { loadingBar } from '@/composables/useLoadingBar'

const visible = loadingBar.visible
</script>

<template>
  <Transition name="tlb">
    <div v-if="visible" class="tlb" role="progressbar" :aria-label="$t('common.loading')" aria-busy="true">
      <span />
    </div>
  </Transition>
</template>

<style scoped>
.tlb {
  position: fixed;
  inset: 0 0 auto;
  z-index: 200;
  height: 3px;
  overflow: hidden;
  pointer-events: none;
  background: color-mix(in oklab, var(--brand-500) 18%, transparent);
}
.tlb span {
  position: absolute;
  inset: 0 auto 0 0;
  width: 35%;
  background: linear-gradient(90deg, transparent, var(--brand-500), var(--brand-600));
  animation: tlb-run 1.1s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
@keyframes tlb-run {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(300%);
  }
}
.tlb-enter-active,
.tlb-leave-active {
  transition: opacity 0.2s ease;
}
.tlb-enter-from,
.tlb-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .tlb span {
    animation: none;
    width: 100%;
    opacity: 0.6;
  }
}
</style>
