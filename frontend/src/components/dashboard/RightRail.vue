<script setup>
import { computed, ref } from 'vue'

import Icon from '@/components/ui/Icon.vue'
import StreakCalendar from './StreakCalendar.vue'
import CoinsCard from './CoinsCard.vue'
import WeeklyProgressCard from './WeeklyProgressCard.vue'
import FinancialGoalCard from './FinancialGoalCard.vue'
import TasksChecklist from './TasksChecklist.vue'
import { useSharedStats } from '@/composables/useSharedStats'
import { useAuthStore } from '@/store/auth'

const { data: stats, reload } = useSharedStats()
const auth = useAuthStore()
const name = computed(() => auth.user?.first_name || auth.user?.email?.split('@')[0] || 'You')

const TABS = [
  { key: 'progress', label: 'dashboard.tabProgress', icon: 'chart' },
  { key: 'tasks', label: 'dashboard.tabTasks', icon: 'checkCircle' },
]
const tab = ref('progress') // 'progress' | 'tasks'

function select(key) {
  if (key !== tab.value) tab.value = key
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Tab switcher -->
    <div class="flex rounded-full bg-slate-100 p-1 dark:bg-surface-2">
      <button
        v-for="t in TABS"
        :key="t.key"
        type="button"
        class="flex flex-1 items-center justify-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold transition-all duration-200 ease-in-out"
        :class="
          tab === t.key
            ? 'bg-white text-brand-700 shadow-sm dark:bg-surface dark:text-brand-300'
            : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
        "
        @click="select(t.key)"
      >
        <Icon :name="t.icon" class="h-4 w-4" />
        {{ $t(t.label) }}
      </button>
    </div>

    <!-- Panels swap with the same motion as a route change (see the
         <router-view> in DashboardLayout), so switching tabs feels like moving
         between pages rather than a separate effect. -->
    <div>
      <Transition name="fade-slide" mode="out-in">
        <div v-if="tab === 'progress'" key="progress" class="flex flex-col gap-4">
          <StreakCalendar
            :streak="stats?.day_streak || 0"
            :longest="stats?.longest_streak || 0"
            :week="stats?.week || []"
            :active-today="stats?.streak_active_today || false"
          />
          <CoinsCard :coins="stats?.coins || 0" />
          <WeeklyProgressCard :name="name" />
        </div>
        <div v-else key="tasks" class="flex flex-col gap-4">
          <TasksChecklist :tasks="stats?.tasks || []" @changed="reload" />
          <FinancialGoalCard />
        </div>
      </Transition>
    </div>
  </div>
</template>
