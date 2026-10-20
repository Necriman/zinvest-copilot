<script setup>
/**
 * One of the clay 3D icons in /icons3d (made for this landing, in the bear's
 * palette): book, card, coins, flame, gift, growth, piggy, plane, rocket,
 * shield, target, trophy. Decorative: the text next to it carries the meaning.
 */
defineProps({ name: { type: String, required: true } })
</script>

<template>
  <img
    :src="`/icons3d/${name}.webp`"
    alt=""
    aria-hidden="true"
    width="256"
    height="256"
    class="z3-icon"
    loading="lazy"
    decoding="async"
    draggable="false"
  />
</template>
