<script setup>
// The bear's nudge at the foot of the sidebar: it naps when there is no streak,
// cheers you on to keep one alive, and celebrates once today counts.
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import BearSticker from '@/components/mascot/BearSticker.vue'
import { useSharedStats } from '@/composables/useSharedStats'

const { data: stats } = useSharedStats()
const streak = computed(() => stats.value?.day_streak || 0)
const done = computed(() => !!stats.value?.streak_active_today)
const sticker = computed(() => (done.value ? 'happy' : streak.value > 0 ? 'cheer' : 'sleep'))
const text = computed(() => (done.value ? 'today.streakDone' : streak.value > 0 ? 'today.keepStreak' : 'today.startStreak'))
</script>

<template>
  <RouterLink
    v-if="stats"
    :to="{ name: 'dashboard' }"
    class="flex items-center gap-2 rounded-2xl border border-hairline bg-white p-2 pr-3 transition hover:border-brand-200 dark:bg-surface"
  >
    <BearSticker :name="sticker" class="h-14 w-14 shrink-0" />
    <span class="text-xs font-medium leading-snug text-slate-600 dark:text-slate-300">{{ $t(text, { n: streak }) }}</span>
  </RouterLink>
</template>
