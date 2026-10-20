<script setup>
/**
 * Settings — categories down the side, one section at a time.
 *
 * The active category lives in `?tab=`, so a section is linkable and survives a
 * refresh. Each section is its own component under components/settings/ and
 * owns its own requests; nothing here knows what they do.
 */
import { computed, markRaw, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import SettingsAccount from '@/components/settings/SettingsAccount.vue'
import SettingsAppearance from '@/components/settings/SettingsAppearance.vue'
import SettingsLearning from '@/components/settings/SettingsLearning.vue'
import SettingsPrivacy from '@/components/settings/SettingsPrivacy.vue'
import SettingsProfile from '@/components/settings/SettingsProfile.vue'
import SettingsTelegram from '@/components/settings/SettingsTelegram.vue'
import Icon from '@/components/ui/Icon.vue'

const route = useRoute()
const router = useRouter()

const CATEGORIES = [
  { key: 'profile', icon: 'user', label: 'settings.profile', component: markRaw(SettingsProfile) },
  { key: 'account', icon: 'shield', label: 'settings.account', component: markRaw(SettingsAccount) },
  { key: 'appearance', icon: 'palette', label: 'settings.appearance', component: markRaw(SettingsAppearance) },
  { key: 'privacy', icon: 'lock', label: 'settings.privacy', component: markRaw(SettingsPrivacy) },
  { key: 'learning', icon: 'map', label: 'settings.studyPlan', component: markRaw(SettingsLearning) },
  { key: 'telegram', icon: 'send', label: 'telegram.title', component: markRaw(SettingsTelegram) },
]

const active = computed(() => {
  const wanted = String(route.query.tab || '')
  return CATEGORIES.find((c) => c.key === wanted) || CATEGORIES[0]
})

function select(key) {
  if (key !== active.value.key) router.replace({ query: { ...route.query, tab: key } })
}

// Normalise an unknown ?tab= so the URL always reflects what's on screen.
watch(
  () => route.query.tab,
  (tab) => {
    if (tab !== active.value.key) router.replace({ query: { ...route.query, tab: active.value.key } })
  },
  { immediate: true },
)

// --- panel transition ------------------------------------------------------
// Direction is derived from where the category sits in the rail, and watched on
// `active` rather than set in the click handler so back/forward and deep links
// animate correctly too.
const direction = ref('down')
let lastIndex = CATEGORIES.indexOf(active.value)
watch(active, (category) => {
  const index = CATEGORIES.indexOf(category)
  direction.value = index >= lastIndex ? 'down' : 'up'
  lastIndex = index
})

// The card is height-animated across the swap. Without this, `mode="out-in"`
// empties the card between panels, so a tall section → short one collapses to
// nothing and snaps back.
const panelHeight = ref(null) // px while animating, null = auto
const settling = ref(false)

function lockHeight(el) {
  settling.value = true
  panelHeight.value = el.offsetHeight
}
function growTo(el) {
  // The incoming panel is already laid out (its enter transform doesn't affect
  // layout), so this is its final height.
  panelHeight.value = el.offsetHeight
}
function release() {
  panelHeight.value = null
  settling.value = false
}
</script>

<template>
  <div>
    <h1 class="mb-6 text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
      {{ $t('nav.settings') }}
    </h1>

    <div class="flex flex-col gap-6 md:flex-row md:items-start">
      <!-- Category nav: a rail on desktop, a scrolling strip on mobile.
           The labels are nowrap only on the mobile strip, which scrolls
           sideways. In the desktop rail the box is a fixed width, and the
           longer RU/UZ labels ran straight out of it — there they wrap. -->
      <nav
        class="-mx-1 flex shrink-0 gap-1 overflow-x-auto px-1 pb-1 md:sticky md:top-20 md:mx-0 md:w-56 md:flex-col md:overflow-visible md:px-0 md:pb-0"
      >
        <button
          v-for="category in CATEGORIES"
          :key="category.key"
          type="button"
          class="flex shrink-0 items-center gap-2.5 whitespace-nowrap rounded-xl px-3.5 py-2.5 text-left text-sm font-semibold transition md:w-full md:whitespace-normal"
          :class="
            active.key === category.key
              ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300'
              : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-surface-2 dark:hover:text-slate-200'
          "
          @click="select(category.key)"
        >
          <Icon :name="category.icon" class="h-4 w-4" />
          {{ $t(category.label) }}
        </button>
      </nav>

      <!-- Active section. Keyed so switching category remounts cleanly rather
           than reusing a sibling's form state. The inner wrapper carries the
           height animation; `overflow-hidden` only while it runs, so it can't
           clip focus rings or the colour picker at rest. -->
      <div class="card min-w-0 flex-1 p-6">
        <div
          data-settings-panel
          class="transition-[height] duration-300 ease-out"
          :class="settling ? 'overflow-hidden' : ''"
          :style="panelHeight !== null ? { height: `${panelHeight}px` } : null"
        >
          <Transition
            :name="`settings-${direction}`"
            mode="out-in"
            @before-leave="lockHeight"
            @enter="growTo"
            @after-enter="release"
          >
            <component :is="active.component" :key="active.key" />
          </Transition>
        </div>
      </div>
    </div>
  </div>
</template>
