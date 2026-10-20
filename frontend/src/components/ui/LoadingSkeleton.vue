<script setup>
defineProps({
  width: { type: String, default: 'w-full' },
  height: { type: String, default: 'h-4' },
  rounded: { type: String, default: 'rounded-lg' },
})
</script>

<template>
  <div
    class="animate-pulse bg-slate-200/70 dark:bg-surface-2/60"
    :class="[width, height, rounded]"
  />
</template>
