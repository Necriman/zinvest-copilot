<script setup>
import Icon from '@/components/ui/Icon.vue'
import SidebarItem from './SidebarItem.vue'
import StreakCallout from './StreakCallout.vue'
import { useSidebar } from '@/composables/useSidebar'

// `mini`/`docked` come from the layout so one Sidebar serves the full rail, the
// mini icon rail and the mobile drawer. `navigate` fires on any link tap so the
// drawer can close itself.
defineProps({
  mini: { type: Boolean, default: false },
  docked: { type: Boolean, default: true },
})
defineEmits(['navigate'])

const { toggleCollapsed } = useSidebar()

// Decluttered nav: only the essentials.
const SECTIONS = [
  {
    key: 'main',
    items: [
      { name: 'dashboard', icon: 'home', label: 'nav.today', exact: true },
      { name: 'studyPlan', icon: 'map', label: 'nav.studyPlan' },
      { name: 'lessons', icon: 'book', label: 'nav.lessons' },
      { name: 'units', icon: 'target', label: 'nav.units' },
      { name: 'drills', icon: 'zap', label: 'challenge.title' },
      { name: 'practice', icon: 'checkCircle', label: 'trainer.title' },
      { name: 'predict', icon: 'trending', label: 'upDown.title' },
      { name: 'leaderboard', icon: 'trophy', label: 'league.title' },
    ],
  },
  {
    key: 'tools',
    items: [
      { name: 'notes', icon: 'note', label: 'nav.notes' },
      { name: 'zinvestAI', icon: 'bot', label: 'nav.zinvestAI' },
      { name: 'copilot', icon: 'sparkles', label: 'copilot.nav' },
      { name: 'myStartup', icon: 'store', label: 'nav.myStartup' },
      { name: 'network', icon: 'globe', label: 'network.title' },
      { name: 'plans', icon: 'coin', label: 'nav.plans' },
    ],
  },
]
</script>

<template>
  <aside class="flex h-full flex-col gap-4">
    <!-- Header: the collapse control, docked right.
         In the mini rail the badge drops and the (now expand) control centres;
         in the drawer there's no control at all, since it closes instead. -->
    <div class="flex items-center gap-2" :class="mini ? 'justify-center' : ''">
      <button
        v-if="docked"
        type="button"
        class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-transparent text-slate-400 transition hover:border-hairline hover:bg-slate-50 hover:text-slate-600 dark:hover:bg-surface-2 dark:hover:text-slate-200"
        :class="mini ? '' : 'ml-auto'"
        :title="$t(mini ? 'nav.expandSidebar' : 'nav.collapseSidebar')"
        :aria-label="$t(mini ? 'nav.expandSidebar' : 'nav.collapseSidebar')"
        @click="toggleCollapsed"
      >
        <Icon name="chevronRight" class="h-4 w-4 transition-transform" :class="mini ? '' : 'rotate-180'" />
      </button>
    </div>

    <!-- No scroller of its own: the rail around it scrolls, with the overlay
         scrollbar, so a short window never shows a second, native one. -->
    <nav class="flex flex-1 flex-col gap-6">
      <div
        v-for="(section, i) in SECTIONS"
        :key="section.key"
        :class="mini && i > 0 ? 'mt-2 border-t border-hairline pt-3' : ''"
      >
        <p
          v-if="!mini"
          class="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-400"
        >
          {{ $t(`nav.${section.key}`) }}
        </p>
        <div class="flex flex-col gap-0.5">
          <SidebarItem
            v-for="item in section.items"
            :key="item.name"
            :item="item"
            :mini="mini"
            @navigate="$emit('navigate')"
          />
        </div>
      </div>
    </nav>

    <StreakCallout v-if="!mini" />
  </aside>
</template>
