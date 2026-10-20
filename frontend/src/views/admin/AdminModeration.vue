<script setup>
// Reports from learners and the founder network's posts. A report shows what
// was flagged as it looked at the time (a snapshot), so edits cannot hide it.
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminModal from '@/components/admin/AdminModal.vue'
import AdminPager from '@/components/admin/AdminPager.vue'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import PillBadge from '@/components/ui/PillBadge.vue'
import SearchField from '@/components/ui/SearchField.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'

const { t, te } = useI18n()
const admin = useAdmin()
const fmt = useAdminFormat()

const tab = ref('reports') // reports | posts
const canManage = computed(() => admin.can('moderation.manage'))

// ---- Reports -----------------------------------------------------------------
const status = ref('open')
const reports = reactive({ rows: [], page: 1, pages: 1, total: 0, loading: false, error: '' })
const notes = reactive({})
const acting = ref('')

async function loadReports() {
  reports.loading = true
  reports.error = ''
  try {
    const data = await admin.act(() => adminApi.reports({ status: status.value, page: reports.page }))
    Object.assign(reports, { rows: data.results, pages: data.pages, total: data.total, page: data.page })
  } catch (e) {
    reports.error = admin.errorText(e, t)
  } finally {
    reports.loading = false
  }
}

async function resolve(report, nextStatus, action = 'none') {
  acting.value = report.id
  reports.error = ''
  try {
    await admin.act(() => adminApi.resolveReport(report.id, { status: nextStatus, action, note: notes[report.id] || '' }))
    await loadReports()
  } catch (e) {
    reports.error = admin.errorText(e, t)
  } finally {
    acting.value = ''
  }
}

const reasonLabel = (r) => (te(`admin.report.reasons.${r.reason}`) ? t(`admin.report.reasons.${r.reason}`) : r.reason_label)

// ---- Posts -------------------------------------------------------------------
const onlyHidden = ref(false)
const q = ref('')
const posts = reactive({ rows: [], page: 1, pages: 1, total: 0, loading: false, error: '' })
const hiding = reactive({ post: null, reason: '', busy: false, error: '' })

async function loadPosts() {
  posts.loading = true
  posts.error = ''
  try {
    const data = await admin.act(() => adminApi.posts({ hidden: onlyHidden.value ? 1 : undefined, q: q.value || undefined, page: posts.page }))
    Object.assign(posts, { rows: data.results, pages: data.pages, total: data.total, page: data.page })
  } catch (e) {
    posts.error = admin.errorText(e, t)
  } finally {
    posts.loading = false
  }
}

async function setHidden(post, hidden, reason = '') {
  hiding.busy = true
  hiding.error = ''
  try {
    const fresh = await admin.act(() => adminApi.setPostHidden(post.id, hidden, reason))
    Object.assign(post, fresh)
    hiding.post = null
  } catch (e) {
    if (hiding.post) hiding.error = admin.errorText(e, t)
    else posts.error = admin.errorText(e, t)
  } finally {
    hiding.busy = false
  }
}

function askHide(post) {
  Object.assign(hiding, { post, reason: '', error: '' })
}

// A filter change goes back to page 1; the page watcher loads when the page moved.
watch(status, () => {
  if (reports.page !== 1) reports.page = 1
  else loadReports()
})
watch(() => reports.page, (value, old) => value !== old && loadReports())
watch([onlyHidden, q], () => {
  if (posts.page !== 1) posts.page = 1
  else loadPosts()
})
watch(() => posts.page, (value, old) => value !== old && loadPosts())
watch(
  tab,
  (value) => {
    if (value === 'reports' && !reports.rows.length) loadReports()
    if (value === 'posts' && !posts.rows.length) loadPosts()
  },
  { immediate: true },
)

const TAB = 'rounded-lg px-3.5 py-1.5 text-sm font-semibold transition'
const TAB_ON = 'bg-white text-slate-900 shadow-sm dark:bg-surface dark:text-white'
const TAB_OFF = 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200'
</script>

<template>
  <div>
    <AdminHeader :title="$t('admin.moderation.title')">
      <div class="inline-flex rounded-xl bg-slate-100 p-1 dark:bg-surface-2" role="tablist">
        <button type="button" role="tab" :aria-selected="tab === 'reports'" :class="[TAB, tab === 'reports' ? TAB_ON : TAB_OFF]" @click="tab = 'reports'">
          {{ $t('admin.moderation.reports') }}
        </button>
        <button type="button" role="tab" :aria-selected="tab === 'posts'" :class="[TAB, tab === 'posts' ? TAB_ON : TAB_OFF]" @click="tab = 'posts'">
          {{ $t('admin.moderation.posts') }}
        </button>
      </div>
    </AdminHeader>

    <!-- Reports -->
    <section v-if="tab === 'reports'">
      <div class="mb-4 flex flex-wrap gap-2">
        <button
          v-for="s in ['open', 'resolved', 'dismissed']"
          :key="s"
          type="button"
          class="rounded-full border px-3.5 py-1.5 text-sm font-semibold transition"
          :class="status === s ? 'border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300' : 'border-slate-200 text-slate-500 hover:bg-slate-50 dark:border-hairline dark:hover:bg-surface-2'"
          @click="status = s"
        >
          {{ $t(`admin.moderation.${s}`) }}
        </button>
      </div>

      <p v-if="reports.error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ reports.error }}</p>

      <div v-if="reports.loading && !reports.rows.length" class="space-y-3">
        <LoadingSkeleton v-for="i in 3" :key="i" height="h-36" rounded="rounded-3xl" />
      </div>
      <div v-else-if="!reports.rows.length" class="card">
        <EmptyState icon="flag" :title="$t('admin.common.empty')" />
      </div>
      <ul v-else class="space-y-3" :class="reports.loading ? 'opacity-60' : ''">
        <li v-for="r in reports.rows" :key="r.id" class="card p-4 sm:p-5">
          <div class="flex flex-wrap items-center gap-2">
            <PillBadge color="risk" size="sm">{{ $t(`admin.moderation.target.${r.target_type}`) }}</PillBadge>
            <PillBadge color="amber" size="sm">{{ reasonLabel(r) }}</PillBadge>
            <span v-if="r.same_target > 1" class="text-xs font-semibold text-red-600 dark:text-red-400">{{ $t('admin.moderation.times', { n: r.same_target }) }}</span>
            <span class="ml-auto text-xs text-slate-400">{{ fmt.dateTime(r.created_at) }}</span>
          </div>

          <!-- What was reported, as it looked then -->
          <blockquote class="mt-3 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700 dark:bg-surface-2/60 dark:text-slate-200">
            <p v-if="r.snapshot.title || r.snapshot.company" class="font-semibold">{{ r.snapshot.title || r.snapshot.company }}</p>
            <p class="whitespace-pre-line break-words">{{ r.snapshot.text || r.snapshot.summary }}</p>
          </blockquote>
          <p v-if="r.comment" class="mt-2 text-sm italic text-slate-500">“{{ r.comment }}”</p>

          <div class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
            <span v-if="r.reporter">{{ $t('admin.moderation.from', { email: r.reporter.email }) }}</span>
            <span v-if="r.target_user">
              <RouterLink v-if="admin.can('users.view')" :to="{ name: 'adminUser', params: { id: r.target_user.id } }" class="font-semibold text-brand-600 hover:underline dark:text-brand-300">
                {{ $t('admin.moderation.about', { email: r.target_user.email }) }}
              </RouterLink>
              <template v-else>{{ $t('admin.moderation.about', { email: r.target_user.email }) }}</template>
              <template v-if="!r.target_user.is_active"> · {{ $t('admin.common.disabled') }}</template>
            </span>
          </div>

          <!-- Decide -->
          <div v-if="r.status === 'open' && canManage" class="mt-4 border-t border-slate-100 pt-4 dark:border-hairline">
            <input v-model="notes[r.id]" maxlength="500" class="zx-input" :placeholder="$t('admin.moderation.note')" :aria-label="$t('admin.moderation.note')" />
            <div class="mt-3 flex flex-wrap gap-2">
              <AppButton size="sm" variant="outline" :disabled="acting === r.id" @click="resolve(r, 'dismissed')">{{ $t('admin.moderation.dismiss') }}</AppButton>
              <AppButton size="sm" variant="outline" icon="check" :disabled="acting === r.id" @click="resolve(r, 'resolved')">{{ $t('admin.moderation.resolve') }}</AppButton>
              <AppButton v-if="r.target_type === 'post'" size="sm" icon="eyeOff" :disabled="acting === r.id" @click="resolve(r, 'resolved', 'hide_post')">
                {{ $t('admin.moderation.hidePost') }}
              </AppButton>
              <button
                v-if="r.target_user?.is_active"
                type="button"
                class="pill bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-50"
                :disabled="acting === r.id"
                @click="resolve(r, 'resolved', 'disable_user')"
              >
                {{ $t('admin.moderation.disableUser') }}
              </button>
            </div>
          </div>
          <p v-else-if="r.status !== 'open'" class="mt-3 text-xs text-slate-500">
            {{ $t('admin.moderation.handledBy', { status: $t(`admin.moderation.${r.status}`), email: r.resolved_by || '—' }) }} · {{ fmt.dateTime(r.resolved_at) }}
            <template v-if="r.resolution"> — {{ r.resolution }}</template>
          </p>
        </li>
      </ul>
      <AdminPager v-model:page="reports.page" :pages="reports.pages" :total="reports.total" class="mt-4" />
    </section>

    <!-- Posts -->
    <section v-else>
      <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <SearchField v-model="q" :placeholder="$t('admin.common.search')" class="sm:max-w-xs sm:flex-1" />
        <label class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <input v-model="onlyHidden" type="checkbox" class="h-4 w-4 rounded accent-brand-600" />
          {{ $t('admin.moderation.onlyHidden') }}
        </label>
      </div>

      <p v-if="posts.error" class="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{{ posts.error }}</p>

      <div v-if="posts.loading && !posts.rows.length" class="space-y-3">
        <LoadingSkeleton v-for="i in 3" :key="i" height="h-28" rounded="rounded-3xl" />
      </div>
      <div v-else-if="!posts.rows.length" class="card">
        <EmptyState icon="note" :title="$t('admin.common.empty')" />
      </div>
      <ul v-else class="grid gap-3 md:grid-cols-2" :class="posts.loading ? 'opacity-60' : ''">
        <li v-for="p in posts.rows" :key="p.id" class="card flex flex-col p-4" :class="p.hidden ? 'border-dashed opacity-80' : ''">
          <div class="flex items-start gap-3">
            <img v-if="p.image_url" :src="p.image_url" alt="" class="h-14 w-14 shrink-0 rounded-xl object-cover" loading="lazy" />
            <div class="min-w-0 flex-1">
              <p class="font-semibold text-slate-800 dark:text-slate-100">{{ p.title }}</p>
              <p class="truncate text-xs text-slate-400">{{ p.company || p.author?.name }} · {{ p.author?.email }} · {{ fmt.ago(p.created_at) }}</p>
            </div>
          </div>
          <p class="mt-2 line-clamp-4 whitespace-pre-line break-words text-sm text-slate-600 dark:text-slate-300">{{ p.text }}</p>
          <div class="mt-auto flex flex-wrap items-center gap-2 pt-3">
            <PillBadge v-if="p.hidden" color="slate" size="sm" icon="eyeOff">{{ $t('admin.moderation.hidden') }}</PillBadge>
            <PillBadge v-if="p.reports" color="amber" size="sm" icon="flag">{{ p.reports }}</PillBadge>
            <span v-if="p.hidden && p.hidden_reason" class="min-w-0 truncate text-xs text-slate-400">{{ p.hidden_reason }}</span>
            <template v-if="canManage">
              <AppButton v-if="p.hidden" class="ml-auto" size="sm" variant="outline" icon="eye" :disabled="hiding.busy" @click="setHidden(p, false)">
                {{ $t('admin.moderation.show') }}
              </AppButton>
              <AppButton v-else class="ml-auto" size="sm" variant="outline" icon="eyeOff" @click="askHide(p)">{{ $t('admin.moderation.hide') }}</AppButton>
            </template>
          </div>
        </li>
      </ul>
      <AdminPager v-model:page="posts.page" :pages="posts.pages" :total="posts.total" class="mt-4" />
    </section>

    <AdminModal :open="!!hiding.post" :title="$t('admin.moderation.hidePost')" :text="hiding.post?.title" @close="hiding.post = null">
      <form class="space-y-4" @submit.prevent="setHidden(hiding.post, true, hiding.reason.trim())">
        <input v-model="hiding.reason" maxlength="300" class="zx-input py-2.5" :placeholder="$t('admin.moderation.hideReason')" :aria-label="$t('admin.moderation.hideReason')" />
        <p v-if="hiding.error" class="text-sm text-red-600 dark:text-red-400">{{ hiding.error }}</p>
        <div class="flex justify-end gap-2">
          <AppButton variant="ghost" size="sm" type="button" @click="hiding.post = null">{{ $t('admin.common.cancel') }}</AppButton>
          <AppButton size="sm" type="submit" icon="eyeOff" :disabled="hiding.busy || !hiding.reason.trim()">{{ $t('admin.moderation.hide') }}</AppButton>
        </div>
      </form>
    </AdminModal>
  </div>
</template>
