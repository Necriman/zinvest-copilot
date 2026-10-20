<script setup>
// A short wait inside a page: three bouncing dots and what is loading.
defineProps({
  label: { type: String, default: '' }, // defaults to "Loading…"
})
</script>

<template>
  <div class="il" role="status">
    <span class="il__dots" aria-hidden="true"><i /><i /><i /></span>
    <span>{{ label || $t('common.loading') }}</span>
  </div>
</template>

<style scoped>
.il {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  padding: 1.5rem 0;
  font-size: 0.9rem;
  color: var(--text-muted);
}
.il__dots {
  display: inline-flex;
  gap: 0.25rem;
}
.il__dots i {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--brand-500);
  animation: il-bounce 0.9s ease-in-out infinite;
}
.il__dots i:nth-child(2) {
  animation-delay: 0.15s;
}
.il__dots i:nth-child(3) {
  animation-delay: 0.3s;
}
@keyframes il-bounce {
  0%,
  80%,
  100% {
    transform: translateY(0);
    opacity: 0.45;
  }
  40% {
    transform: translateY(-0.35rem);
    opacity: 1;
  }
}
@media (prefers-reduced-motion: reduce) {
  .il__dots i {
    animation: none;
  }
}
</style>
