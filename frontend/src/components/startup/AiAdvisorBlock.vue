<script setup>
/**
 * AI Advisor block: preset prompts ("What problems does my business have?",
 * "Give directions to grow") plus a free question. Every call passes a snapshot
 * of the whole startup (profile + employees + products + finance summary) as
 * context, so the model reasons over the actual company, not a blank prompt.
 */
import { computed, nextTick, ref } from 'vue'
import i18n from '@/i18n'

import Icon from '@/components/ui/Icon.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
import BlockCard from './BlockCard.vue'
import MarketResearch from './MarketResearch.vue'
import { askAdvisor } from '@/api/ai'
import AiAvatar from '@/components/ai/AiAvatar.vue'
import {
  getStartupSummary,
  listEmployees,
  listProducts,
  listAssignments,
  listStartupTodos,
  getStartupProfile,
} from '@/api/startup'

const props = defineProps({
  // Raw onboarding answers + AI assessment, passed from the profile.
  profile: { type: Object, default: () => ({}) },
})

const PRESETS = [
  'startup.advisor.presetProblems',
  'startup.advisor.presetGrowth',
  'startup.advisor.presetPricing',
]

const messages = ref([])
const input = ref('')
const loading = ref(false)
const quota = ref(null)
const thread = ref(null)

async function scrollDown() {
  await nextTick()
  const el = thread.value
  el?.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
}

async function buildContext() {
  // Pull a fresh snapshot so advice reflects the current state of the business.
  const [summary, emps, prods, assignments, todos, profile] = await Promise.all([
    getStartupSummary().catch(() => null),
    listEmployees().catch(() => null),
    listProducts().catch(() => null),
    listAssignments().catch(()=>null),
    listStartupTodos().catch(()=>null),
    getStartupProfile().catch(()=>null),
  ])
  return {
    onboarding: props.profile?.onboarding || null,
    locations:profile?.locations||[],
    demand:profile?.demand||null,
    employees:emps?.employees?.map(e=>({name:e.full_name,position:e.position,role:e.role,team:e.team,salary:e.salary}))||[],
    assignments:assignments?.assignments||[],
    todos:todos?.todos||[],
    assessment: props.profile?.blocks?.analysis || null,
    // The intake's market check, without the link list: competitors, demand, risks.
    market: marketForAdvisor(),
    finance: summary ? { revenue: summary.revenue, spending: summary.spending, net: summary.net } : null,
    employee_count: emps?.employees?.length ?? null,
    monthly_payroll: emps?.total_salary ?? null,
    products: (prods?.products || []).map((p) => ({ name: p.name, price: p.price })),
  }
}

async function ask(question) {
  const q = (question || '').trim()
  if (!q || loading.value) return
  messages.value.push({ role: 'user', text: q })
  input.value = ''
  loading.value = true
  scrollDown()
  try {
    const context = await buildContext()
    const res = await askAdvisor(q, context)
    messages.value.push({ role: 'ai', text: res.answer, stub: res.is_stub })
    quota.value = res.quota
  } catch (e) {
    messages.value.push({ role: 'ai', text: e?.response?.data?.detail || i18n.global.t('errors.generic'), error: true })
  } finally {
    loading.value = false
    scrollDown()
  }
}

const empty = computed(() => !messages.value.length)
const research = computed(() => props.profile?.blocks?.research || null)
const place = computed(() => props.profile?.onboarding?.location || '')

function marketForAdvisor() {
  if (!research.value) return null
  const { sources, ...rest } = research.value
  return rest
}
</script>

<template>
  <BlockCard
    icon="bot"
    :title="$t('startup.advisor.title')"
    :subtitle="$t('startup.advisor.subtitle')"
  >
    <template #action>
      <PillBadge v-if="quota" color="brand" variant="soft" icon="coin" size="sm">
        {{ quota.remaining }} / {{ quota.limit }}
      </PillBadge>
    </template>

    <!-- The market check from the intake, kept for later -->
    <details v-if="research" class="mb-3 rounded-2xl border border-slate-200 px-4 py-3 dark:border-hairline">
      <summary class="cursor-pointer text-sm font-bold text-slate-700 dark:text-slate-200">
        {{ $t('startup.research.eyebrow') }}
      </summary>
      <MarketResearch class="mt-3" :research="research" :place="place" />
    </details>

    <!-- Preset prompts -->
    <div class="mb-3 flex flex-wrap gap-2">
      <button
        v-for="p in PRESETS"
        :key="p"
        type="button"
        :disabled="loading"
        class="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 disabled:opacity-40 dark:border-hairline dark:text-slate-300 dark:hover:bg-brand-500/10"
        @click="ask($t(p))"
      >
        {{ $t(p) }}
      </button>
    </div>

    <div ref="thread" class="max-h-80 space-y-3 overflow-y-auto">
      <div v-if="empty" class="rounded-2xl bg-slate-50 px-4 py-6 text-center text-sm text-slate-400 dark:bg-surface-2">
        {{ $t('startup.advisor.placeholder') }}
      </div>
      <div v-for="(m, i) in messages" :key="i" class="flex items-start gap-2" :class="m.role === 'user' ? 'justify-end' : 'justify-start'">
        <AiAvatar v-if="m.role !== 'user'" class="mt-0.5 h-7 w-7" />
        <div
          class="max-w-[85%] rounded-2xl px-3.5 py-2 text-sm"
          :class="m.role === 'user'
            ? 'bg-brand-600 text-white'
            : m.error
              ? 'bg-red-50 text-red-700 dark:bg-red-500/10'
              : 'bg-slate-100 text-slate-800 dark:bg-surface-2 dark:text-ink'"
        >
          <PillBadge v-if="m.stub" color="amber" size="sm" class="mb-1.5">STUB</PillBadge>
          <p class="whitespace-pre-wrap">{{ m.text }}</p>
        </div>
      </div>
      <p v-if="loading" class="flex items-center gap-2 text-sm text-slate-400">
        <AiAvatar thinking class="h-7 w-7" />
        {{ $t('startup.advisor.thinking') }}
      </p>
    </div>

    <form class="mt-3 flex items-center gap-2" @submit.prevent="ask(input)">
      <input v-model="input" :placeholder="$t('startup.advisor.inputPlaceholder')" class="zx-input min-w-0 flex-1 py-2" />
      <button type="submit" :disabled="loading || !input.trim()" class="pill shrink-0 bg-brand-600 p-2 text-white hover:bg-brand-700 disabled:opacity-40">
        <Icon name="send" class="h-4 w-4" />
      </button>
    </form>
  </BlockCard>
</template>
