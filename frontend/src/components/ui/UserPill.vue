<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import Avatar from './Avatar.vue'
import Icon from './Icon.vue'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const router = useRouter()
const root = ref(null)
const open = ref(false)

const displayName = computed(
  () => auth.user?.first_name || auth.user?.email?.split('@')[0] || 'You',
)

async function onLogout() {
  open.value = false
  await auth.logout()
  router.push({ name: 'login' })
}

// Outside-click / Escape dismiss (document listener — the navbar's backdrop-filter
// would otherwise confine a `fixed inset-0` overlay to the navbar box).
function onDoc(e) {
  if (open.value && root.value && !root.value.contains(e.target)) open.value = false
}
function onKey(e) {
  if (e.key === 'Escape') open.value = false
}
onMounted(() => {
  document.addEventListener('mousedown', onDoc)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDoc)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div ref="root" class="relative">
    <!-- h-9 matches the sign-up button this swaps places with in the landing
         navbar; the 1px border otherwise made the bar 2px taller once you
         signed in. -->
    <button
      type="button"
      class="flex h-9 items-center gap-2 rounded-full border border-slate-200 bg-white p-1 pr-1 text-sm font-medium text-slate-700 hover:bg-slate-50 min-[400px]:pl-1 min-[400px]:pr-3 dark:border-hairline dark:bg-surface dark:text-slate-200 dark:hover:bg-surface-2"
      @click="open = !open"
    >
      <Avatar :name="displayName" :src="auth.user?.avatar_url || ''" size="h-7 w-7 text-xs" />
      <!-- Name drops on the tightest widths so the pill stays a compact avatar
           next to the theme / language / menu controls. -->
      <span class="hidden max-w-[90px] truncate min-[400px]:block">{{ displayName }}</span>
      <Icon name="chevronDown" class="hidden h-3.5 w-3.5 text-slate-400 min-[400px]:block" />
    </button>

    <Transition name="pop">
      <div
        v-if="open"
        class="absolute right-0 z-20 mt-2 w-48 origin-top-right overflow-hidden rounded-2xl border border-slate-200 bg-white py-1 shadow-float dark:border-hairline dark:bg-surface"
      >
        <RouterLink
          :to="{ name: 'dashboard' }"
          class="flex items-center gap-2 px-4 py-2 text-sm text-slate-700 transition-colors duration-200 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-surface-2"
          @click="open = false"
        >
          <Icon name="home" class="h-4 w-4" /> {{ $t('nav.dashboard') }}
        </RouterLink>
        <RouterLink
          :to="{ name: 'settings' }"
          class="flex items-center gap-2 px-4 py-2 text-sm text-slate-700 transition-colors duration-200 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-surface-2"
          @click="open = false"
        >
          <Icon name="settings" class="h-4 w-4" /> {{ $t('nav.settings') }}
        </RouterLink>
        <!-- Team only; the panel itself asks for a password and a 2FA code. -->
        <RouterLink
          v-if="auth.user?.staff_role"
          :to="{ name: 'adminOverview' }"
          class="flex items-center gap-2 px-4 py-2 text-sm text-slate-700 transition-colors duration-200 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-surface-2"
          @click="open = false"
        >
          <Icon name="shield" class="h-4 w-4" /> {{ $t('admin.nav.open') }}
        </RouterLink>
        <button
          type="button"
          class="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-600 transition-colors duration-200 hover:bg-red-50 dark:hover:bg-red-500/10"
          @click="onLogout"
        >
          <Icon name="logout" class="h-4 w-4" /> {{ $t('nav.logout') }}
        </button>
      </div>
    </Transition>
  </div>
</template>
