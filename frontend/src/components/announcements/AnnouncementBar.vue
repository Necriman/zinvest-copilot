<script setup>
// Team announcements above every /app page: the maintenance note (always shown
// while it is set) and live announcements, each dismissible on this device.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import AnnouncementBanner from '@/components/announcements/AnnouncementBanner.vue'
import { getAnnouncements } from '@/api/platform'

const { t } = useI18n()

const STORAGE_KEY = 'zx-dismissed-announcements'
const REFRESH_MS = 10 * 60 * 1000

const items = ref([])
const maintenance = ref('')
const dismissed = ref(readDismissed())
let fetchedAt = 0

function readDismissed() {
  try {
    const list = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

function dismiss(id) {
  dismissed.value = [...dismissed.value.filter((x) => x !== id), id].slice(-50)
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(dismissed.value))
  } catch {
    /* private mode: dismissed for this visit only */
  }
}

async function load() {
  fetchedAt = Date.now()
  try {
    const data = await getAnnouncements()
    items.value = data.announcements || []
    maintenance.value = data.maintenance_message || ''
  } catch {
    /* banners are optional; never get in the way of the page */
  }
}

function onFocus() {
  if (Date.now() - fetchedAt > REFRESH_MS) load()
}

onMounted(() => {
  load()
  window.addEventListener('focus', onFocus)
})
onBeforeUnmount(() => window.removeEventListener('focus', onFocus))

const visible = computed(() => items.value.filter((a) => !dismissed.value.includes(a.id)))
</script>

<template>
  <div v-if="maintenance || visible.length" class="space-y-2">
    <AnnouncementBanner v-if="maintenance" :item="{ title: t('admin.banner.maintenance'), body: maintenance }" maintenance />
    <AnnouncementBanner v-for="a in visible" :key="a.id" :item="a" dismissible @dismiss="dismiss(a.id)" />
  </div>
</template>
