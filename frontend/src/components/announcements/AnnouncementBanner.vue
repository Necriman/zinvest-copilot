<script setup>
// One announcement from the team: a slim coloured strip with an optional link.
// Shared by the learner's announcement bar and the admin preview, so what the
// team sees is what learners get.
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'

const props = defineProps({
  item: { type: Object, required: true }, // { title, body, link_url, link_label, level }
  dismissible: { type: Boolean, default: false },
  maintenance: { type: Boolean, default: false },
})
const emit = defineEmits(['dismiss'])

const TONES = {
  info: 'border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-400/25 dark:bg-blue-500/10 dark:text-blue-100',
  success: 'border-green-200 bg-green-50 text-green-900 dark:border-green-400/25 dark:bg-green-500/10 dark:text-green-100',
  warning: 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-400/25 dark:bg-amber-500/10 dark:text-amber-100',
}
const ICONS = { info: 'bell', success: 'sparkles', warning: 'alert' }

const level = computed(() => (props.maintenance ? 'warning' : TONES[props.item.level] ? props.item.level : 'info'))

// The server only accepts app paths and https links; check again before rendering.
const link = computed(() => {
  const url = String(props.item.link_url || '').trim()
  if (!url || /[\\\s]/.test(url)) return null
  if (url.startsWith('/') && !url.startsWith('//')) return { internal: true, url }
  if (/^https:\/\/[^/]/i.test(url)) return { internal: false, url }
  return null
})
</script>

<template>
  <div class="flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm" :class="TONES[level]" :role="maintenance ? 'alert' : 'status'">
    <Icon :name="ICONS[level]" class="mt-0.5 h-4 w-4 shrink-0 opacity-80" />
    <div class="min-w-0 flex-1">
      <p class="font-semibold">{{ item.title }}</p>
      <p v-if="item.body" class="mt-0.5 whitespace-pre-line break-words opacity-90">{{ item.body }}</p>
      <template v-if="link">
        <RouterLink v-if="link.internal" :to="link.url" class="mt-1.5 inline-flex font-semibold underline underline-offset-2">
          {{ item.link_label || link.url }}
        </RouterLink>
        <a v-else :href="link.url" target="_blank" rel="noopener noreferrer" class="mt-1.5 inline-flex font-semibold underline underline-offset-2">
          {{ item.link_label || link.url }}
        </a>
      </template>
    </div>
    <button
      v-if="dismissible"
      type="button"
      class="-mr-1 -mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full opacity-60 transition hover:bg-black/5 hover:opacity-100 dark:hover:bg-white/10"
      :aria-label="$t('admin.banner.dismiss')"
      @click="emit('dismiss')"
    >
      <Icon name="x" class="h-4 w-4" />
    </button>
  </div>
</template>
