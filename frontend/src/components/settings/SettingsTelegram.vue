<script setup>
// Pairing the account with the Telegram bot: ask for a one-time code, open the
// bot with it, and the chat links itself. Disconnecting is one button.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import AppButton from '@/components/ui/AppButton.vue'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import { createTelegramCode, getTelegram, unlinkTelegram } from '@/api/telegram'

const { t, locale } = useI18n()

const state = ref(null)
const invite = ref(null) // { code, deep_link, expires_at }
const busy = ref(false)
const error = ref('')

async function load() {
  try {
    state.value = await getTelegram()
  } catch (e) {
    error.value = e?.response?.data?.detail || t('common.error')
  }
}
onMounted(load)

async function connect() {
  busy.value = true
  error.value = ''
  try {
    invite.value = await createTelegramCode()
  } catch (e) {
    error.value = e?.response?.data?.detail || t('common.error')
  } finally {
    busy.value = false
  }
}

async function disconnect() {
  busy.value = true
  try {
    state.value = await unlinkTelegram()
    invite.value = null
  } catch (e) {
    error.value = e?.response?.data?.detail || t('common.error')
  } finally {
    busy.value = false
  }
}

const chatName = computed(() => {
  const chat = state.value?.chat
  if (!chat) return ''
  return chat.username ? `@${chat.username}` : chat.first_name || ''
})

const linkedDate = computed(() =>
  state.value?.chat ? new Date(state.value.chat.linked_at).toLocaleDateString(locale.value, { day: 'numeric', month: 'long' }) : '',
)

const NUDGES = { daily: 'telegram.nudgesDaily', weekly: 'telegram.nudgesWeekly', off: 'telegram.nudgesOff' }
</script>

<template>
  <div>
    <h2 class="text-base font-bold text-slate-900 dark:text-white">{{ $t('telegram.title') }}</h2>
    <p class="mt-1 max-w-xl text-sm text-slate-500">{{ $t('telegram.intro') }}</p>

    <p v-if="error" role="alert" class="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>

    <LoadingSkeleton v-if="!state" height="h-24" rounded="rounded-3xl" class="mt-6" />

    <p v-else-if="!state.enabled" class="mt-6 rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-600 dark:bg-surface-2 dark:text-slate-300">
      {{ $t('telegram.off') }}
    </p>

    <!-- Linked -->
    <div v-else-if="state.linked" class="card mt-6 p-5">
      <div class="flex flex-wrap items-center gap-3">
        <span class="flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-50 text-sky-600 dark:bg-sky-500/15 dark:text-sky-300">
          <Icon name="send" class="h-5 w-5" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="font-semibold text-slate-800 dark:text-slate-100">{{ $t('telegram.connected', { name: chatName }) }}</p>
          <p class="text-xs text-slate-400">{{ $t('telegram.since', { date: linkedDate }) }}</p>
        </div>
        <AppButton variant="outline" size="sm" :disabled="busy" @click="disconnect">{{ $t('telegram.disconnect') }}</AppButton>
      </div>
      <div class="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4 text-sm dark:border-hairline">
        <span class="text-slate-500">{{ $t('telegram.nudges') }}:</span>
        <b class="font-semibold text-slate-800 dark:text-slate-100">{{ $t(NUDGES[state.chat.nudges]) }}</b>
        <span class="text-xs text-slate-400">· {{ $t('telegram.nudgesHint') }}</span>
      </div>
    </div>

    <!-- Not linked -->
    <div v-else class="card mt-6 p-5">
      <template v-if="invite">
        <p class="text-sm text-slate-600 dark:text-slate-300">{{ $t('telegram.codeHint') }}</p>
        <p class="mt-3 text-xs font-semibold uppercase tracking-wider text-slate-400">{{ $t('telegram.code') }}</p>
        <p class="mt-1 select-all font-mono text-2xl font-bold tracking-[0.2em] text-slate-900 dark:text-white">{{ invite.code }}</p>
        <AppButton :href="invite.deep_link" icon="send" class="mt-4" target="_blank" rel="noopener">
          {{ $t('telegram.open') }}
        </AppButton>
      </template>
      <template v-else>
        <div class="flex flex-wrap items-center gap-3">
          <span class="flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-50 text-sky-600 dark:bg-sky-500/15 dark:text-sky-300">
            <Icon name="send" class="h-5 w-5" />
          </span>
          <p class="min-w-0 flex-1 text-sm text-slate-600 dark:text-slate-300">@{{ state.bot }}</p>
          <AppButton size="sm" icon="send" :disabled="busy" @click="connect">{{ $t('telegram.connect') }}</AppButton>
        </div>
      </template>
    </div>
  </div>
</template>
