<script setup>
/**
 * "Who to connect with": the AI reads this startup (profile + intake answers)
 * and suggests up to three public founders to talk to or build with. The
 * conversation itself happens in the Network page; this block is the entry.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import Avatar from '@/components/ui/Avatar.vue'
import BlockCard from './BlockCard.vue'
import { connectFounder, getNetwork, recommendFounders } from '@/api/network'

const props = defineProps({
  profile: { type: Object, default: () => ({}) },
})
const { t } = useI18n()

const founders = ref([])
const connections = ref([])
const matches = ref([])
const busy = ref(false)
const error = ref('')
const notice = ref('')
const asked = ref(false)

const isPublic = computed(() => !!props.profile?.public_visible)
const suggested = computed(() =>
  matches.value.map((m) => ({ ...m, founder: founders.value.find((f) => f.id === m.id) })).filter((m) => m.founder),
)
const connection = (id) => connections.value.find((c) => c.peer === id)

async function suggest() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    const [result, network] = await Promise.all([recommendFounders(), getNetwork()])
    founders.value = network.founders
    connections.value = network.connections
    matches.value = result.matches
    asked.value = true
    notice.value = result.is_stub ? t('business.aiUnavailable') : result.matches.length ? '' : t('network.noMatches')
  } catch (e) {
    error.value = e?.response?.data?.detail || e.message
  } finally {
    busy.value = false
  }
}

async function connect(id) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const c = await connectFounder(id)
    connections.value = [...connections.value.filter((x) => x.peer !== id), c]
  } catch (e) {
    error.value = e?.response?.data?.detail || e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BlockCard
    icon="globe"
    icon-color="text-emerald-600"
    icon-bg="bg-emerald-50 dark:bg-emerald-500/15"
    :title="$t('matches.title')"
    :subtitle="$t('matches.subtitle')"
  >
    <template #action>
      <RouterLink :to="{ name: 'network' }" class="rounded-lg px-2.5 py-1.5 text-sm font-semibold text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-500/10">
        {{ $t('network.title') }}
      </RouterLink>
    </template>

    <p class="text-sm text-slate-500">{{ $t('matches.intro') }}</p>
    <button type="button" :disabled="busy" class="pill mt-3 self-start bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40" @click="suggest">
      {{ busy ? '…' : $t(asked ? 'matches.again' : 'matches.suggest') }}
    </button>
    <p v-if="!isPublic" class="mt-3 rounded-xl bg-amber-50 p-3 text-xs text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">{{ $t('matches.publishHint') }}</p>

    <ul v-if="suggested.length" class="mt-4 space-y-3">
      <li v-for="m in suggested" :key="m.id" class="rounded-2xl border border-hairline p-3">
        <div class="flex items-center gap-3">
          <Avatar :name="m.founder.founder" :src="m.founder.photo_url || ''" size="h-10 w-10 text-sm" />
          <div class="min-w-0 flex-1">
            <p class="truncate font-semibold">{{ m.founder.founder }}</p>
            <p class="truncate text-xs text-brand-600">{{ m.founder.name }}<template v-if="m.founder.industry"> · {{ m.founder.industry }}</template></p>
          </div>
          <button v-if="!connection(m.id)" type="button" :disabled="busy || !isPublic" class="min-h-9 shrink-0 rounded-xl bg-brand-600 px-3 text-xs font-semibold text-white disabled:opacity-40" @click="connect(m.id)">
            {{ $t('network.connect') }}
          </button>
          <span v-else class="shrink-0 text-xs text-slate-500">{{ $t(connection(m.id).accepted ? 'matches.connected' : 'network.pending') }}</span>
        </div>
        <p class="mt-2 text-sm text-slate-600 dark:text-slate-300">{{ m.reason }}</p>
      </li>
    </ul>
    <p v-if="notice" role="status" class="mt-3 text-sm text-slate-500">{{ notice }}</p>
    <p v-if="error" role="alert" class="mt-3 text-sm text-red-600">{{ error }}</p>
  </BlockCard>
</template>
