<script setup>
/**
 * The "Approve?" gate under every piece of work the Copilot proposes: what an
 * approval would change, and Yes / No. Once decided it shows the decision and
 * what actually changed. Nothing in the business's data changes before "Yes".
 *
 * Keyboard: both answers are plain buttons in reading order (Yes first). The
 * panel is named "Approve? <step title>" and each button is described by the
 * list of what it would change; after a decision, focus moves to the result
 * line so it is not dropped on the page body when the buttons disappear.
 */
import { nextTick, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'

import Icon from '@/components/ui/Icon.vue'
import { decideAction } from '@/api/copilot'

const props = defineProps({
  action: { type: Object, required: true },
  // id of the step's heading, so the group reads as "Approve? Analysis".
  labelledby: { type: String, default: '' },
})
const emit = defineEmits(['decided'])
const { t } = useI18n()

const uid = useId()
const busy = ref('') // 'approve' | 'reject' while the answer is being sent
const error = ref('')
const result = ref(null)

async function decide(decision) {
  if (busy.value) return
  busy.value = decision
  error.value = ''
  let decided = null
  try {
    decided = (await decideAction(props.action.id, decision)).action
  } catch (e) {
    // 409: it was already decided (another tab) — show that decision.
    if (e?.response?.status === 409 && e.response.data?.action) decided = e.response.data.action
    else error.value = e?.response?.data?.detail || t('errors.generic')
  } finally {
    busy.value = ''
  }
  if (decided) {
    emit('decided', decided)
    await nextTick()
    result.value?.focus()
  }
}

// The count picks the English singular / plural (ru and uz are written to need none).
const effectText = (e) => t(`copilot.eff_${e.type}`, { count: e.count ?? '' }, Number(e.count) || 0)
const outcomeText = (o) => t(`copilot.out_${o.type}`, { count: o.count ?? '', what: o.what ? t(`copilot.what_${o.what}`) : '' }, Number(o.count) || 0)
</script>

<template>
  <div
    v-if="action.status === 'pending'"
    class="mt-4 rounded-2xl border-2 border-amber-300 bg-amber-50 p-4 dark:border-amber-500/40 dark:bg-amber-500/10"
    role="group"
    :aria-labelledby="[`${uid}-q`, labelledby].filter(Boolean).join(' ')"
    :aria-busy="!!busy"
  >
    <p :id="`${uid}-q`" class="flex items-center gap-2 text-base font-extrabold text-amber-900 dark:text-amber-100">
      <Icon name="shield" class="h-5 w-5 shrink-0" />{{ $t('copilot.approveQ') }}
    </p>
    <div :id="`${uid}-effects`">
      <p class="mt-1 text-sm text-amber-900/80 dark:text-amber-100/80">{{ $t('copilot.willDo') }}</p>
      <ul class="mt-1 list-disc space-y-0.5 pl-5 text-sm text-amber-900 dark:text-amber-100">
        <li v-for="(e, i) in action.effects" :key="i">{{ effectText(e) }}</li>
      </ul>
    </div>
    <div class="mt-3 flex flex-wrap gap-2">
      <button
        type="button"
        :disabled="!!busy"
        :aria-describedby="`${uid}-effects`"
        class="pill min-h-11 justify-center bg-emerald-700 px-5 text-sm font-bold text-white hover:bg-emerald-800 disabled:cursor-wait disabled:opacity-60"
        data-approve
        @click="decide('approve')"
      >
        <Icon :name="busy === 'approve' ? 'refresh' : 'check'" class="h-4 w-4 shrink-0" :class="busy === 'approve' ? 'animate-spin' : ''" />{{ $t('copilot.yes') }}
      </button>
      <button
        type="button"
        :disabled="!!busy"
        class="pill min-h-11 justify-center border border-slate-300 bg-white px-5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-wait disabled:opacity-60 dark:border-hairline dark:bg-surface dark:text-slate-200 dark:hover:bg-surface-2"
        data-reject
        @click="decide('reject')"
      >
        <Icon :name="busy === 'reject' ? 'refresh' : 'x'" class="h-4 w-4 shrink-0" :class="busy === 'reject' ? 'animate-spin' : ''" />{{ $t('copilot.no') }}
      </button>
    </div>
    <p v-if="error" role="alert" class="mt-2 text-sm text-red-700 dark:text-red-300">{{ error }}</p>
  </div>
  <p
    v-else
    ref="result"
    tabindex="-1"
    class="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 rounded-xl px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
    :class="action.status === 'approved' ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-200' : 'bg-slate-100 text-slate-600 dark:bg-surface-2 dark:text-slate-300'"
  >
    <span class="font-bold"><span aria-hidden="true">{{ action.status === 'approved' ? '✅' : '❌' }} </span>{{ action.status === 'approved' ? $t('copilot.approved') : $t('copilot.rejected') }}</span>
    <span v-for="(o, i) in action.outcome" :key="i"><span aria-hidden="true">· </span>{{ outcomeText(o) }}</span>
  </p>
</template>
