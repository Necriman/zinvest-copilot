<script setup>
/**
 * Select any text, ask Zinvest about it — the button and the answer card.
 *
 * Over an ordinary selection a small "Ask Zinvest" pill appears; inside the
 * lesson editor the same action lives in the editor's own selection menu (see
 * DocumentEditor), so two menus never fight over the same spot. Either way the
 * question goes out at once and the answer lands in one card next to the
 * text, so the learner never leaves what they were reading.
 *
 * The card is deliberately not dismissed by clicking elsewhere: reading the
 * explanation beside the paragraph is the point. It closes with its ×, Esc, or
 * a change of page.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AiAvatar from './AiAvatar.vue'
import AiText from './AiText.vue'
import Icon from '@/components/ui/Icon.vue'
import { useAskAI } from '@/composables/useAskAI'

const { state, ask, close, handOff } = useAskAI()
const route = useRoute()
const router = useRouter()

const coarse = typeof window !== 'undefined' && window.matchMedia?.('(pointer: coarse)').matches

// ---- the pill over a selection -------------------------------------------
const pill = reactive({ show: false, x: 0, y: 0, below: false, text: '', rect: null })

// Form fields and the lesson editor are excluded: in a field, selecting is
// editing; in the editor, its own menu carries the button.
const SKIP = 'input, textarea, select, [contenteditable="true"], .ProseMirror, [data-no-ask]'

function readSelection() {
  const sel = window.getSelection?.()
  if (!sel || sel.isCollapsed || !sel.rangeCount) return null
  const text = sel.toString().replace(/\s+/g, ' ').trim()
  if (text.length < 2) return null
  const anchor = sel.anchorNode?.nodeType === 1 ? sel.anchorNode : sel.anchorNode?.parentElement
  if (!anchor || anchor.closest(SKIP)) return null
  const rect = sel.getRangeAt(0).getBoundingClientRect()
  if (!rect.width && !rect.height) return null
  return { text, rect }
}

let timer = null
function refresh() {
  clearTimeout(timer)
  // Let the browser finish the selection (double-click, drag end) first.
  timer = setTimeout(() => {
    const found = readSelection()
    if (!found) {
      pill.show = false
      return
    }
    const { rect } = found
    // Phones draw their own copy/paste bar above a selection: go below it.
    const below = coarse || rect.top < 72
    Object.assign(pill, {
      show: true,
      text: found.text,
      rect,
      below,
      x: Math.min(Math.max(rect.left + rect.width / 2, 90), window.innerWidth - 90),
      y: below ? rect.bottom + 10 : rect.top - 10,
    })
  }, coarse ? 120 : 10)
}

function onSelectionChange() {
  const sel = window.getSelection?.()
  if (!sel || sel.isCollapsed) pill.show = false
}
function onKeyUp(event) {
  if (event.key === 'Escape') {
    pill.show = false
    if (state.open) close()
    return
  }
  if (event.shiftKey) refresh()
}
function onScroll() {
  pill.show = false
}

function askNow() {
  pill.show = false
  ask(pill.text, pill.rect)
  // Drop the highlight, so the pill does not come straight back.
  window.getSelection?.()?.removeAllRanges()
}

onMounted(() => {
  document.addEventListener('mouseup', refresh)
  document.addEventListener('touchend', refresh, { passive: true })
  document.addEventListener('keyup', onKeyUp)
  document.addEventListener('selectionchange', onSelectionChange)
  window.addEventListener('scroll', onScroll, { passive: true, capture: true })
  window.addEventListener('resize', onResize, { passive: true })
})
onBeforeUnmount(() => {
  clearTimeout(timer)
  document.removeEventListener('mouseup', refresh)
  document.removeEventListener('touchend', refresh)
  document.removeEventListener('keyup', onKeyUp)
  document.removeEventListener('selectionchange', onSelectionChange)
  window.removeEventListener('scroll', onScroll, { capture: true })
  window.removeEventListener('resize', onResize)
  close()
})

// A new page is a new context: the card and the pill go with the old one.
watch(
  () => route.fullPath,
  () => {
    pill.show = false
    if (state.open) close()
  },
)

// ---- the answer card -------------------------------------------------------
const CARD_W = 352
// A card, not a page: long answers scroll inside it.
const CARD_MAX_H = 420
const narrow = ref(typeof window !== 'undefined' && window.innerWidth < 640)
function onResize() {
  narrow.value = window.innerWidth < 640
}

// Beside the selection on a wide screen: under it when there is room, over it
// when not. On a phone, a sheet along the bottom edge.
const cardStyle = computed(() => {
  if (narrow.value) return null
  const r = state.rect
  const vw = window.innerWidth
  const vh = window.innerHeight
  // Nothing on screen to sit beside (no anchor, or it has scrolled away):
  // dock in the corner, where a chat widget would be, not off the screen.
  if (!r || r.bottom < 0 || r.top > vh) {
    return { right: '24px', bottom: '24px', maxHeight: `${Math.min(CARD_MAX_H, vh - 48)}px` }
  }
  const left = Math.min(Math.max(r.left + r.width / 2 - CARD_W / 2, 12), vw - CARD_W - 12)
  const roomBelow = vh - r.bottom
  if (roomBelow > 300 || roomBelow > r.top) {
    return { left: `${left}px`, top: `${Math.min(r.bottom + 12, vh - 160)}px`, maxHeight: `${Math.min(CARD_MAX_H, Math.max(160, vh - r.bottom - 24))}px` }
  }
  return { left: `${left}px`, bottom: `${vh - r.top + 12}px`, maxHeight: `${Math.min(CARD_MAX_H, Math.max(160, r.top - 24))}px` }
})

// A long answer scrolls inside the card without a scrollbar of its own; a
// fade along the bottom edge says there is more until the end is reached.
const bodyEl = ref(null)
const more = ref(false)
function measure() {
  const el = bodyEl.value
  more.value = !!el && el.scrollTop + el.clientHeight < el.scrollHeight - 4
}
watch(
  () => [state.open, state.loading, state.answer],
  () => nextTick(() => {
    if (bodyEl.value) bodyEl.value.scrollTop = 0
    measure()
  }),
)

function continueInChat() {
  handOff()
  if (route.name === 'zinvestAI') window.dispatchEvent(new CustomEvent('zinvest-ai-handoff'))
  else router.push({ name: 'zinvestAI' })
}
</script>

<template>
  <!-- The pill -->
  <Transition name="ask-pop">
    <button
      v-if="pill.show"
      type="button"
      data-no-ask
      class="ask-pill"
      :class="pill.below ? 'ask-pill--below' : ''"
      :style="{ left: pill.x + 'px', top: pill.y + 'px' }"
      @mousedown.prevent
      @click="askNow"
    >
      <AiAvatar class="h-5 w-5" />
      {{ $t('askAI.button') }}
    </button>
  </Transition>

  <!-- The answer -->
  <Transition name="ask-card">
    <section
      v-if="state.open"
      data-no-ask
      class="ask-card"
      :class="narrow ? 'ask-card--sheet' : ''"
      :style="cardStyle"
      role="dialog"
      aria-modal="false"
      :aria-label="$t('ai.title')"
    >
      <header class="flex items-start gap-2.5">
        <AiAvatar :thinking="state.loading" class="h-8 w-8" />
        <div class="min-w-0 flex-1">
          <p class="text-xs font-bold text-ink">{{ $t('ai.title') }}</p>
          <p class="ask-card__quote">«{{ state.text }}»</p>
        </div>
        <button type="button" class="ask-card__close" :aria-label="$t('askAI.close')" @click="close">
          <Icon name="x" class="h-4 w-4" />
        </button>
      </header>

      <div
        ref="bodyEl"
        class="ask-card__body"
        :class="{ 'ask-card__body--more': more }"
        aria-live="polite"
        @scroll.passive="measure"
      >
        <p v-if="state.loading" class="ask-card__typing" :aria-label="$t('ai.thinking')">
          <span /><span /><span />
        </p>
        <p v-else-if="state.error" class="text-sm text-amber-700 dark:text-amber-300">{{ state.answer }}</p>
        <AiText v-else class="text-sm text-ink" :text="state.answer" />
      </div>

      <footer v-if="!state.loading && !state.error && state.answer" class="ask-card__foot">
        <button type="button" class="ask-card__more" @click="continueInChat">
          {{ $t('askAI.continue') }}
          <Icon name="arrowRight" class="h-3.5 w-3.5" />
        </button>
      </footer>
    </section>
  </Transition>
</template>

<style scoped>
.ask-pill {
  position: fixed;
  z-index: 70;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  transform: translate(-50%, -100%);
  border-radius: 999px;
  border: 1px solid var(--color-hairline);
  background: var(--surface);
  padding: 0.3rem 0.8rem 0.3rem 0.3rem;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-ink);
  box-shadow: 0 12px 28px -14px rgb(15 23 42 / 0.45);
  white-space: nowrap;
}
.ask-pill--below {
  transform: translate(-50%, 0);
}
.ask-pill:hover {
  border-color: color-mix(in oklab, var(--brand-500) 55%, transparent);
}
.ask-pill:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
}

.ask-card {
  position: fixed;
  z-index: 70;
  width: 22rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow: hidden;
  border-radius: 1.25rem;
  border: 1px solid var(--color-hairline);
  background: var(--surface);
  padding: 0.9rem 1rem 1rem;
  box-shadow: 0 24px 60px -24px rgb(15 23 42 / 0.5);
}
.ask-card--sheet {
  left: 0.75rem;
  right: 0.75rem;
  bottom: 0.75rem;
  width: auto;
  max-height: 60vh;
}
.ask-card__quote {
  margin-top: 0.1rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 0.75rem;
  line-height: 1.4;
  color: var(--color-ink-muted);
}
.ask-card__close {
  display: grid;
  place-items: center;
  width: 1.75rem;
  aspect-ratio: 1;
  flex-shrink: 0;
  border-radius: 0.6rem;
  color: var(--color-ink-muted);
  transition: background-color 150ms ease;
}
.ask-card__close:hover {
  background: var(--surface-2);
  color: var(--color-ink);
}
.ask-card__body {
  min-height: 2.5rem;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: none;
}
.ask-card__body::-webkit-scrollbar {
  display: none;
}
.ask-card__body--more {
  -webkit-mask-image: linear-gradient(to bottom, #000 calc(100% - 2.5rem), transparent);
  mask-image: linear-gradient(to bottom, #000 calc(100% - 2.5rem), transparent);
}
.ask-card__typing {
  display: inline-flex;
  gap: 0.25rem;
  border-radius: 0.9rem;
  background: var(--surface-2);
  padding: 0.75rem 0.9rem;
}
.ask-card__typing span {
  width: 0.33rem;
  aspect-ratio: 1;
  border-radius: 999px;
  background: var(--color-ink-faint);
  animation: ask-blink 1.1s ease-in-out infinite;
}
.ask-card__typing span:nth-child(2) {
  animation-delay: 0.16s;
}
.ask-card__typing span:nth-child(3) {
  animation-delay: 0.32s;
}
@keyframes ask-blink {
  0%,
  60%,
  100% {
    opacity: 0.3;
  }
  30% {
    opacity: 1;
  }
}
.ask-card__foot {
  border-top: 1px solid var(--color-hairline);
  padding-top: 0.7rem;
}
.ask-card__more {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--brand-700);
}
.dark .ask-card__more {
  color: var(--brand-300);
}
.ask-card__more:hover {
  text-decoration: underline;
}

.ask-pop-enter-active,
.ask-pop-leave-active,
.ask-card-enter-active,
.ask-card-leave-active {
  transition:
    opacity 180ms ease,
    translate 180ms var(--ease-out);
}
.ask-pop-enter-from,
.ask-pop-leave-to {
  opacity: 0;
  translate: 0 4px;
}
.ask-card-enter-from,
.ask-card-leave-to {
  opacity: 0;
  translate: 0 6px;
}

@media (prefers-reduced-motion: reduce) {
  .ask-card__typing span {
    animation: none;
    opacity: 0.6;
  }
  .ask-pop-enter-active,
  .ask-pop-leave-active,
  .ask-card-enter-active,
  .ask-card-leave-active {
    transition: none;
  }
}
</style>
