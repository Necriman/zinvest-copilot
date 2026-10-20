<script setup>
/**
 * A still of the bear for small, frequent spots (answer feedback, empty
 * states, the study map) where a live 3D scene would cost more than it adds.
 * The stills are rendered from the same model as the live bear.
 */
import { computed } from 'vue'

import { stickerUrl } from '@/composables/useMascot'

const props = defineProps({
  name: { type: String, default: 'idle' },
  alt: { type: String, default: '' }, // decorative by default
  pop: { type: Boolean, default: false }, // bounce in when it appears
  float: { type: Boolean, default: false }, // gentle idle bob
})
const src = computed(() => stickerUrl(props.name))
</script>

<template>
  <img
    :key="src"
    :src="src"
    :alt="alt"
    :aria-hidden="alt ? undefined : 'true'"
    class="zs"
    :class="{ 'zs--pop': pop, 'zs--float': float }"
    draggable="false"
    decoding="async"
    loading="lazy"
  />
</template>

<style scoped>
/* In the components layer so utilities on the tag (hidden, sm:block...) still win. */
@layer components { .zs { display: block; } }
.zs { object-fit: contain; user-select: none; }
.zs--pop { animation: zs-pop 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both; }
.zs--float { animation: zs-float 3.2s ease-in-out -1.1s infinite; }
.zs--pop.zs--float { animation: zs-pop 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both, zs-float 3.2s ease-in-out 0.45s infinite; }
@keyframes zs-pop { from { transform: scale(0.6) translateY(12%); opacity: 0; } to { transform: none; opacity: 1; } }
@keyframes zs-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5%); } }
@media (prefers-reduced-motion: reduce) { .zs { animation: none !important; } }
</style>
