<script setup>
defineProps({
  title: { type: String, default: '' },
  hint: { type: String, default: '' },
})
</script>

<template>
  <section class="card p-4 sm:p-5">
    <div v-if="title || $slots.actions" class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <h2 class="text-sm font-bold text-slate-800 dark:text-slate-100">{{ title }}</h2>
        <p v-if="hint" class="mt-0.5 text-xs text-slate-400">{{ hint }}</p>
      </div>
      <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2">
        <slot name="actions" />
      </div>
    </div>
    <slot />
  </section>
</template>
