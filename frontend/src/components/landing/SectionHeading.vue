<script setup>
/** Eyebrow + title + optional lede, shared by every landing section. */
defineProps({
  eyebrow: { type: String, default: '' },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  align: { type: String, default: 'center' }, // center|left
})
</script>

<template>
  <div :class="align === 'center' ? 'mx-auto max-w-2xl text-center' : 'max-w-xl'">
    <p
      v-if="eyebrow"
      class="text-xs font-bold uppercase tracking-[0.18em] text-brand-600 dark:text-brand-400"
    >
      {{ eyebrow }}
    </p>
    <h2
      class="mt-3 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl dark:text-white"
    >
      {{ title }}
    </h2>
    <p v-if="subtitle" class="mt-4 text-base leading-relaxed text-slate-500 dark:text-slate-400">
      {{ subtitle }}
    </p>
  </div>
</template>
