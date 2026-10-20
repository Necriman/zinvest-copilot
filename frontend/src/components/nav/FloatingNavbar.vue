<script setup>
/**
 * Landing navbar.
 *
 * The links are in-page section anchors, so they do two things depending on
 * where you are: scroll smoothly when already on the landing page, or route
 * back to it with the hash (the router's scrollBehavior finishes the job).
 * An IntersectionObserver marks whichever section is currently under the bar.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import BrandMark from '@/components/ui/BrandMark.vue'
import Icon from '@/components/ui/Icon.vue'
import LanguageSwitcher from '@/components/ui/LanguageSwitcher.vue'
import ThemeToggle from '@/components/ui/ThemeToggle.vue'
import UserPill from '@/components/ui/UserPill.vue'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

// Order matches the order the sections appear on the page, so the active
// highlight travels left-to-right as you scroll.
// Four, not five: "Learning paths" and "Learning" named the same promise
// twice, which cost the bar a slot and made the reader choose between
// synonyms. One "Learn" now covers both sections; the personal-plan section
// still sits on the page, it just no longer needs its own word up here.
// The ids are the main landing's sections (views/Landing.vue).
const NAV = [
  { key: 'howItWorks', hash: '#how-it-works' },
  { key: 'learn', hash: '#learning' },
  { key: 'whoItsFor', hash: '#who-its-for' },
  { key: 'zinvestAI', hash: '#zinvest-ai' },
]

const menuOpen = ref(false)
const scrolled = ref(false)
const activeHash = ref('')

const onLanding = computed(() => route.name === 'landing')

function go(hash) {
  menuOpen.value = false
  if (!onLanding.value) {
    router.push({ name: 'landing', hash })
    return
  }
  // Already here — scroll instead of navigating, which a same-route push would
  // refuse to do. `scroll-mt` on the sections clears the fixed bar.
  document.querySelector(hash)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  activeHash.value = hash
  history.replaceState(history.state, '', hash)
}

// --- chrome + scroll spy ---------------------------------------------------
const onScroll = () => {
  scrolled.value = window.scrollY > 8
}

// --- collapse on scroll ----------------------------------------------------
// At rest the bar is a wide pill and justify-between pushes the three groups
// apart. Once you scroll it draws in until it just fits them, so the empty
// space between disappears and brand / links / controls sit next to each other.
//
// This has to be a measured pixel width: `max-width: fit-content` is not a
// length, so it can't be transitioned — the bar would snap instead of animate.
const row = ref(null)
const compact = ref(0)

function measure() {
  const el = row.value
  // Only on the desktop layout. Below `lg` the links are behind the hamburger,
  // so collapsing would leave a stub of a bar with a menu hanging off it.
  if (!el || !window.matchMedia('(min-width: 1024px)').matches) {
    compact.value = 0
    return
  }
  const style = getComputedStyle(el)
  const gap = parseFloat(style.columnGap) || 0
  const padding = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight)
  const kids = [...el.children].filter((c) => c.getBoundingClientRect().width > 0)
  const content = kids.reduce((sum, c) => sum + c.getBoundingClientRect().width, 0)
  // +2 for the pill's own 1px borders.
  compact.value = Math.ceil(content + gap * Math.max(kids.length - 1, 0) + padding + 2)
}

// Re-measure whenever the contents change width: switching language, signing in
// (the account button replaces two links), or the webfont finishing loading.
let sizeObserver = null

let observer = null
// Ids currently crossing the band. Tracked across callbacks on purpose: an
// IntersectionObserver batch only carries the sections whose state *changed*,
// so deciding from one batch alone picks whichever happened to fire last.
const inBand = new Set()

function watchSections() {
  observer?.disconnect()
  observer = null
  inBand.clear()
  if (!onLanding.value || typeof IntersectionObserver === 'undefined') return

  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) inBand.add(entry.target.id)
        else inBand.delete(entry.target.id)
      }
      // Two sections straddle the band at every boundary — the outgoing one
      // still has a sliver under the bar while the incoming one has arrived.
      // NAV is in document order, so the last match is the furthest down.
      const current = NAV.filter((item) => inBand.has(item.hash.slice(1)))
      if (current.length) {
        activeHash.value = current[current.length - 1].hash
      } else if (window.scrollY < (document.querySelector(NAV[0].hash)?.offsetTop ?? 0)) {
        // Back up in the hero, which isn't one of the nav targets — nothing
        // should stay lit. Below the last section the highlight is left alone.
        activeHash.value = ''
      }
    },
    // The band runs from just under the bar down to a third of the viewport, so
    // a section takes over once its heading reaches the upper third.
    { rootMargin: '-88px 0px -65% 0px', threshold: 0 },
  )
  for (const item of NAV) {
    const el = document.querySelector(item.hash)
    if (el) observer.observe(el)
  }
}

onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', measure)
  // The landing view mounts in the same tick; wait a frame for its sections.
  requestAnimationFrame(watchSections)

  measure()
  document.fonts?.ready.then(measure)
  if (typeof ResizeObserver !== 'undefined' && row.value) {
    sizeObserver = new ResizeObserver(measure)
    for (const child of row.value.children) sizeObserver.observe(child)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', measure)
  observer?.disconnect()
  sizeObserver?.disconnect()
})

// Leaving the landing page invalidates every observed node.
watch(onLanding, () => {
  activeHash.value = ''
  requestAnimationFrame(watchSections)
})
// A route change should never leave the mobile sheet hanging open.
watch(() => route.fullPath, () => (menuOpen.value = false))

// --- mobile sheet animation ------------------------------------------------
// Height is animated in JS from the measured scrollHeight rather than through
// CSS `grid-template-rows: 0fr → 1fr`. iPad Safari doesn't interpolate `fr`
// tracks smoothly, so that approach snapped from a full-height flash to nothing
// (the tablet "jitter"). An explicit pixel height eases identically everywhere.
const reducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function onSheetEnter(el, done) {
  if (reducedMotion()) return done()
  el.style.height = '0px'
  el.style.opacity = '0'
  void el.offsetHeight // commit the start frame before transitioning
  el.style.transition = 'height 0.26s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.2s ease'
  el.style.height = `${el.scrollHeight}px`
  el.style.opacity = '1'
  el.addEventListener('transitionend', function end(e) {
    if (e.propertyName !== 'height') return
    el.removeEventListener('transitionend', end)
    done()
  })
}
function onSheetAfterEnter(el) {
  el.style.height = ''
  el.style.opacity = ''
  el.style.transition = ''
}
function onSheetLeave(el, done) {
  if (reducedMotion()) return done()
  el.style.height = `${el.scrollHeight}px`
  el.style.opacity = '1'
  void el.offsetHeight
  el.style.transition = 'height 0.22s ease, opacity 0.16s ease'
  el.style.height = '0px'
  el.style.opacity = '0'
  el.addEventListener('transitionend', function end(e) {
    if (e.propertyName !== 'height') return
    el.removeEventListener('transitionend', end)
    done()
  })
}
</script>

<template>
  <header class="fixed inset-x-0 top-4 z-40 px-4">
    <!-- The bar floats 16px down the page, so content scrolls through the strip
         above it. This fades that strip into the page colour; it sits behind
         the pill and takes no pointer events. -->
    <span
      aria-hidden="true"
      class="pointer-events-none absolute inset-x-0 -top-4 h-16 bg-gradient-to-b from-canvas via-canvas/75 to-transparent"
    />
    <div
      class="mx-auto max-w-6xl rounded-3xl border border-slate-200 backdrop-blur-xl transition-all duration-300 ease-out dark:border-hairline"
      :class="[
        scrolled ? 'shadow-float' : 'shadow-card',
        // Translucent as a bar, opaque as a menu — at 85% the hero headline
        // reads straight through the open sheet.
        menuOpen ? 'bg-white dark:bg-surface' : 'bg-white/80 dark:bg-surface/80',
      ]"
      :style="
        compact && scrolled && !menuOpen ? { maxWidth: `${compact}px` } : null
      "
    >
      <!-- Both side clusters are shrink-0, so justify-between splits the free
           space into two *equal* gaps around the links. A grid with 1fr side
           columns looks like it would centre things better, but the columns
           absorb the slack at their inner edges instead — that put 131px
           between the wordmark and the links and only 32px on the other side,
           which is what made the bar look lopsided.
           Padding is asymmetric on purpose: the right end is a filled pill
           whose own padding already reads as space, so it needs less around it
           than the bare wordmark on the left. -->
      <!-- `gap-6` is the *minimum* separation, which is all that's left once the
           bar has collapsed; at rest justify-between spreads the groups well
           past it, so the value only shows itself in the scrolled state. -->
      <div
        ref="row"
        class="flex items-center justify-between gap-6 pl-5 pr-3 transition-all duration-300"
        :class="scrolled ? 'py-2.5' : 'py-3'"
      >
        <!-- Brand. The social links live in the footer only — in the bar they
             sat between the wordmark and the section links and read as a third
             nav group. -->
        <div class="flex shrink-0 items-center">
          <RouterLink :to="{ name: 'landing' }" class="flex items-center gap-2">
            <BrandMark class="h-7 w-7 rounded-lg" />
            <span class="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white">
              {{ $t('common.appName') }}
            </span>
          </RouterLink>
        </div>

        <!-- Section links. `whitespace-nowrap` is load-bearing: the Russian and
             Uzbek labels are much longer than the English ones and wrapped the
             bar onto two lines. -->
        <nav class="hidden items-center gap-5 text-sm font-medium lg:flex xl:gap-7">
          <button
            v-for="item in NAV"
            :key="item.key"
            type="button"
            class="relative whitespace-nowrap py-1 transition"
            :class="
              activeHash === item.hash
                ? 'text-brand-600 dark:text-brand-400'
                : 'text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white'
            "
            @click="go(item.hash)"
          >
            {{ $t(`nav.${item.key}`) }}
            <span
              class="absolute inset-x-0 -bottom-0.5 h-0.5 rounded-full bg-brand-600 transition-opacity duration-200 dark:bg-brand-400"
              :class="activeHash === item.hash ? 'opacity-100' : 'opacity-0'"
            />
          </button>
        </nav>

        <!-- Right cluster. No coins/streak pills here: they're progress
             readouts that belong in the app, and at RU/UZ label widths they
             were what squeezed the bar onto two lines. -->
        <div class="flex shrink-0 items-center justify-end gap-0.5">
          <!-- The polar landing is dark by design, so a theme switch there
               would look broken; it comes back on every other page. -->
          <ThemeToggle v-if="!route.meta.polar" />
          <LanguageSwitcher />
          <template v-if="auth.isAuthenticated">
            <UserPill class="ml-1.5" />
          </template>
          <template v-else>
            <RouterLink
              :to="{ name: 'login' }"
              class="ml-1.5 hidden whitespace-nowrap px-2 text-sm font-medium text-slate-600 transition hover:text-slate-900 sm:block dark:text-slate-300 dark:hover:text-white"
            >
              {{ $t('nav.login') }}
            </RouterLink>
            <!-- Sign-up drops out of the bar on the smallest screens, where it
                 fought the theme/language/menu controls for room; it reappears
                 as a full-width CTA in the open sheet. -->
            <RouterLink
              :to="{ name: 'register' }"
              class="pill ml-1 hidden h-9 whitespace-nowrap bg-brand-600 px-4 text-sm font-semibold text-white transition hover:bg-brand-700 sm:inline-flex"
            >
              {{ $t('nav.register') }}
            </RouterLink>
          </template>

          <button
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 lg:hidden dark:text-slate-300 dark:hover:bg-surface-2"
            :aria-label="$t(menuOpen ? 'nav.closeMenu' : 'nav.menu')"
            :aria-expanded="menuOpen"
            @click="menuOpen = !menuOpen"
          >
            <Icon :name="menuOpen ? 'x' : 'menu'" class="h-[18px] w-[18px]" />
          </button>
        </div>
      </div>

      <!-- Mobile sheet. Inside the same rounded shell, so it reads as the bar
           expanding rather than a second floating surface. Height is animated in
           JS (see onSheet* hooks) — CSS `fr`-track easing jitters on iPad. -->
      <Transition :css="false" @enter="onSheetEnter" @after-enter="onSheetAfterEnter" @leave="onSheetLeave">
        <div v-if="menuOpen" class="overflow-hidden lg:hidden">
          <nav class="border-t border-hairline px-3 py-3">
            <button
              v-for="item in NAV"
              :key="item.key"
              type="button"
              class="flex w-full items-center justify-between rounded-2xl px-3 py-2.5 text-left text-sm font-medium transition"
              :class="
                activeHash === item.hash
                  ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2'
              "
              @click="go(item.hash)"
            >
              {{ $t(`nav.${item.key}`) }}
              <Icon name="chevronRight" class="h-4 w-4 opacity-40" />
            </button>

            <!-- Auth CTAs, for the widths where the bar hides them. -->
            <div v-if="!auth.isAuthenticated" class="mt-2 flex flex-col gap-2 border-t border-hairline pt-3 sm:hidden">
              <RouterLink
                :to="{ name: 'register' }"
                class="pill h-11 w-full justify-center bg-brand-600 text-sm font-semibold text-white transition hover:bg-brand-700"
              >
                {{ $t('nav.register') }}
              </RouterLink>
              <RouterLink
                :to="{ name: 'login' }"
                class="pill h-11 w-full justify-center border border-hairline text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2"
              >
                {{ $t('nav.login') }}
              </RouterLink>
            </div>
          </nav>
        </div>
      </Transition>
    </div>
  </header>
</template>
