<script setup>
import Icon from './Icon.vue'
import { updateProfile } from '@/api/account'
import { useTheme } from '@/composables/useTheme'
import { useAuthStore } from '@/store/auth'

// The icon reflects what's on screen, which may come from the OS under "system".
const auth = useAuthStore()
const { resolvedTheme, toggle } = useTheme()

async function onToggle() {
  const next = toggle()
  // Mirror onto the account, exactly as the Settings panel does. Without this
  // the choice applies locally and is then quietly undone on the next load,
  // when /me hands back the theme the account still remembers. Signed out (the
  // auth pages carry this toggle too) there is nothing to mirror it onto.
  if (!auth.isAuthenticated) return
  try {
    auth.setUser(await updateProfile({ theme: next }))
  } catch {
    // The local preference already applies; a failed sync just means this
    // device keeps it and the account doesn't learn about it.
  }
}
</script>

<template>
  <button
    type="button"
    :title="$t(resolvedTheme === 'dark' ? 'common.lightMode' : 'common.darkMode')"
    class="inline-flex h-9 w-9 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-surface-2 dark:hover:text-white"
    @click="onToggle"
  >
    <Icon :name="resolvedTheme === 'dark' ? 'sun' : 'moon'" class="h-[18px] w-[18px]" />
  </button>
</template>
