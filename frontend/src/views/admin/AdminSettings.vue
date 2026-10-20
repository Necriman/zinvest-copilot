<script setup>
// Platform switches that work without a deploy (sign-ups, AI, voice, posting,
// a maintenance note), facts about this server, and my own two-factor.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import AdminCard from '@/components/admin/AdminCard.vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminSwitch from '@/components/admin/AdminSwitch.vue'
import AdminTotpSetup from '@/components/admin/AdminTotpSetup.vue'
import AnnouncementBanner from '@/components/announcements/AnnouncementBanner.vue'
import AppButton from '@/components/ui/AppButton.vue'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'

const { t } = useI18n()
const admin = useAdmin()
const fmt = useAdminFormat()

const data = ref(null)
const error = ref('')
const notice = ref('')
const busy = ref('')
const message = ref('')
const canManage = computed(() => admin.can('settings.manage'))

const SWITCHES = ['registration_open', 'ai_enabled', 'tts_enabled', 'network_posting_enabled']

async function load() {
  try {
    data.value = await admin.act(() => adminApi.settings())
    message.value = data.value.maintenance_message
  } catch (e) {
    error.value = admin.errorText(e, t)
  }
}
onMounted(load)

async function update(patch, key) {
  busy.value = key
  error.value = ''
  notice.value = ''
  try {
    data.value = await admin.act(() => adminApi.updateSettings(patch))
    message.value = data.value.maintenance_message
    notice.value = t('admin.common.saved')
  } catch (e) {
    error.value = admin.errorText(e, t)
  } finally {
    busy.value = ''
  }
}

const settingUp = ref(false)
const me = computed(() => admin.me.value)

const facts = computed(() => {
  const s = data.value?.server || {}
  return [
    { label: t('admin.settings.debug'), value: s.debug, good: !s.debug },
    { label: t('admin.settings.require2fa'), value: s.require_2fa, good: !!s.require_2fa },
    { label: t('admin.settings.aiKey'), value: s.ai_key, good: !!s.ai_key },
    { label: t('admin.settings.sharedCache'), value: s.shared_cache, good: !!s.shared_cache },
  ]
})
</script>

<template>
  <div>
    <AdminHeader :title="$t('admin.settings.title')" />

    <p v-if="error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>
    <p v-if="notice" class="mb-4 rounded-2xl bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-500/10 dark:text-green-300" role="status">{{ notice }}</p>

    <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div class="grid min-w-0 content-start gap-4">
        <AdminCard :title="$t('admin.settings.switches')" :hint="$t('admin.settings.switchesHint')">
          <LoadingSkeleton v-if="!data" height="h-40" />
          <div v-else class="divide-y divide-slate-100 dark:divide-hairline">
            <AdminSwitch
              v-for="key in SWITCHES"
              :key="key"
              :model-value="data[key]"
              :label="$t(`admin.settings.${key}`)"
              :hint="$t(`admin.settings.${key}Hint`)"
              :disabled="!canManage || busy === key"
              @update:model-value="update({ [key]: $event }, key)"
            />
          </div>
          <p v-if="data?.updated_by" class="mt-3 text-xs text-slate-400">{{ data.updated_by }} · {{ fmt.dateTime(data.updated_at) }}</p>
        </AdminCard>

        <AdminCard :title="$t('admin.settings.maintenance')" :hint="$t('admin.settings.maintenanceHint')">
          <form class="space-y-3" @submit.prevent="update({ maintenance_message: message }, 'message')">
            <textarea v-model="message" rows="3" maxlength="300" class="zx-input" :readonly="!canManage" :aria-label="$t('admin.settings.maintenance')" />
            <AnnouncementBanner v-if="message.trim()" :item="{ title: $t('admin.banner.maintenance'), body: message }" maintenance />
            <div v-if="canManage" class="flex justify-end">
              <AppButton size="sm" type="submit" :disabled="busy === 'message' || message === (data?.maintenance_message || '')">{{ $t('admin.common.save') }}</AppButton>
            </div>
          </form>
        </AdminCard>
      </div>

      <div class="grid content-start gap-4">
        <AdminCard :title="$t('admin.settings.myAccount')">
          <template v-if="me?.totp_enabled">
            <p class="flex items-center gap-2 text-sm font-semibold text-green-700 dark:text-green-300">
              <Icon name="shield" class="h-4 w-4" /> {{ $t('admin.unlock.enabled') }}
            </p>
          </template>
          <template v-else-if="settingUp">
            <AdminTotpSetup @done="settingUp = false" @cancel="settingUp = false" />
          </template>
          <template v-else>
            <p class="flex items-center gap-2 text-sm font-semibold text-amber-700 dark:text-amber-300">
              <Icon name="alert" class="h-4 w-4" /> {{ $t('admin.unlock.notEnabled') }}
            </p>
            <p class="mt-1.5 text-xs leading-relaxed text-slate-500">{{ $t('admin.unlock.setupText') }}</p>
            <AppButton size="sm" icon="key" class="mt-3" @click="settingUp = true">{{ $t('admin.unlock.setupStart') }}</AppButton>
          </template>
        </AdminCard>

        <AdminCard :title="$t('admin.settings.server')">
          <LoadingSkeleton v-if="!data" height="h-28" />
          <ul v-else class="space-y-2.5 text-sm">
            <li v-for="fact in facts" :key="fact.label" class="flex items-center justify-between gap-3">
              <span class="text-slate-600 dark:text-slate-300">{{ fact.label }}</span>
              <span
                class="rounded-full px-2.5 py-0.5 text-xs font-semibold"
                :class="fact.good ? 'bg-green-50 text-green-700 dark:bg-green-500/15 dark:text-green-300' : 'bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300'"
              >
                {{ fact.value ? $t('admin.common.yes') : $t('admin.common.no') }}
              </span>
            </li>
            <li class="flex items-center justify-between gap-3">
              <span class="text-slate-600 dark:text-slate-300">{{ $t('admin.settings.database') }}</span>
              <span class="font-mono text-xs text-slate-500">{{ data.server.database }}</span>
            </li>
          </ul>
          <p v-if="data?.server.debug" class="mt-3 text-xs text-amber-700 dark:text-amber-300">{{ $t('admin.settings.debugWarn') }}</p>
        </AdminCard>
      </div>
    </div>
  </div>
</template>
