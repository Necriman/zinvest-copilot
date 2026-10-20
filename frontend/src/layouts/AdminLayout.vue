<script setup>
/**
 * Admin panel shell: top bar, section nav (only what the role may see), and the
 * gate in front of every page. The gate asks the staff member to confirm it's
 * them on this device (password + two-factor code) before any data loads; the
 * server enforces the same rule, this only makes it pleasant.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import AdminPrompt from '@/components/admin/AdminPrompt.vue'
import AdminRoleBadge from '@/components/admin/AdminRoleBadge.vue'
import AdminUnlockForm from '@/components/admin/AdminUnlockForm.vue'
import BrandMark from '@/components/ui/BrandMark.vue'
import Icon from '@/components/ui/Icon.vue'
import LanguageSwitcher from '@/components/ui/LanguageSwitcher.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import ThemeToggle from '@/components/ui/ThemeToggle.vue'
import { adminApi } from '@/api/admin'
import { useAdmin } from '@/composables/useAdmin'
import { useAdminFormat } from '@/composables/useAdminFormat'
import { flushPendingScroll } from '@/router/navScroll'

const route = useRoute()
const admin = useAdmin()
const fmt = useAdminFormat()

const NAV = [
  { name: 'adminOverview', icon: 'chart', label: 'overview', perm: 'overview.view' },
  { name: 'adminUsers', icon: 'users', label: 'users', perm: 'users.view' },
  { name: 'adminStartups', icon: 'store', label: 'startups', perm: 'startups.view' },
  { name: 'adminContent', icon: 'book', label: 'content', perm: 'content.view' },
  { name: 'adminModeration', icon: 'flag', label: 'moderation', perm: 'moderation.view' },
  { name: 'adminAI', icon: 'bot', label: 'ai', perm: 'ai.view' },
  { name: 'adminAnnouncements', icon: 'megaphone', label: 'announcements', perm: 'announcements.view' },
  { name: 'adminTeam', icon: 'key', label: 'team', perm: 'users.view' },
  { name: 'adminSecurity', icon: 'shield', label: 'security', perm: 'security.view' },
  { name: 'adminSystem', icon: 'settings', label: 'system', perm: 'system.view' },
  { name: 'adminAudit', icon: 'history', label: 'audit', perm: 'audit.view' },
  { name: 'adminSettings', icon: 'settings', label: 'settings', perm: 'settings.view' },
]

const me = computed(() => admin.state.me)
const items = computed(() => NAV.filter((item) => admin.can(item.perm)))
const allowed = computed(() => !route.meta.perm || admin.can(route.meta.perm))

// Drawer below lg; the rail is docked from lg up.
const drawer = ref(false)
watch(() => route.fullPath, () => (drawer.value = false))

function onKey(e) {
  if (e.key === 'Escape') drawer.value = false
}

onMounted(() => {
  document.addEventListener('keydown', onKey)
  admin.load()
})
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))

const locking = ref(false)
async function lock() {
  locking.value = true
  try {
    admin.setMe(await adminApi.lock())
  } catch {
    await admin.load()
  } finally {
    locking.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-canvas text-slate-900 dark:text-ink">
    <header class="fixed inset-x-0 top-0 z-50 h-16 border-b border-slate-200 bg-surface/95 backdrop-blur dark:border-hairline">
      <div class="flex h-full items-center justify-between gap-2 px-3 sm:px-6">
        <div class="flex min-w-0 items-center gap-1.5 sm:gap-2">
          <button
            v-if="me?.unlocked"
            type="button"
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 lg:hidden dark:text-slate-300 dark:hover:bg-surface-2"
            :aria-label="$t('admin.nav.sections')"
            :aria-expanded="drawer"
            @click="drawer = !drawer"
          >
            <Icon :name="drawer ? 'x' : 'menu'" class="h-5 w-5" />
          </button>
          <RouterLink :to="{ name: 'adminOverview' }" class="flex min-w-0 items-center gap-2">
            <BrandMark class="h-8 w-8 shrink-0 rounded-lg" />
            <span class="hidden text-lg font-extrabold tracking-tight text-slate-900 min-[420px]:inline dark:text-white">
              {{ $t('common.appName') }}
            </span>
            <span class="whitespace-nowrap rounded-md bg-slate-900 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white dark:bg-white dark:text-slate-900">
              {{ $t('admin.nav.title') }}
            </span>
          </RouterLink>
        </div>

        <div class="flex items-center gap-1 sm:gap-1.5">
          <AdminRoleBadge :role="me?.role" class="hidden md:inline-flex" />
          <ThemeToggle />
          <LanguageSwitcher />
          <button
            v-if="me?.unlocked"
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 disabled:opacity-50 dark:text-slate-300 dark:hover:bg-surface-2"
            :title="$t('admin.nav.lock')"
            :aria-label="$t('admin.nav.lock')"
            :disabled="locking"
            @click="lock"
          >
            <Icon name="lock" class="h-[18px] w-[18px]" />
          </button>
          <RouterLink
            :to="{ name: 'dashboard' }"
            class="flex h-9 items-center gap-1.5 rounded-full border border-slate-200 px-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 sm:px-3.5 dark:border-hairline dark:text-slate-300 dark:hover:bg-surface-2"
            :title="$t('admin.nav.backToApp')"
          >
            <Icon name="arrowLeft" class="h-4 w-4" />
            <span class="hidden sm:inline">{{ $t('admin.nav.backToApp') }}</span>
          </RouterLink>
        </div>
      </div>
    </header>

    <template v-if="me?.unlocked">
      <Transition name="fade">
        <div v-if="drawer" class="fixed inset-0 top-16 z-40 bg-slate-900/50 backdrop-blur-sm lg:hidden" @click="drawer = false" />
      </Transition>

      <aside
        class="fixed bottom-0 left-0 top-16 z-40 flex w-60 flex-col border-r border-slate-200 bg-surface transition-transform duration-300 ease-out lg:translate-x-0 dark:border-hairline"
        :class="drawer ? 'translate-x-0' : '-translate-x-full'"
        :aria-label="$t('admin.nav.sections')"
      >
        <nav class="flex-1 overflow-y-auto px-3 py-5">
          <RouterLink
            v-for="item in items"
            :key="item.name"
            :to="{ name: item.name }"
            class="group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2"
            active-class="!bg-brand-50 !text-brand-700 dark:!bg-brand-500/15 dark:!text-brand-300"
          >
            <Icon :name="item.icon" class="h-5 w-5 shrink-0" />
            <span class="truncate">{{ $t(`admin.nav.${item.label}`) }}</span>
          </RouterLink>
        </nav>
        <div class="border-t border-slate-200 px-5 py-4 text-xs text-slate-400 dark:border-hairline">
          <p class="truncate font-semibold text-slate-600 dark:text-slate-300">{{ me.email }}</p>
          <p v-if="me.session_until" class="mt-0.5">{{ $t('admin.unlock.sessionUntil', { time: fmt.dateTime(me.session_until) }) }}</p>
        </div>
      </aside>
    </template>

    <main id="main" tabindex="-1" class="pt-16" :class="me?.unlocked ? 'lg:pl-60' : ''">
      <div class="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <!-- Who am I on the team? -->
        <div v-if="!me && admin.state.loading" class="space-y-4">
          <LoadingSkeleton width="w-48" height="h-8" />
          <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <LoadingSkeleton v-for="i in 4" :key="i" height="h-28" rounded="rounded-3xl" />
          </div>
        </div>

        <!-- Not on the team (the router normally stops this earlier). -->
        <div v-else-if="!me" class="card mx-auto mt-10 max-w-md p-8 text-center">
          <span class="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400 dark:bg-surface-2">
            <Icon name="lock" class="h-6 w-6" />
          </span>
          <p class="mt-4 font-semibold text-slate-700 dark:text-slate-200">
            {{ admin.state.error === 'forbidden' ? $t('admin.unlock.noAccess') : $t('admin.common.error') }}
          </p>
          <button
            v-if="admin.state.error !== 'forbidden'"
            type="button"
            class="mt-4 text-sm font-semibold text-brand-600 hover:underline dark:text-brand-300"
            @click="admin.load()"
          >
            {{ $t('admin.common.refresh') }}
          </button>
        </div>

        <!-- Confirm it's you on this device. -->
        <div v-else-if="!me.unlocked" class="card mx-auto mt-4 max-w-md p-6 sm:mt-10 sm:p-8">
          <span class="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
            <Icon name="shield" class="h-6 w-6" />
          </span>
          <h1 class="mt-4 text-xl font-extrabold tracking-tight text-slate-900 dark:text-white">{{ $t('admin.unlock.title') }}</h1>
          <p class="mt-1.5 text-sm leading-relaxed text-slate-500 dark:text-slate-400">{{ me.has_password === false ? $t('admin.unlock.textGoogle') : $t('admin.unlock.text') }}</p>
          <div class="mt-6">
            <AdminUnlockForm :cancellable="false" />
          </div>
        </div>

        <div v-else-if="!allowed" class="card mx-auto mt-10 max-w-md p-8 text-center">
          <p class="font-semibold text-slate-700 dark:text-slate-200">{{ $t('admin.common.forbidden') }}</p>
        </div>

        <router-view v-else v-slot="{ Component }">
          <Transition name="fade-slide" mode="out-in" @before-enter="flushPendingScroll">
            <component :is="Component" :key="route.path" />
          </Transition>
        </router-view>
      </div>
    </main>

    <AdminPrompt />
  </div>
</template>
