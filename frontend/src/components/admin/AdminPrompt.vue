<script setup>
// The confirmation useAdmin().act() asks for when the server wants a fresh
// "it's me" before a change. Mounted once, in the admin layout.
import { computed } from 'vue'

import AdminModal from '@/components/admin/AdminModal.vue'
import AdminUnlockForm from '@/components/admin/AdminUnlockForm.vue'
import { useAdmin } from '@/composables/useAdmin'

const admin = useAdmin()
const prompt = computed(() => admin.state.prompt)
</script>

<template>
  <AdminModal
    :open="!!prompt"
    persistent
    :title="$t(prompt?.reason === 'sudo' ? 'admin.unlock.sudoTitle' : 'admin.unlock.title')"
    :text="
      prompt?.reason === 'sudo'
        ? $t('admin.unlock.sudoText', { n: admin.me.value?.sudo_minutes || 30 })
        : $t('admin.unlock.text')
    "
    @close="admin.closePrompt(false)"
  >
    <AdminUnlockForm
      v-if="prompt"
      :key="prompt.reason"
      :mode="prompt.reason"
      @done="admin.closePrompt(true)"
      @cancel="admin.closePrompt(false)"
    />
  </AdminModal>
</template>
