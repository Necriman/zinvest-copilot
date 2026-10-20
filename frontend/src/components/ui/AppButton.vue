<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import Icon from './Icon.vue'

const props = defineProps({
  variant: { type: String, default: 'primary' }, // primary|outline|ghost
  size: { type: String, default: 'md' }, // sm|md|lg
  to: { type: [String, Object], default: null },
  // Plain anchor target — used by the landing page's in-page section links,
  // which are hashes rather than routes.
  href: { type: String, default: '' },
  icon: { type: String, default: '' },
  iconRight: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const VARIANTS = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 hover:shadow-lg hover:shadow-brand-600/20 shadow-sm',
  outline:
    'border border-slate-200 bg-white text-slate-800 hover:bg-slate-50 dark:border-hairline dark:bg-surface dark:text-ink dark:hover:bg-surface-2',
  ghost: 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-surface-2',
}
const SIZES = { sm: 'px-4 py-2 text-sm', md: 'px-5 py-2.5 text-sm', lg: 'px-7 py-3.5 text-base' }

const tag = computed(() => (props.to ? RouterLink : props.href ? 'a' : 'button'))
// Only the attributes the chosen tag takes. An `href: undefined` passed to
// RouterLink falls through onto its <a> and wipes the href it computed, which
// left the landing's main buttons without a real link (no new tab, no SEO).
const tagAttrs = computed(() => {
  if (props.to) return { to: props.to }
  if (props.href) return { href: props.href }
  return { disabled: props.disabled }
})
const cls = computed(() => [VARIANTS[props.variant] || VARIANTS.primary, SIZES[props.size] || SIZES.md])
</script>

<template>
  <component
    :is="tag"
    v-bind="tagAttrs"
    class="group pill justify-center font-semibold transition duration-200 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] disabled:translate-y-0 disabled:opacity-50"
    :class="cls"
  >
    <Icon v-if="icon" :name="icon" class="h-4 w-4" />
    <slot />
    <!-- The trailing arrow steps forward on hover: enough to read as an
         invitation, small enough that the label never shifts. -->
    <Icon
      v-if="iconRight"
      :name="iconRight"
      class="h-4 w-4 transition-transform duration-200 ease-out group-hover:translate-x-[3px] motion-reduce:transition-none motion-reduce:group-hover:translate-x-0"
    />
  </component>
</template>
