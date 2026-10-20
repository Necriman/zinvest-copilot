<script setup>
import Icon from './Icon.vue'
import LoadingSkeleton from './LoadingSkeleton.vue'

defineProps({
  icon: { type: String, default: 'chart' },
  iconColor: { type: String, default: 'text-brand-600' },
  iconBg: { type: String, default: 'bg-brand-50 dark:bg-brand-500/15' },
  label: { type: String, default: '' },
  sub: { type: String, default: '' },
  value: { type: [String, Number], default: '' },
  loading: { type: Boolean, default: false },
})
</script>

<template>
  <div class="card p-5">
    <div class="flex h-10 w-10 items-center justify-center rounded-xl" :class="iconBg">
      <Icon :name="icon" class="h-5 w-5" :class="iconColor" />
    </div>
    <div class="mt-5">
      <LoadingSkeleton v-if="loading" width="w-16" height="h-8" />
      <p v-else class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
        {{ value }}
      </p>
      <p class="mt-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{{ label }}</p>
      <p v-if="sub" class="text-xs text-slate-400">{{ sub }}</p>
    </div>
  </div>
</template>
