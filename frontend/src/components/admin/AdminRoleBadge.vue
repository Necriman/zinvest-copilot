<script setup>
import PillBadge from '@/components/ui/PillBadge.vue'

defineProps({
  role: { type: String, default: '' },
})

const COLORS = { owner: 'risk', admin: 'brand', support: 'cash', content: 'budget', analyst: 'invest' }
</script>

<template>
  <PillBadge v-if="role" :color="COLORS[role] || 'slate'" size="sm">{{ $t(`admin.roles.${role}`) }}</PillBadge>
</template>
