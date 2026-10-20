import { createRouter, createWebHistory } from 'vue-router'

import { authReady } from '@/api/bootstrap'
import { loadingBar } from '@/composables/useLoadingBar'
import { clearPendingScroll, clearReturn, deferScroll, isReturning, rememberReturn } from '@/router/navScroll'
import { applyTitle } from '@/router/titles'
import { useAuthStore } from '@/store/auth'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/LandingLayout.vue'),
    children: [
      // The first landing is the main one again, with the new bear in it.
      { path: '', name: 'landing', component: () => import('@/views/Landing.vue') },
      // It used to live at /old; links shared from then land on the same page.
      { path: 'old', redirect: { name: 'landing' } },
      // The other directions stay reachable so they can be compared side by
      // side and put back without a deploy: V4 (dark, the coin video), V3
      // (Duolingo-style) and V2 (the narrative one).
      { path: 'v4', name: 'landingV4', component: () => import('@/views/LandingV4.vue'), meta: { polar: true } },
      { path: 'v3', name: 'landingV3', component: () => import('@/views/LandingV3.vue') },
      { path: 'v2', name: 'landingV2', component: () => import('@/views/LandingV2.vue') },
      // Privacy, Terms, Cookies, Refunds, Licences. Public, signed in or not.
      { path: 'legal/:doc?', name: 'legal', component: () => import('@/views/Legal.vue') },
    ],
  },
  {
    // Sign-in / sign-up get their own split-screen shell rather than the
    // marketing navbar and footer, which only compete with a form.
    path: '/',
    component: () => import('@/layouts/AuthLayout.vue'),
    meta: { guestOnly: true },
    children: [
      { path: 'login', name: 'login', component: () => import('@/views/Login.vue') },
      { path: 'register', name: 'register', component: () => import('@/views/Register.vue') },
      { path: 'forgot-password', name: 'forgotPassword', component: () => import('@/views/ForgotPassword.vue') },
    ],
  },
  {
    path: '/app',
    component: () => import('@/layouts/DashboardLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'dashboard', component: () => import('@/views/Dashboard.vue') },
      { path: 'study-plan', name: 'studyPlan', component: () => import('@/views/StudyPlan.vue') },
      { path: 'lessons', name: 'lessons', component: () => import('@/views/Lessons.vue') },
      { path: 'notes', name: 'notes', component: () => import('@/views/Notes.vue') },
      { path: 'units', name: 'units', component: () => import('@/views/Units.vue') },
      { path: 'drills', name: 'drills', component: () => import('@/views/Drills.vue') },
      { path: 'practice', name: 'practice', component: () => import('@/views/Practice.vue') },
      { path: 'predict', name: 'predict', component: () => import('@/views/Predict.vue') },
      // Unit tests run full screen at /learn/test/:unitId; the old list page was never built.
      { path: 'mock-tests', name: 'mockTests', redirect: { name: 'studyPlan' } },
      { path: 'ai', name: 'zinvestAI', component: () => import('@/views/ZinvestAI.vue') },
      { path: 'startup', name: 'myStartup', component: () => import('@/views/MyStartup.vue'), meta: { rightRail: false } },
      { path: 'startup/roadmap', name: 'startupRoadmap', component: () => import('@/views/StartupRoadmap.vue'), meta: { rightRail: false } },
      { path: 'copilot', name: 'copilot', component: () => import('@/views/Copilot.vue'), meta: { rightRail: false } },
      { path: 'copilot/history', name: 'copilotHistory', component: () => import('@/views/CopilotHistory.vue'), meta: { rightRail: false } },
      { path: 'network', name: 'network', component: () => import('@/views/Network.vue'), meta: { rightRail: false } },
      // The bear lives inside lessons, tests and the dashboard now; old links land on Today.
      { path: 'bear', redirect: { name: 'dashboard' } },
      { path: 'cashflow', name: 'cashFlow', component: () => import('@/views/CashFlow.vue') },
      { path: 'leaderboard', name: 'leaderboard', component: () => import('@/views/Leaderboard.vue') },
      // Empty placeholder until the screen exists: keep old links working.
      { path: 'score-map', name: 'scoreMap', redirect: { name: 'dashboard' } },
      { path: 'plans', name: 'plans', component: () => import('@/views/Plans.vue') },
      { path: 'settings', name: 'settings', component: () => import('@/views/Settings.vue') },
      // Profile folded into Settings; the redirect keeps old links working.
      { path: 'profile', redirect: { name: 'settings' } },
    ],
  },
  {
    // Full-screen 50/50 lesson view — deliberately NOT under /app so it escapes
    // the sidebar/right-rail chrome. Its own meta.requiresAuth keeps it guarded.
    path: '/learn/:lessonId',
    name: 'lesson',
    component: () => import('@/views/LessonView.vue'),
    meta: { requiresAuth: true },
  },
  {
    // Unit test, full screen like a lesson (the static 'test' segment outranks :lessonId).
    path: '/learn/test/:unitId',
    name: 'unitTest',
    component: () => import('@/views/UnitTest.vue'),
    meta: { requiresAuth: true },
  },
  {
    // Sign-up assessment. Full-screen and outside /app: it runs before the
    // learner has a plan, so the dashboard chrome would be empty anyway.
    path: '/onboarding',
    name: 'onboarding',
    component: () => import('@/views/Onboarding.vue'),
    meta: { requiresAuth: true },
  },
  {
    // Note editor — same reasoning as the lesson view: no sidebar, no right
    // rail, just the document on its resizable sheet of paper.
    path: '/notes/:noteId',
    name: 'noteEditor',
    component: () => import('@/views/NoteEditor.vue'),
    meta: { requiresAuth: true },
  },
  {
    // Admin panel for the team. Not /admin: nginx sends /admin/ to Django's own
    // admin. `staff` keeps learners out here; the API checks every request anyway,
    // and `perm` hides a section the role cannot open.
    path: '/admin-panel',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, staff: true },
    children: [
      { path: '', redirect: { name: 'adminOverview' } },
      { path: 'overview', name: 'adminOverview', component: () => import('@/views/admin/AdminOverview.vue'), meta: { perm: 'overview.view' } },
      { path: 'users', name: 'adminUsers', component: () => import('@/views/admin/AdminUsers.vue'), meta: { perm: 'users.view' } },
      { path: 'users/:id', name: 'adminUser', component: () => import('@/views/admin/AdminUserDetail.vue'), meta: { perm: 'users.view' } },
      { path: 'content', name: 'adminContent', component: () => import('@/views/admin/AdminContent.vue'), meta: { perm: 'content.view' } },
      { path: 'moderation', name: 'adminModeration', component: () => import('@/views/admin/AdminModeration.vue'), meta: { perm: 'moderation.view' } },
      { path: 'ai', name: 'adminAI', component: () => import('@/views/admin/AdminAI.vue'), meta: { perm: 'ai.view' } },
      { path: 'announcements', name: 'adminAnnouncements', component: () => import('@/views/admin/AdminAnnouncements.vue'), meta: { perm: 'announcements.view' } },
      { path: 'team', name: 'adminTeam', component: () => import('@/views/admin/AdminTeam.vue'), meta: { perm: 'users.view' } },
      { path: 'startups', name: 'adminStartups', component: () => import('@/views/admin/AdminStartups.vue'), meta: { perm: 'startups.view' } },
      { path: 'system', name: 'adminSystem', component: () => import('@/views/admin/AdminSystem.vue'), meta: { perm: 'system.view' } },
      { path: 'security', name: 'adminSecurity', component: () => import('@/views/admin/AdminSecurity.vue'), meta: { perm: 'security.view' } },
      { path: 'audit', name: 'adminAudit', component: () => import('@/views/admin/AdminAudit.vue'), meta: { perm: 'audit.view' } },
      { path: 'settings', name: 'adminSettings', component: () => import('@/views/admin/AdminSettings.vue'), meta: { perm: 'settings.view' } },
    ],
  },
  {
    // Links people open from a letter (password reset, address confirmation).
    // Not guest-only: following one while signed in must still work.
    path: '/',
    component: () => import('@/layouts/AuthLayout.vue'),
    children: [
      { path: 'reset-password', name: 'resetPassword', component: () => import('@/views/ResetPassword.vue') },
      { path: 'verify-email', name: 'verifyEmail', component: () => import('@/views/VerifyEmail.vue') },
    ],
  },
  // The app lives at /app; people type /dashboard.
  { path: '/dashboard', redirect: { name: 'dashboard' } },
  {
    path: '/:pathMatch(.*)*',
    component: () => import('@/layouts/LandingLayout.vue'),
    children: [{ path: '', name: 'notFound', component: () => import('@/views/NotFound.vue') }],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // Anything a previous navigation parked is stale the moment a new one starts.
    clearPendingScroll()
    // Back/forward keeps its place.
    if (savedPosition) return savedPosition
    // Coming back out of a lesson to the list it was opened from. The offset is
    // restored by DashboardLayout, not here: the top-level view transition runs
    // out-in, so the destination has not mounted yet at this point — the old
    // lesson is still on screen and only a screen tall, and scrolling now would
    // just clamp to zero.
    if (isReturning(to.fullPath)) return false
    // Landing section anchors. `top` clears the fixed navbar; scroll-mt on the
    // sections covers same-page clicks, this covers arriving with a hash.
    if (to.hash) return { el: to.hash, top: 96, behavior: 'smooth' }
    // Staying on the same route and only changing the query is a view syncing
    // its own state to the URL, not a navigation — the study map writes
    // ?unit= as you scroll past each unit, and Settings writes ?tab=. Scrolling
    // to the top there would yank the page back every time.
    if (to.path === from.path) return false
    // A real navigation starts at the top — but not this instant. The view
    // transitions run out-in, so the page being left is still the only thing on
    // screen for another beat; scrolling now visibly rips it up to its own top
    // before the new view has even appeared. Hand the position to the
    // transition, which applies it in the gap between the two. The very first
    // navigation has no outgoing view and so no transition to flush it.
    if (!from.name) return { top: 0 }
    deferScroll({ top: 0 })
    return false
  },
})

router.beforeEach(async (to, from) => {
  loadingBar.routeStart()
  await authReady

  const auth = useAuthStore()

  if (to.matched.some((r) => r.meta.requiresAuth) && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }
  if (to.meta.staff && !auth.user?.staff_role) {
    return { name: 'dashboard' }
  }

  // Opening a lesson from inside the app: note the way back before the page we
  // are leaving is torn down. Lesson → lesson (Prev/Next, or completing one and
  // rolling into the next) deliberately leaves the note alone, so Back still
  // returns to wherever the run started.
  if (to.name === 'lesson') {
    if (from.name && from.name !== 'lesson') rememberReturn(from.fullPath)
  } else if (!isReturning(to.fullPath)) {
    clearReturn()
  }
  return true
})

router.afterEach((to) => {
  loadingBar.routeDone()
  applyTitle(to)
})
router.onError(() => loadingBar.routeDone())

export default router
