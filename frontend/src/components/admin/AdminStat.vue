<script setup>
// One number on the admin overview: label, value, and a quiet line of context.
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'

defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '' },
  hint: { type: String, default: '' },
  icon: { type: String, default: '' },
  tone: { type: String, default: 'brand' }, // brand | green | amber | red | slate
  loading: { type: Boolean, default: false },
})

const TONES = {
  brand: 'bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300',
  green: 'bg-green-50 text-green-600 dark:bg-green-500/15 dark:text-green-300',
  amber: 'bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300',
  red: 'bg-red-50 text-red-600 dark:bg-red-500/15 dark:text-red-300',
  slate: 'bg-slate-100 text-slate-500 dark:bg-surface-2 dark:text-slate-300',
}
</script>

<template>
  <div class="card flex flex-col p-4">
    <div class="flex items-center gap-2">
      <span v-if="icon" class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg" :class="TONES[tone] || TONES.brand">
        <Icon :name="icon" class="h-4 w-4" />
      </span>
      <p class="min-w-0 text-[13px] font-semibold leading-tight text-slate-500 dark:text-slate-400">{{ label }}</p>
    </div>
    <LoadingSkeleton v-if="loading" width="w-20" height="h-8" class="mt-3" />
    <p v-else class="mt-3 text-[1.75rem] font-extrabold leading-none tracking-tight text-slate-900 tabular-nums dark:text-white">
      {{ value }}
    </p>
    <p v-if="hint && !loading" class="mt-2 text-xs leading-snug text-slate-400">{{ hint }}</p>
    <slot />
  </div>
</template>
