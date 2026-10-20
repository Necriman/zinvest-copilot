<script setup>
import { RouterLink } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'
import PillBadge from '@/components/ui/PillBadge.vue'

defineProps({
  item: { type: Object, required: true },
  // Icon-only rail: label + badge collapse to a centered icon (with a dot for a
  // badge) and the full label surfaces as a tooltip.
  mini: { type: Boolean, default: false },
})
defineEmits(['navigate'])

// Same weight in both states, so the label never grows and gets cut off when active.
const ACTIVE = 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300'
</script>

<template>
  <RouterLink
    :to="{ name: item.name }"
    class="group relative flex items-center rounded-xl text-sm text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2"
    :class="mini ? 'justify-center px-0 py-2.5' : 'gap-3 px-3 py-2.5'"
    :active-class="item.exact ? '' : ACTIVE"
    :exact-active-class="item.exact ? ACTIVE : ''"
    :title="mini ? $t(item.label) : undefined"
    @click="$emit('navigate')"
  >
    <span class="relative shrink-0">
      <Icon :name="item.icon" class="h-5 w-5" />
      <!-- Badge becomes a dot when there's no room for the pill. -->
      <span
        v-if="mini && item.badge"
        class="absolute -right-1 -top-0.5 h-2 w-2 rounded-full bg-brand-500 ring-2 ring-surface"
      />
    </span>
    <template v-if="!mini">
      <span class="flex-1 truncate">{{ $t(item.label) }}</span>
      <PillBadge v-if="item.badge" :color="item.badge.color" size="sm">{{ $t(item.badge.text) }}</PillBadge>
    </template>
  </RouterLink>
</template>
