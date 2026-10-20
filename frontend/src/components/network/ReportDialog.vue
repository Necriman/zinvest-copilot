<script setup>
// "Report" for the founder network: a post, a founder's profile or a message.
// The team sees it in Admin → Moderation with a snapshot of what was reported.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AdminModal from '@/components/admin/AdminModal.vue'
import AppButton from '@/components/ui/AppButton.vue'
import CheckBox from '@/components/ui/CheckBox.vue'
import { sendReport } from '@/api/platform'

const props = defineProps({
  target: { type: Object, default: null }, // { type: 'post' | 'user' | 'message', id }
})
const emit = defineEmits(['close'])

const { t } = useI18n()
const REASONS = ['spam', 'abuse', 'fraud', 'inappropriate', 'other']

const reason = ref('')
const comment = ref('')
const busy = ref(false)
const error = ref('')
const sent = ref(false)

watch(
  () => props.target,
  (target) => {
    if (!target) return
    reason.value = ''
    comment.value = ''
    error.value = ''
    sent.value = false
  },
)

async function submit() {
  if (!reason.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await sendReport({ target_type: props.target.type, target_id: props.target.id, reason: reason.value, comment: comment.value.trim() })
    sent.value = true
  } catch (e) {
    error.value = e?.response?.data?.detail || t('admin.common.error')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AdminModal :open="!!target" :title="sent ? $t('admin.report.action') : $t('admin.report.title')" @close="emit('close')">
    <div v-if="sent" class="space-y-4">
      <p class="text-sm text-slate-600 dark:text-slate-300" role="status">{{ $t('admin.report.thanks') }}</p>
      <div class="flex justify-end">
        <AppButton size="sm" @click="emit('close')">{{ $t('admin.common.close') }}</AppButton>
      </div>
    </div>
    <form v-else class="space-y-4" @submit.prevent="submit">
      <div class="grid gap-2" role="radiogroup" :aria-label="$t('admin.report.title')">
        <CheckBox v-for="r in REASONS" :key="r" v-model="reason" type="radio" :value="r">{{ $t(`admin.report.reasons.${r}`) }}</CheckBox>
      </div>
      <textarea v-model="comment" rows="3" maxlength="1000" class="zx-input" :placeholder="$t('admin.report.comment')" :aria-label="$t('admin.report.comment')" />
      <p v-if="error" class="text-sm text-red-600 dark:text-red-400" role="alert">{{ error }}</p>
      <div class="flex justify-end gap-2">
        <AppButton variant="ghost" size="sm" type="button" @click="emit('close')">{{ $t('admin.common.cancel') }}</AppButton>
        <AppButton size="sm" type="submit" icon="flag" :disabled="busy || !reason">{{ $t('admin.report.send') }}</AppButton>
      </div>
    </form>
  </AdminModal>
</template>
