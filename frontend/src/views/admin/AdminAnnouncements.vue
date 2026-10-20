<script setup>
// Banners at the top of the app: maintenance windows, new lessons, offers.
// Each one can target everyone, newcomers or founders, and run for a window.
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminModal from '@/components/admin/AdminModal.vue'
import AdminSwitch from '@/components/admin/AdminSwitch.vue'
import AnnouncementBanner from '@/components/announcements/AnnouncementBanner.vue'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Icon from '@/components/ui/Icon.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'

const { t } = useI18n()
const admin = useAdmin()
const fmt = useAdminFormat()

const items = ref([])
const loading = ref(true)
const error = ref('')
const canManage = computed(() => admin.can('announcements.manage'))

async function load() {
  loading.value = true
  error.value = ''
  try {
    items.value = (await admin.act(() => adminApi.announcements())).results
  } catch (e) {
    error.value = admin.errorText(e, t)
  } finally {
    loading.value = false
  }
}
onMounted(load)

// <input type="datetime-local"> speaks local time without a zone.
function toLocalInput(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
const fromLocalInput = (value) => (value ? new Date(value).toISOString() : null)

const editor = reactive({ open: false, id: null, busy: false, error: '', form: {} })

function blank() {
  return { title: '', body: '', link_url: '', link_label: '', level: 'info', audience: 'all', starts_at: toLocalInput(new Date().toISOString()), ends_at: '', is_active: true }
}

function openEditor(item = null) {
  editor.id = item?.id || null
  editor.error = ''
  editor.form = item
    ? { ...item, starts_at: toLocalInput(item.starts_at), ends_at: toLocalInput(item.ends_at) }
    : blank()
  editor.open = true
}

async function save() {
  const f = editor.form
  const payload = {
    title: f.title.trim(), body: f.body.trim(), link_url: f.link_url.trim(), link_label: f.link_label.trim(),
    level: f.level, audience: f.audience, starts_at: fromLocalInput(f.starts_at), ends_at: fromLocalInput(f.ends_at), is_active: f.is_active,
  }
  editor.busy = true
  editor.error = ''
  try {
    await admin.act(() => (editor.id ? adminApi.updateAnnouncement(editor.id, payload) : adminApi.createAnnouncement(payload)))
    editor.open = false
    await load()
  } catch (e) {
    editor.error = admin.errorText(e, t)
  } finally {
    editor.busy = false
  }
}

async function toggleActive(item) {
  try {
    Object.assign(item, await admin.act(() => adminApi.updateAnnouncement(item.id, { is_active: !item.is_active })))
  } catch (e) {
    error.value = admin.errorText(e, t)
  }
}

const removing = ref(null)
async function remove() {
  const item = removing.value
  removing.value = null
  try {
    await admin.act(() => adminApi.deleteAnnouncement(item.id))
    await load()
  } catch (e) {
    error.value = admin.errorText(e, t)
  }
}

const LEVELS = ['info', 'success', 'warning']
const AUDIENCES = ['all', 'new', 'founders']
</script>

<template>
  <div>
    <AdminHeader :title="$t('admin.ann.title')" :intro="$t('admin.ann.intro')">
      <AppButton v-if="canManage" size="sm" icon="plus" @click="openEditor()">{{ $t('admin.ann.new') }}</AppButton>
    </AdminHeader>

    <p v-if="error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ error }}</p>

    <div v-if="loading && !items.length" class="space-y-3">
      <LoadingSkeleton v-for="i in 3" :key="i" height="h-28" rounded="rounded-3xl" />
    </div>
    <div v-else-if="!items.length" class="card">
      <EmptyState icon="megaphone" :title="$t('admin.common.empty')" />
    </div>
    <ul v-else class="space-y-3">
      <li v-for="item in items" :key="item.id" class="card p-4 sm:p-5">
        <AnnouncementBanner :item="item" />
        <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <PillBadge :color="item.live ? 'cash' : 'slate'" size="sm">{{ item.live ? $t('admin.ann.live') : $t('admin.ann.notLive') }}</PillBadge>
          <PillBadge size="sm">{{ $t(`admin.ann.audiences.${item.audience}`) }}</PillBadge>
          <span>{{ fmt.dateTime(item.starts_at) }} → {{ item.ends_at ? fmt.dateTime(item.ends_at) : '∞' }}</span>
          <span v-if="item.created_by">· {{ item.created_by }}</span>
          <div v-if="canManage" class="ml-auto flex items-center gap-1">
            <button
              type="button"
              class="rounded-full px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2"
              @click="toggleActive(item)"
            >
              {{ item.is_active ? $t('admin.moderation.hide') : $t('admin.moderation.show') }}
            </button>
            <button
              type="button"
              class="flex h-8 w-8 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 dark:hover:bg-surface-2"
              :aria-label="$t('admin.ann.edit')"
              :title="$t('admin.ann.edit')"
              @click="openEditor(item)"
            >
              <Icon name="pencil" class="h-4 w-4" />
            </button>
            <button
              type="button"
              class="flex h-8 w-8 items-center justify-center rounded-full text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10"
              :aria-label="$t('admin.ann.delete')"
              :title="$t('admin.ann.delete')"
              @click="removing = item"
            >
              <Icon name="trash" class="h-4 w-4" />
            </button>
          </div>
        </div>
      </li>
    </ul>

    <!-- Editor -->
    <AdminModal :open="editor.open" wide :title="editor.id ? $t('admin.ann.edit') : $t('admin.ann.new')" @close="editor.open = false">
      <form class="space-y-4" @submit.prevent="save">
        <label class="block">
          <span class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.ann.headline') }}</span>
          <input v-model="editor.form.title" maxlength="120" required class="zx-input py-2.5" />
        </label>
        <label class="block">
          <span class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.ann.body') }}</span>
          <textarea v-model="editor.form.body" rows="3" maxlength="500" class="zx-input" />
        </label>
        <div class="grid gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <label class="block">
            <span class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.ann.link') }}</span>
            <input v-model="editor.form.link_url" maxlength="300" class="zx-input py-2.5" placeholder="/app/lessons" />
          </label>
          <label class="block">
            <span class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.ann.linkLabel') }}</span>
            <input v-model="editor.form.link_label" maxlength="40" class="zx-input py-2.5" />
          </label>
        </div>
        <div class="grid gap-3 sm:grid-cols-2">
          <label class="block">
            <span class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.ann.level') }}</span>
            <select v-model="editor.form.level" class="zx-input py-2.5">
              <option v-for="level in LEVELS" :key="level" :value="level">{{ $t(`admin.ann.levels.${level}`) }}</option>
            </select>
          </label>
          <label class="block">
            <span class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.ann.audience') }}</span>
            <select v-model="editor.form.audience" class="zx-input py-2.5">
              <option v-for="a in AUDIENCES" :key="a" :value="a">{{ $t(`admin.ann.audiences.${a}`) }}</option>
            </select>
          </label>
          <label class="block">
            <span class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.ann.starts') }}</span>
            <input v-model="editor.form.starts_at" type="datetime-local" required class="zx-input py-2.5" />
          </label>
          <label class="block">
            <span class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.ann.ends') }}</span>
            <input v-model="editor.form.ends_at" type="datetime-local" class="zx-input py-2.5" />
          </label>
        </div>
        <AdminSwitch v-model="editor.form.is_active" :label="$t('admin.ann.active')" />

        <div v-if="editor.form.title">
          <p class="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">{{ $t('admin.ann.preview') }}</p>
          <AnnouncementBanner :item="editor.form" dismissible />
        </div>

        <p v-if="editor.error" class="text-sm text-red-600 dark:text-red-400">{{ editor.error }}</p>
        <div class="flex justify-end gap-2">
          <AppButton variant="ghost" size="sm" type="button" @click="editor.open = false">{{ $t('admin.common.cancel') }}</AppButton>
          <AppButton size="sm" type="submit" :disabled="editor.busy || !editor.form.title?.trim()">
            {{ editor.id ? $t('admin.common.save') : $t('admin.ann.publish') }}
          </AppButton>
        </div>
      </form>
    </AdminModal>

    <!-- Delete -->
    <AdminModal :open="!!removing" :title="$t('admin.ann.delete')" :text="removing?.title" @close="removing = null">
      <div class="flex justify-end gap-2">
        <AppButton variant="ghost" size="sm" @click="removing = null">{{ $t('admin.common.cancel') }}</AppButton>
        <button type="button" class="pill bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700" @click="remove">
          <Icon name="trash" class="h-4 w-4" /> {{ $t('admin.ann.delete') }}
        </button>
      </div>
    </AdminModal>
  </div>
</template>
