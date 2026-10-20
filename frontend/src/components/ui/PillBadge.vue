<script setup>
import { computed } from 'vue'

import Icon from './Icon.vue'

const props = defineProps({
  color: { type: String, default: 'slate' }, // brand|cash|startup|risk|budget|invest|slate|amber
  variant: { type: String, default: 'soft' }, // solid|soft
  icon: { type: String, default: '' },
  label: { type: String, default: '' },
  size: { type: String, default: 'md' }, // sm|md
})

// Static class maps — Tailwind v4 needs whole class strings, not built at runtime.
const SOLID = {
  brand: 'bg-brand-600 text-white',
  cash: 'bg-cash text-white',
  startup: 'bg-startup text-white',
  risk: 'bg-risk text-white',
  budget: 'bg-budget text-white',
  invest: 'bg-invest text-white',
  slate: 'bg-slate-900 text-white',
  amber: 'bg-amber-500 text-white',
}
const SOFT = {
  brand: 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300',
  cash: 'bg-green-50 text-green-700 dark:bg-green-500/15 dark:text-green-300',
  startup: 'bg-pink-50 text-pink-700 dark:bg-pink-500/15 dark:text-pink-300',
  risk: 'bg-violet-50 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300',
  budget: 'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
  invest: 'bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300',
  slate: 'bg-slate-100 text-slate-600 dark:bg-surface-2 dark:text-slate-300',
  amber: 'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
}

const SIZES = { sm: 'px-2.5 py-1 text-xs', md: 'px-3.5 py-1.5 text-sm' }

const cls = computed(() => {
  const palette = props.variant === 'solid' ? SOLID : SOFT
  return [palette[props.color] || palette.slate, SIZES[props.size] || SIZES.md]
})
const iconSize = computed(() => (props.size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'))
</script>

<template>
  <span class="pill" :class="cls">
    <Icon v-if="icon" :name="icon" :class="iconSize" />
    <slot>{{ label }}</slot>
  </span>
</template>
