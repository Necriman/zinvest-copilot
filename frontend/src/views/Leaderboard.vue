<script setup>
// The weekly league board: your group of 25, sorted by points earned this week.
// The top five move up a division, the bottom five move down — the zones are
// marked so it is obvious what this week is worth.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import Avatar from '@/components/ui/Avatar.vue'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
import { getLeague } from '@/api/league'

const { t, locale } = useI18n()

const data = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    data.value = await getLeague()
  } catch (e) {
    error.value = e?.response?.data?.detail || t('common.error')
  }
})

const DIVISION_COLOR = { bronze: 'budget', silver: 'slate', gold: 'amber', platinum: 'invest', diamond: 'risk' }

const endsAt = computed(() => {
  if (!data.value) return ''
  return new Date(data.value.ends_at).toLocaleString(locale.value, {
    weekday: 'long',
    hour: '2-digit',
    minute: '2-digit',
  })
})

const total = computed(() => data.value?.members.length || 0)
const demoteFrom = computed(() => (data.value?.demote ? total.value - data.value.demote + 1 : total.value + 1))

function zone(rank) {
  if (!data.value) return ''
  if (rank <= data.value.promote) return 'promote'
  if (rank >= demoteFrom.value) return 'demote'
  return ''
}
</script>

<template>
  <div>
    <header class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">{{ $t('league.title') }}</h1>
        <p class="mt-2 max-w-xl text-sm text-slate-500">{{ $t('league.intro') }}</p>
      </div>
      <PillBadge v-if="data" :color="DIVISION_COLOR[data.division] || 'slate'" icon="trophy">
        {{ $t(`league.div_${data.division}`) }}
      </PillBadge>
    </header>

    <p v-if="error" role="alert" class="mt-5 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>

    <div v-if="!data && !error" class="mt-6 space-y-3">
      <LoadingSkeleton v-for="i in 6" :key="i" height="h-14" rounded="rounded-2xl" />
    </div>

    <template v-else-if="data">
      <div class="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-slate-500">
        <span class="flex items-center gap-1.5"><Icon name="calendar" class="h-4 w-4" /> {{ $t('league.endsIn', { when: endsAt }) }}</span>
        <span v-if="data.me.rank" class="flex items-center gap-1.5">
          <Icon name="target" class="h-4 w-4" /> {{ $t('league.place', { n: data.me.rank }) }} · {{ $t('league.points', { n: data.me.points }) }}
        </span>
        <span v-if="data.last_week" class="flex items-center gap-1.5 text-slate-400">
          <Icon name="history" class="h-4 w-4" />
          {{ $t('league.lastWeek', { division: $t(`league.div_${data.last_week.division}`), rank: data.last_week.rank ?? '—' }) }}
          <template v-if="data.last_week.result">· {{ $t(`league.result${data.last_week.result.charAt(0).toUpperCase()}${data.last_week.result.slice(1)}`) }}</template>
        </span>
      </div>

      <ol class="card mt-5 divide-y divide-slate-100 overflow-hidden dark:divide-hairline">
        <li
          v-for="member in data.members"
          :key="member.id"
          class="flex items-center gap-3 px-4 py-3 sm:px-5"
          :class="[
            member.is_me ? 'bg-brand-50/70 dark:bg-brand-500/10' : '',
            zone(member.rank) === 'promote' ? 'border-l-4 border-l-green-500' : '',
            zone(member.rank) === 'demote' ? 'border-l-4 border-l-red-400' : '',
          ]"
        >
          <span
            class="w-7 shrink-0 text-center text-sm font-bold tabular-nums"
            :class="member.rank <= 3 ? 'text-amber-500' : 'text-slate-400'"
          >
            {{ member.rank }}
          </span>
          <Avatar :name="member.name" :src="member.avatar_url || ''" size="h-9 w-9 text-xs" />
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
              {{ member.name }}
              <span v-if="member.is_me" class="ml-1 text-xs font-medium text-brand-600 dark:text-brand-300">· {{ $t('league.you') }}</span>
            </p>
            <p v-if="member.rank <= data.prizes.length && member.points" class="text-xs text-amber-600 dark:text-amber-400">
              {{ $t('league.prize', { n: data.prizes[member.rank - 1] }) }}
            </p>
          </div>
          <span class="shrink-0 text-sm font-bold tabular-nums text-slate-900 dark:text-white">{{ member.points }}</span>
        </li>
      </ol>

      <div class="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500">
        <span class="flex items-center gap-2"><span class="h-3 w-1 rounded bg-green-500" /> {{ $t('league.promoteZone') }}</span>
        <span v-if="data.demote" class="flex items-center gap-2"><span class="h-3 w-1 rounded bg-red-400" /> {{ $t('league.demoteZone') }}</span>
      </div>

      <section class="card mt-6 p-5">
        <h2 class="text-sm font-bold text-slate-800 dark:text-slate-100">{{ $t('league.how') }}</h2>
        <ul class="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
          <li class="flex justify-between gap-3"><span>{{ $t('league.howLesson') }}</span><b class="tabular-nums">+{{ data.points.lesson }}</b></li>
          <li class="flex justify-between gap-3"><span>{{ $t('league.howTest') }}</span><b class="tabular-nums">+{{ data.points.test }}</b></li>
          <li class="flex justify-between gap-3"><span>{{ $t('league.howDay') }}</span><b class="tabular-nums">+{{ data.points.day }}</b></li>
        </ul>
        <p class="mt-3 text-xs text-slate-400">{{ $t('league.howFair') }}</p>
      </section>

      <p v-if="!data.me.points" class="mt-4 text-center text-sm text-slate-400">{{ $t('league.empty') }}</p>
    </template>
  </div>
</template>
