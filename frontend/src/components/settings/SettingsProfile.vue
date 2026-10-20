<script setup>
/**
 * Profile — picture and name.
 *
 * The picture is STAGED: choosing (or clearing) one only swaps the local
 * preview, and nothing is sent until Save. That keeps one Save button
 * responsible for everything on the card, and makes the choice discardable.
 */
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'

import Avatar from '@/components/ui/Avatar.vue'
import Icon from '@/components/ui/Icon.vue'
import { removeAvatar, updateProfile, uploadAvatar } from '@/api/account'
import { useTask } from '@/composables/useTask'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const { state, run } = useTask()

const form = reactive({ first_name: '', last_name: '' })
const fileInput = ref(null)
// null = untouched · {file,url} = new picture chosen · {remove:true} = clearing
const pending = ref(null)

function resetForm() {
  form.first_name = auth.user?.first_name || ''
  form.last_name = auth.user?.last_name || ''
}
watch(() => auth.user, resetForm, { immediate: true, deep: true })

function releasePreview() {
  if (pending.value?.url) URL.revokeObjectURL(pending.value.url)
}
onBeforeUnmount(releasePreview)

const savedAvatar = computed(() => auth.user?.avatar_url || '')
const previewSrc = computed(() => {
  if (pending.value?.remove) return ''
  return pending.value?.url || savedAvatar.value
})
const displayName = computed(
  () => `${form.first_name} ${form.last_name}`.trim() || auth.user?.email || 'You',
)

const dirty = computed(
  () =>
    !!pending.value ||
    form.first_name !== (auth.user?.first_name || '') ||
    form.last_name !== (auth.user?.last_name || ''),
)

function choose(event) {
  const file = event.target.files?.[0]
  event.target.value = '' // let the same file be re-picked after a discard
  if (!file) return
  releasePreview()
  pending.value = { file, url: URL.createObjectURL(file) }
}

function clearPicture() {
  releasePreview()
  pending.value = savedAvatar.value ? { remove: true } : null
}

function discard() {
  releasePreview()
  pending.value = null
  resetForm()
}

function save() {
  run(async () => {
    // Picture first: if it fails we don't want a half-applied card.
    if (pending.value?.file) auth.setUser(await uploadAvatar(pending.value.file))
    else if (pending.value?.remove) auth.setUser(await removeAvatar())
    releasePreview()
    pending.value = null
    auth.setUser(await updateProfile({ ...form }))
  })
}
</script>

<template>
  <div>
    <h2 class="text-base font-bold text-slate-900 dark:text-white">{{ $t('settings.profile') }}</h2>
    <p class="mt-1 text-sm text-slate-500">{{ $t('settings.profileHint') }}</p>

    <div class="mt-6 flex flex-wrap items-center gap-5">
      <div class="relative">
        <Avatar :name="displayName" :src="previewSrc" size="h-20 w-20 text-2xl" />
        <span
          v-if="pending"
          class="absolute -bottom-1 -right-1 rounded-full bg-amber-500 px-2 py-0.5 text-[10px] font-bold text-white"
        >
          {{ $t('settings.pendingBadge') }}
        </span>
      </div>

      <div>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="flex items-center gap-1.5 rounded-xl bg-brand-600 px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
            @click="fileInput?.click()"
          >
            <Icon name="upload" class="h-3.5 w-3.5" />
            {{ $t(previewSrc ? 'settings.changePicture' : 'settings.uploadPicture') }}
          </button>
          <button
            v-if="previewSrc"
            type="button"
            class="rounded-xl border border-slate-200 px-3.5 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 dark:border-hairline dark:text-slate-300 dark:hover:bg-surface-2"
            @click="clearPicture"
          >
            {{ $t('common.delete') }}
          </button>
        </div>
        <p class="mt-2 text-xs text-slate-400">{{ $t('settings.pictureHint') }}</p>
      </div>
      <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="choose" />
    </div>

    <form class="mt-6 grid gap-4 sm:grid-cols-2" @submit.prevent="save">
      <label class="block">
        <span class="mb-1.5 block text-xs font-semibold text-slate-500">{{ $t('settings.firstName') }}</span>
        <input v-model="form.first_name" type="text" maxlength="150" class="zx-input" />
      </label>
      <label class="block">
        <span class="mb-1.5 block text-xs font-semibold text-slate-500">{{ $t('settings.lastName') }}</span>
        <input v-model="form.last_name" type="text" maxlength="150" class="zx-input" />
      </label>

      <div class="flex flex-wrap items-center gap-3 sm:col-span-2">
        <button
          type="submit"
          :disabled="state.busy || !dirty"
          class="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
        >
          {{ state.busy ? $t('settings.saving') : $t('common.save') }}
        </button>
        <button
          v-if="dirty && !state.busy"
          type="button"
          class="rounded-xl px-3 py-2 text-sm font-medium text-slate-500 transition hover:bg-slate-100 dark:hover:bg-surface-2"
          @click="discard"
        >
          {{ $t('settings.discard') }}
        </button>
        <span v-if="state.saved" class="text-sm text-green-600 dark:text-green-400">{{ $t('settings.saved') }}</span>
        <span v-if="state.error" class="text-sm text-red-500">{{ state.error }}</span>
      </div>
    </form>
  </div>
</template>
