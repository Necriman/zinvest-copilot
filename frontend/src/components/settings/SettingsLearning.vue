<script setup>
/** Learning — the personalised study plan built from the sign-up assessment. */
import { onMounted, ref } from 'vue'

import InlineLoader from '@/components/ui/InlineLoader.vue'

import { getOnboarding, regenerateStudyPlan } from '@/api/onboarding'
import { useTask } from '@/composables/useTask'

const { state, run } = useTask()
const plan = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    plan.value = await getOnboarding()
  } catch {
    plan.value = null
  } finally {
    loading.value = false
  }
})

const rebuild = () =>
  run(async () => {
    plan.value = { ...plan.value, ...(await regenerateStudyPlan()) }
  })
</script>

<template>
  <div>
    <h2 class="text-base font-bold text-slate-900 dark:text-white">{{ $t('settings.studyPlan') }}</h2>
    <p class="mt-1 text-sm text-slate-500">{{ $t('settings.studyPlanHint') }}</p>

    <InlineLoader v-if="loading" class="mt-6" />

    <template v-else-if="plan">
      <span
        class="pill mt-5 inline-flex bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-surface-2 dark:text-slate-300"
      >
        {{ $t(plan.plan?.source === 'ai' ? 'settings.planAi' : 'settings.planDefault') }}
      </span>

      <dl class="mt-4 grid gap-4 sm:grid-cols-3">
        <div class="rounded-2xl bg-slate-50 p-4 dark:bg-surface-2/50">
          <dt class="text-xs uppercase tracking-wide text-slate-400">{{ $t('settings.level') }}</dt>
          <dd class="mt-1 font-medium text-slate-800 dark:text-ink">
            {{ plan.completed ? $t(`onboarding.level.${plan.level}`) : '—' }}
          </dd>
        </div>
        <div class="rounded-2xl bg-slate-50 p-4 dark:bg-surface-2/50">
          <dt class="text-xs uppercase tracking-wide text-slate-400">{{ $t('settings.quizScore') }}</dt>
          <dd class="mt-1 font-medium text-slate-800 dark:text-ink">
            {{ plan.completed ? plan.quiz_score + '%' : '—' }}
          </dd>
        </div>
        <div class="rounded-2xl bg-slate-50 p-4 dark:bg-surface-2/50">
          <dt class="text-xs uppercase tracking-wide text-slate-400">{{ $t('settings.lessons') }}</dt>
          <dd class="mt-1 font-medium text-slate-800 dark:text-ink">{{ plan.plan?.lesson_count || 0 }}</dd>
        </div>
      </dl>

      <p v-if="plan.plan?.rationale" class="mt-4 text-sm text-slate-500">{{ plan.plan.rationale }}</p>
      <p v-if="state.error" class="mt-4 text-sm text-red-500">{{ state.error }}</p>

      <div class="mt-5 flex flex-wrap gap-2">
        <RouterLink
          :to="{ name: 'onboarding' }"
          class="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          {{ $t(plan.completed ? 'settings.retakeAssessment' : 'settings.takeAssessment') }}
        </RouterLink>
        <button
          v-if="plan.completed"
          type="button"
          :disabled="state.busy"
          class="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50 dark:border-hairline dark:text-slate-300 dark:hover:bg-surface-2"
          @click="rebuild"
        >
          {{ state.busy ? $t('onboarding.building') : $t('settings.regenerate') }}
        </button>
      </div>
    </template>
  </div>
</template>
