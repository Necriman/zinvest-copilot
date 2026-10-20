<script setup>
defineProps({
  title: { type: String, required: true },
  intro: { type: String, default: '' },
})
</script>

<template>
  <header class="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div class="min-w-0">
      <slot name="above" />
      <h1 class="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">{{ title }}</h1>
      <p v-if="intro" class="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">{{ intro }}</p>
    </div>
    <div v-if="$slots.default" class="flex flex-wrap items-center gap-2">
      <slot />
    </div>
  </header>
</template>
