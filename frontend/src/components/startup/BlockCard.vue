<script setup>
// Shared shell for a My Startup workspace block: a .card with an icon + title
// header, an optional right-aligned action slot, and the block body in the
// default slot.
import Icon from '@/components/ui/Icon.vue'

defineProps({
  icon: { type: String, default: 'store' },
  iconColor: { type: String, default: 'text-brand-600' },
  iconBg: { type: String, default: 'bg-brand-50 dark:bg-brand-500/15' },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
})
</script>

<template>
  <section class="card flex min-w-0 flex-col p-5">
    <header class="mb-4 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
      <div class="flex min-w-[10rem] flex-1 items-center gap-2.5">
        <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl" :class="iconBg">
          <Icon :name="icon" class="h-5 w-5" :class="iconColor" />
        </span>
        <div class="min-w-0">
          <p class="truncate font-bold text-slate-900 dark:text-white">{{ title }}</p>
          <p v-if="subtitle" class="truncate text-xs text-slate-400">{{ subtitle }}</p>
        </div>
      </div>
      <div v-if="$slots.action" class="shrink-0">
        <slot name="action" />
      </div>
    </header>
    <slot />
  </section>
</template>
