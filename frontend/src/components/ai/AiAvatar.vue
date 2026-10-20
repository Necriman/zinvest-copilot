<script setup>
/**
 * Zinvest AI's face: the bear's portrait on its blue tile.
 *
 * Used wherever the AI itself is the one talking — the chat, its start
 * screen, the lesson's "ask" button and the select-to-ask card — so the tutor
 * has one recognisable face across the app, distinct from the 3D bear who
 * guides lessons and the map. Rounded like an app icon rather than cropped to
 * a circle, which would cut off the arrow and the wave.
 *
 * Small sizes take the 96px file; `large` takes the 256px one.
 */
defineProps({
  large: { type: Boolean, default: false },
  // Breathes gently while the AI is working on an answer.
  thinking: { type: Boolean, default: false },
})
</script>

<template>
  <img
    :src="large ? '/mascot/ai-avatar.webp' : '/mascot/ai-avatar-96.webp'"
    alt=""
    aria-hidden="true"
    draggable="false"
    decoding="async"
    class="ai-avatar block shrink-0 select-none object-cover"
    :class="thinking ? 'ai-avatar--thinking' : ''"
  />
</template>

<style scoped>
.ai-avatar {
  border-radius: 28%;
  box-shadow: 0 6px 16px -8px rgb(21 126 253 / 0.55);
}
.ai-avatar--thinking {
  animation: ai-avatar-think 1.6s ease-in-out infinite;
}
@keyframes ai-avatar-think {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(0.94);
  }
}
@media (prefers-reduced-motion: reduce) {
  .ai-avatar--thinking {
    animation: none;
  }
}
</style>
