<script setup>
/**
 * My Startup — the founder's workspace.
 *
 * First visit shows a five-question intake; the answers go to the AI, which
 * writes an assessment and picks which blocks to surface. After that the page is
 * a grid of workspace blocks (employees, optional task board, products, AI
 * advisor, AI roadmap, founder matches, monthly finances, to-dos). Blocks render in the
 * order saved in blocks.enabled; founders rearrange them by dragging a block's
 * handle or with the arrows in the customize panel. The right rail is hidden for this route
 * (see the `meta.rightRail: false` guard in the router) so the grid runs full
 * width.
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import BearSticker from '@/components/mascot/BearSticker.vue'
import BusinessDetails from '@/components/startup/BusinessDetails.vue'

import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import StartupOnboarding from '@/components/startup/StartupOnboarding.vue'
import EmployeesBlock from '@/components/startup/EmployeesBlock.vue'
import TaskDashboardBlock from '@/components/startup/TaskDashboardBlock.vue'
import ProductsBlock from '@/components/startup/ProductsBlock.vue'
import AiAdvisorBlock from '@/components/startup/AiAdvisorBlock.vue'
import FinanceBlock from '@/components/startup/FinanceBlock.vue'
import TodoBlock from '@/components/startup/TodoBlock.vue'
import MatchesBlock from '@/components/startup/MatchesBlock.vue'
import RoadmapBlock from '@/components/startup/RoadmapBlock.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { getStartupProfile, updateStartupProfile } from '@/api/startup'

const { data: profile, loading, error, reload } = useAsyncData(getStartupProfile)
const configuring=ref(false),saving=ref(false),saveError=ref('')
const rosterVersion=ref(0)
const blockKeys=['employees','tasks','products','finance','advisor','roadmap','matches','todo','demand','locations']
// Saved order first; unknown keys from an older client are dropped.
const order=computed(()=>(profile.value?.blocks?.enabled||blockKeys).filter(k=>blockKeys.includes(k)))
const enabled=key=>order.value.includes(key)
const hidden=computed(()=>blockKeys.filter(k=>!enabled(k)))
async function saveOrder(keys){
  if(saving.value)return
  const previous=profile.value.blocks
  profile.value={...profile.value,blocks:{...(previous||{}),enabled:keys}} // optimistic, so a drop lands instantly
  saving.value=true;saveError.value=''
  try{profile.value=await updateStartupProfile({blocks:keys})}
  catch(e){profile.value={...profile.value,blocks:previous};saveError.value=e?.response?.data?.detail||e.message}
  finally{saving.value=false}
}
function toggleBlock(key){saveOrder(enabled(key)?order.value.filter(k=>k!==key):[...order.value,key])}
function move(key,delta){
  const keys=[...order.value],from=keys.indexOf(key),to=from+delta
  if(from<0||to<0||to>=keys.length)return
  keys.splice(to,0,keys.splice(from,1)[0]);saveOrder(keys)
}

// Drag and drop (mouse). Touch and keyboard users move blocks with the arrows.
const dragging=ref(null),over=ref(null)
function dragStart(key,e){dragging.value=key;e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',key);const card=e.target.closest('[data-block]');if(card)e.dataTransfer.setDragImage(card,24,24)}
function dragEnd(){dragging.value=null;over.value=null}
function drop(target){
  const key=dragging.value;dragEnd()
  if(!key||key===target)return
  const keys=order.value.filter(k=>k!==key)
  keys.splice(keys.indexOf(target)+(order.value.indexOf(key)<order.value.indexOf(target)?1:0),0,key)
  saveOrder(keys)
}
function saved(p){profile.value=p}

const onboarded = computed(() => !!profile.value?.onboarding_completed)
// The optional Task-Dashboard block is enabled by the AI recommendation.
// Two independent columns (blocks alternate left, right, left...) instead of a
// row grid: in a grid a tall block stretches its row and leaves a hole next to
// it. One column when the page is narrow, in the saved order.
const workspace = ref(null)
const twoColumns = ref(false)
const columns = computed(() => (twoColumns.value ? [order.value.filter((_, i) => i % 2 === 0), order.value.filter((_, i) => i % 2 === 1)] : [order.value]))
const resize = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(([entry]) => { twoColumns.value = entry.contentRect.width >= 760 }) : null
watch(workspace, (el, before) => {
  if (before) resize?.unobserve(before)
  if (el) resize?.observe(el)
})
onBeforeUnmount(() => resize?.disconnect())

const showTasks = computed(() => (profile.value?.blocks?.enabled || []).includes('tasks'))
</script>

<template>
  <div>
    <h1 class="mb-6 text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
      {{ $t('dashboard.myStartup') }}
    </h1>
    <div v-if="onboarded" class="card mb-6 flex items-center justify-between gap-4 overflow-hidden px-6">
      <div class="py-5"><p class="text-xs font-bold uppercase tracking-widest text-brand-600">{{ $t('business.workspace') }}</p><h2 class="mt-2 text-xl font-extrabold">{{ profile.name || $t('business.grow') }}</h2><p class="mt-2 max-w-lg text-sm text-slate-600 dark:text-slate-300">{{ $t('business.intro') }}</p><div class="mt-4 flex flex-wrap gap-3"><button class="min-h-11 rounded-xl bg-brand-600 px-4 text-sm font-semibold text-white" :aria-expanded="configuring" @click="configuring=!configuring">{{ $t('business.customize') }}</button><RouterLink :to="{name:'network'}" class="inline-flex min-h-11 items-center rounded-xl border border-hairline px-4 text-sm font-semibold">{{ $t('network.title') }}</RouterLink></div></div><BearSticker name="tablet" float class="hidden h-44 w-44 shrink-0 self-end sm:block" />
    </div>
    <div v-if="configuring" class="card mb-6 p-4">
      <p class="mb-3 text-sm text-slate-500">{{ $t('layout.hint') }}</p>
      <ol class="grid gap-2 sm:grid-cols-2">
        <li v-for="(key,i) in order" :key="key" class="flex min-h-11 items-center gap-2 rounded-xl border border-hairline px-3">
          <label class="flex min-w-0 flex-1 items-center gap-2"><input type="checkbox" checked :disabled="saving" @change="toggleBlock(key)" /><span class="truncate">{{ $t(`business.block_${key}`) }}</span></label>
          <button type="button" class="min-h-11 min-w-9 rounded-lg text-slate-500 hover:bg-slate-100 disabled:opacity-30 dark:hover:bg-surface-2" :disabled="saving||i===0" :aria-label="$t('layout.up',{name:$t(`business.block_${key}`)})" @click="move(key,-1)">↑</button>
          <button type="button" class="min-h-11 min-w-9 rounded-lg text-slate-500 hover:bg-slate-100 disabled:opacity-30 dark:hover:bg-surface-2" :disabled="saving||i===order.length-1" :aria-label="$t('layout.down',{name:$t(`business.block_${key}`)})" @click="move(key,1)">↓</button>
        </li>
      </ol>
      <div v-if="hidden.length" class="mt-3 flex flex-wrap gap-2"><label v-for="key in hidden" :key="key" class="flex min-h-11 items-center gap-2 rounded-xl border border-dashed border-hairline px-3 text-slate-500"><input type="checkbox" :disabled="saving" @change="toggleBlock(key)" />{{ $t(`business.block_${key}`) }}</label></div>
    </div>
    <p v-if="saveError" role="alert" class="mb-4 text-red-600">{{ saveError }}</p>

    <div v-if="loading" class="mx-auto max-w-xl space-y-3">
      <LoadingSkeleton height="h-8" rounded="rounded-xl" />
      <LoadingSkeleton v-for="n in 3" :key="n" height="h-16" rounded="rounded-2xl" />
    </div>

    <!-- Intake gate -->
    <div v-else-if="error" role="alert" class="card p-5"><p>{{ error }}</p><button class="mt-3 min-h-11 px-4 text-brand-600" @click="reload().catch(()=>{})">{{ $t('business.retry') }}</button></div>
    <StartupOnboarding v-else-if="!onboarded" @done="reload" />

    <!-- Workspace -->
    <div v-else ref="workspace" class="flex items-start gap-6">
      <TransitionGroup v-for="(column, c) in columns" :key="c" tag="div" name="block" class="flex min-w-0 flex-1 flex-col gap-6">
      <div
        v-for="key in column"
        :key="key"
        data-block
        class="group/block relative min-w-0 rounded-3xl"
        :class="[dragging===key&&'opacity-40', over===key&&dragging!==key&&'ring-2 ring-brand-500 ring-offset-4 ring-offset-transparent']"
        @dragover.prevent="dragging&&(over=key)"
        @drop.prevent="drop(key)"
      >
        <button
          type="button"
          draggable="true"
          class="block-handle absolute left-1/2 top-1 z-10 flex h-6 w-12 -translate-x-1/2 cursor-grab items-center justify-center rounded-full text-slate-400 opacity-0 transition hover:bg-slate-100 hover:text-slate-600 focus-visible:opacity-100 group-hover/block:opacity-100 active:cursor-grabbing dark:hover:bg-surface-2"
          :aria-label="$t('layout.handle',{name:$t(`business.block_${key}`)})"
          :title="$t('layout.drag')"
          @dragstart="dragStart(key,$event)"
          @dragend="dragEnd"
          @keydown.up.prevent="move(key,-1)"
          @keydown.down.prevent="move(key,1)"
        ><svg viewBox="0 0 20 8" class="h-2 w-5" aria-hidden="true" fill="currentColor"><circle cx="3" cy="2" r="1.4"/><circle cx="10" cy="2" r="1.4"/><circle cx="17" cy="2" r="1.4"/><circle cx="3" cy="6" r="1.4"/><circle cx="10" cy="6" r="1.4"/><circle cx="17" cy="6" r="1.4"/></svg></button>
        <EmployeesBlock v-if="key==='employees'" :currency="profile.currency || 'UZS'" @changed="rosterVersion++" />
        <TaskDashboardBlock v-else-if="key==='tasks'" :roster-version="rosterVersion" />
        <ProductsBlock v-else-if="key==='products'" />
        <FinanceBlock v-else-if="key==='finance'" :currency="profile.currency || 'UZS'" />
        <AiAdvisorBlock v-else-if="key==='advisor'" :profile="profile" />
        <RoadmapBlock v-else-if="key==='roadmap'" />
        <MatchesBlock v-else-if="key==='matches'" :profile="profile" />
        <TodoBlock v-else-if="key==='todo'" />
        <BusinessDetails v-else-if="key==='demand'" :profile="profile" kind="demand" @saved="saved" />
        <BusinessDetails v-else-if="key==='locations'" :profile="profile" kind="locations" @saved="saved" />
      </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<style scoped>
.block-move { transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1); }
/* Touch screens have no hover and no HTML5 drag: they use the arrows in the customize panel. */
@media (pointer: coarse) { .block-handle { display: none; } }
@media (prefers-reduced-motion: reduce) { .block-move { transition: none; } }
</style>
