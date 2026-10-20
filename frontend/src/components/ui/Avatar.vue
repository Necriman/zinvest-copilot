<script setup>
// Uploaded picture when there is one, initials otherwise. A broken or missing
// image falls back to the initials rather than showing a torn-image icon.
import { computed, ref, watch } from 'vue'

const props = defineProps({
  name: { type: String, default: '' },
  src: { type: String, default: '' },
  size: { type: String, default: 'h-8 w-8 text-xs' },
  rounded: { type: String, default: 'rounded-full' },
})

const failed = ref(false)
watch(
  () => props.src,
  () => {
    failed.value = false
  },
)

const showImage = computed(() => !!props.src && !failed.value)

const initials = computed(() => {
  const parts = (props.name || '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '·'
  return (parts[0][0] + (parts[1]?.[0] || '')).toUpperCase()
})
</script>

<template>
  <img
    v-if="showImage"
    :src="src"
    :alt="name"
    class="inline-block shrink-0 bg-slate-100 object-cover dark:bg-surface-2"
    :class="[size, rounded]"
    @error="failed = true"
  />
  <span
    v-else
    class="inline-flex shrink-0 items-center justify-center bg-brand-600 font-bold text-white"
    :class="[size, rounded]"
  >
    {{ initials }}
  </span>
</template>
