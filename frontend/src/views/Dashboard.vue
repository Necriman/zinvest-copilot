<script setup>
/**
 * Today. Read top to bottom it answers, in order: what should I do now (the
 * focus card), the two-minute daily habit, what else is on today's list, and
 * only then the numbers and the wider tools.
 */
import { computed } from 'vue'

import DailyCard from '@/components/dashboard/DailyCard.vue'
import GamesCard from '@/components/dashboard/GamesCard.vue'
import TodayFocus from '@/components/dashboard/TodayFocus.vue'
import TodayStats from '@/components/dashboard/TodayStats.vue'
import TodayPlanDeck from '@/components/dashboard/TodayPlanDeck.vue'
import TodayRoute from '@/components/dashboard/TodayRoute.vue'
import MyStartupWidget from '@/components/dashboard/MyStartupWidget.vue'
import { getTodayPlan } from '@/api/stats'
import { useAsyncData } from '@/composables/useAsyncData'
import { useSharedStats } from '@/composables/useSharedStats'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const { data: stats } = useSharedStats()
const { data: plan, loading: planLoading } = useAsyncData(getTodayPlan)

const name = computed(() => auth.user?.first_name || auth.user?.email?.split('@')[0] || '')

// The focus card already carries the study step, so the deck below keeps the
// rest of the day — the AI question and the startup entry — instead of
// showing the same lesson twice on one screen.
const restOfDay = computed(() => {
  if (!plan.value) return null
  const cards = (plan.value.cards || []).slice(1)
  return {
    ...plan.value,
    cards,
    done: cards.filter((c) => c.done).length,
    total: cards.length,
    minutes_left: cards.filter((c) => !c.done).reduce((sum, c) => sum + (c.minutes || 0), 0),
  }
})
</script>

<template>
  <div class="@container">
    <TodayFocus :name="name" :stats="stats" :plan="plan" :loading="planLoading" />
    <DailyCard />
    <GamesCard />
    <TodayPlanDeck v-if="!restOfDay || restOfDay.cards.length" :plan="restOfDay" :loading="planLoading" title-key="focus.restOfDay" />
    <TodayStats :stats="stats" />

    <div class="grid items-start gap-5 @3xl:grid-cols-2">
      <TodayRoute />
      <MyStartupWidget />
    </div>
  </div>
</template>
