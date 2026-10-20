<script setup>
import BearSticker from '@/components/mascot/BearSticker.vue'
import Icon from './Icon.vue'

defineProps({
  icon: { type: String, default: 'note' },
  bear: { type: String, default: '' }, // a mascot sticker instead of the icon
  title: { type: String, default: '' },
  message: { type: String, default: '' },
})
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
    <BearSticker v-if="bear" :name="bear" pop class="h-28 w-28" />
    <div v-else class="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400 dark:bg-surface-2">
      <Icon :name="icon" class="h-6 w-6" />
    </div>
    <p v-if="title" class="font-semibold text-slate-700 dark:text-slate-200">{{ title }}</p>
    <p v-if="message" class="max-w-sm text-sm text-slate-500">{{ message }}</p>
    <slot />
  </div>
</template>
