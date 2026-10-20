<script setup>
/**
 * Explain / Quiz me / Analyse my mistake / Give an example.
 *
 * The same four actions on the start screen and above the message box, so
 * what a learner found on the way in is still there mid-conversation. "My
 * mistake" is disabled rather than hidden when there is none: seeing it greyed
 * out tells the learner it exists and what feeds it.
 */
import { ACTIONS } from './actions'
import Icon from '@/components/ui/Icon.vue'

defineProps({
  ctx: { type: Object, default: null },
  compact: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
defineEmits(['pick'])
</script>

<template>
  <!-- On the start screen: one row when it fits, a 2×2 block when it does
       not — never three and a lonely fourth. Mid-conversation: one tight row. -->
  <div :class="compact ? 'flex flex-wrap gap-2' : 'grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:justify-center'">
    <button
      v-for="action in ACTIONS"
      :key="action.key"
      type="button"
      class="inline-flex items-center gap-1.5 border font-semibold transition duration-200 ease-out focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-45"
      :class="[
        compact
          ? 'min-h-9 rounded-full px-3 text-xs'
          : 'min-h-10 justify-center rounded-2xl px-4 py-2 text-sm leading-tight sm:rounded-full sm:py-0',
        'border-hairline bg-surface text-ink-muted enabled:hover:-translate-y-px enabled:hover:border-brand-400 enabled:hover:text-brand-700 dark:enabled:hover:text-brand-300',
      ]"
      :disabled="disabled || (action.key === 'mistake' && !ctx?.mistake)"
      :title="action.key === 'mistake' && !ctx?.mistake ? $t('aiHome.noMistake') : undefined"
      @click="$emit('pick', action.key)"
    >
      <Icon :name="action.icon" :class="compact ? 'h-3.5 w-3.5' : 'h-4 w-4'" />
      {{ $t(`aiHome.action.${action.key}`) }}
    </button>
  </div>
</template>
