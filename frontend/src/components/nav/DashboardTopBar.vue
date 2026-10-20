<script setup>
// Full-width application navbar. Brand on the left; streak, coins, theme,
// language and the profile dropdown clustered on the right. Rendered fixed by
// DashboardLayout (fallthrough classes land on the <header> root).
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import BrandMark from '@/components/ui/BrandMark.vue'
import Icon from '@/components/ui/Icon.vue'
import LanguageSwitcher from '@/components/ui/LanguageSwitcher.vue'
import ThemeToggle from '@/components/ui/ThemeToggle.vue'
import UserPill from '@/components/ui/UserPill.vue'
import { useSharedStats } from '@/composables/useSharedStats'
import { useSidebar } from '@/composables/useSidebar'

const { data: stats } = useSharedStats()
const { docked, drawerOpen, toggleDrawer } = useSidebar()
const streak = computed(() => stats.value?.day_streak ?? 0)
const coins = computed(() => stats.value?.coins ?? 0)
</script>

<template>
  <header class="h-16 border-b border-slate-200 bg-surface/95 backdrop-blur dark:border-hairline">
    <div class="flex h-full items-center justify-between gap-2 px-3 sm:gap-3 sm:px-6">
      <div class="flex items-center gap-1.5 sm:gap-2">
        <!-- Drawer trigger — only when the rail isn't docked. -->
        <button
          v-if="!docked"
          type="button"
          class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2"
          :aria-label="$t(drawerOpen ? 'nav.closeMenu' : 'nav.menu')"
          :aria-expanded="drawerOpen"
          @click="toggleDrawer"
        >
          <Icon :name="drawerOpen ? 'x' : 'menu'" class="h-5 w-5" />
        </button>

        <!-- Brand -->
        <RouterLink :to="{ name: 'dashboard' }" class="flex items-center gap-2">
          <BrandMark class="h-8 w-8 rounded-lg" />
          <span class="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white">
            {{ $t('common.appName') }}
          </span>
        </RouterLink>
      </div>

      <!-- Metrics + profile -->
      <div class="flex items-center gap-2">
        <!-- Day streak -->
        <div
          class="hidden items-center gap-1.5 rounded-full bg-orange-50 px-3 py-1.5 text-sm font-semibold text-orange-600 sm:flex dark:bg-orange-500/15 dark:text-orange-300"
          role="img"
          :aria-label="`${streak} ${$t('common.streakDays')}`"
          :title="$t('common.streakDays')"
        >
          <Icon name="flame" filled class="h-4 w-4" />
          {{ streak }}
        </div>
        <!-- Coins -->
        <div
          class="hidden items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1.5 text-sm font-semibold text-amber-600 sm:flex dark:bg-amber-500/15 dark:text-amber-300"
          role="img"
          :aria-label="`${coins} ${$t('common.coins')}`"
          :title="$t('common.coins')"
        >
          <Icon name="coin" class="h-4 w-4" />
          {{ coins }}
        </div>

        <ThemeToggle />
        <LanguageSwitcher />
        <UserPill />
      </div>
    </div>
  </header>
</template>
