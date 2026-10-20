<script setup>
// Application shell: a fixed top bar spanning the viewport, a left rail that
// docks (full or mini) on wide screens and slides in as a drawer on narrow
// ones, an optional right rail, and a fluid main column that clears them.
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import AnnouncementBar from '@/components/announcements/AnnouncementBar.vue'
import VerifyEmailNotice from '@/components/announcements/VerifyEmailNotice.vue'
import DashboardTopBar from '@/components/nav/DashboardTopBar.vue'
import Sidebar from '@/components/nav/Sidebar.vue'
import RightRail from '@/components/dashboard/RightRail.vue'
import { useSidebar } from '@/composables/useSidebar'
import { flushPendingScroll, takeReturn } from '@/router/navScroll'

const route = useRoute()
const { locale } = useI18n()
const { docked, drawerOpen, mini, width, closeDrawer } = useSidebar()

// A page opts out of the right rail with `meta: { rightRail: false }` (see the
// startup route). The main column's right padding drops with it so the content
// reclaims the full width.
const showRightRail = computed(() => route.meta.rightRail !== false)

// Returning from a lesson: put the page back on the offset it was left at.
//
// The router can't do this itself. The top-level transition is out-in, so when
// scrollBehavior runs the lesson is still the only thing on screen and one
// screen tall — a scroll there clamps straight to zero. By the time this shell
// mounts the destination is rendered (from its cached payload, so at full
// height), which is the first moment the offset is actually reachable.
onMounted(() => {
  const back = takeReturn(route.fullPath)
  if (back) window.scrollTo(0, back.top)
})
</script>

<template>
  <div class="min-h-screen bg-canvas text-slate-900 print:bg-white dark:bg-canvas dark:text-ink">
    <!-- Full-width fixed top bar (brand · streak · coins · profile) -->
    <DashboardTopBar class="fixed inset-x-0 top-0 z-50 print:hidden" />

    <!-- Drawer backdrop — mobile only, behind the sliding rail. -->
    <Transition name="fade">
      <div
        v-if="!docked && drawerOpen"
        class="fixed inset-0 top-16 z-40 bg-slate-900/50 backdrop-blur-sm"
        @click="closeDrawer"
      />
    </Transition>

    <!-- Left rail. Docked: sits in the layout, width animates between full and
         mini. Undocked: fixed off-canvas, slides in as a drawer. -->
    <aside
      class="fixed bottom-0 left-0 top-16 z-40 print:hidden border-r border-slate-200 bg-surface transition-[width,transform] duration-300 ease-out dark:border-hairline"
      :style="{
        width: `${docked ? width : 256}px`,
        transform: docked || drawerOpen ? 'none' : 'translateX(-100%)',
      }"
    >
      <div class="h-full overflow-y-auto overflow-x-hidden py-6" :class="mini ? 'px-3' : 'px-4'" v-os>
        <Sidebar :mini="mini" :docked="docked" @navigate="closeDrawer" />
      </div>
    </aside>

    <!-- Fixed right rail, below the top bar -->
    <div
      v-if="showRightRail"
      class="fixed bottom-0 right-0 top-16 z-30 hidden w-80 print:hidden border-l border-slate-200 bg-surface xl:block dark:border-hairline"
    >
      <div class="h-full overflow-y-auto px-4 py-6" v-os>
        <RightRail />
      </div>
    </div>

    <!-- Main content: clears the top bar and, when docked, the left rail; the
         right rail is cleared from xl up. padding-left is bound (not a utility)
         so it eases in step with the rail's width animation. -->
    <main
      id="main"
      tabindex="-1"
      class="app-main pt-16 transition-[padding] duration-300 ease-out"
      :class="showRightRail ? 'xl:pr-80' : ''"
      :style="{ paddingLeft: docked ? `${width}px` : '0px' }"
    >
      <div class="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
        <!-- Team announcements, the maintenance note and the "confirm your
             address" reminder; each renders nothing when it has nothing to say. -->
        <div class="space-y-2 has-[div]:mb-5">
          <VerifyEmailNotice />
          <AnnouncementBar />
        </div>
        <!-- Animate between /app children (dashboard ↔ study-plan ↔ …). The
             scroll-to-top rides on before-enter so a tab swap never shows the
             page you are leaving being pulled up to its own top first. -->
        <!-- Keyed on the language: switching it brings the page back with the
             course, the plan and the server's words fetched in the new one. -->
        <router-view v-slot="{ Component }">
          <Transition name="fade-slide" mode="out-in" @before-enter="flushPendingScroll">
            <component :is="Component" :key="locale" />
          </Transition>
        </router-view>
      </div>
    </main>
  </div>
</template>
