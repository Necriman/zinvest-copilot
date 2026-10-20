<script setup>
// The bear's head in a circle, for chat messages and small badges. Crops the
// full-body sticker instead of shipping a separate image.
//
// The window is measured, not guessed: in the 384px stickers the growth arrow
// sits at 10–20% of the height, the head at 18–54%, the glasses at 27–40% and
// the necklace at 50–65%, all centred on x=50%. Showing 20–54% therefore fills
// the circle with the face and leaves out both the arrow above it and the
// necklace below — at a 32px avatar that was the difference between a bear and
// a yellow smudge sitting on a blue one.
import { computed } from 'vue'

import { stickerUrl } from '@/composables/useMascot'

const props = defineProps({ name: { type: String, default: 'idle' } })
const src = computed(() => stickerUrl(props.name))
</script>

<template>
  <span class="relative block shrink-0 overflow-hidden rounded-full bg-brand-50 dark:bg-brand-500/15" aria-hidden="true">
    <img :src="src" alt="" class="absolute left-1/2 top-[-59%] h-[294%] w-[294%] max-w-none -translate-x-1/2" draggable="false" />
  </span>
</template>
