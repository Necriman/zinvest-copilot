<script setup>
/**
 * Reusable tick control — checkbox or radio, circle or square.
 *
 * Wraps a real (visually hidden) <input> so it stays keyboard-reachable, focus-
 * ringed and screen-reader correct; the visible box is a sibling <span> driven
 * by the checked state. Used by Today's Tasks, and meant for quiz answers,
 * settings and any future checklist.
 *
 *   <CheckBox v-model="done" label="Read a balance sheet" />
 *   <CheckBox v-model="picked" type="radio" :value="opt.id" shape="circle" />
 *   <CheckBox v-model="selectedIds" :value="row.id" />   <!-- array = group -->
 */
import { computed } from 'vue'

import Icon from './Icon.vue'

const props = defineProps({
  modelValue: { type: [Boolean, String, Number, Array], default: false },
  // Identifies this control within a radio group or an array-backed checkbox group.
  value: { type: [String, Number, Boolean], default: undefined },
  type: { type: String, default: 'checkbox' }, // 'checkbox' | 'radio'
  shape: { type: String, default: 'circle' }, // 'circle' | 'square'
  size: { type: String, default: 'md' }, // 'sm' | 'md' | 'lg'
  label: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  /** Strike through + fade the label once ticked (checklist style). */
  strikeWhenChecked: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'change'])

const SIZES = {
  sm: { box: 'h-4 w-4', icon: 'h-2.5 w-2.5', dot: 'h-1.5 w-1.5', text: 'text-xs' },
  md: { box: 'h-5 w-5', icon: 'h-3 w-3', dot: 'h-2 w-2', text: 'text-sm' },
  lg: { box: 'h-6 w-6', icon: 'h-3.5 w-3.5', dot: 'h-2.5 w-2.5', text: 'text-base' },
}
const dims = computed(() => SIZES[props.size] || SIZES.md)

const isGroup = computed(() => Array.isArray(props.modelValue))
const checked = computed(() => {
  if (props.type === 'radio') return props.modelValue === props.value
  if (isGroup.value) return props.modelValue.includes(props.value)
  return Boolean(props.modelValue)
})

function toggle() {
  if (props.disabled) return
  let next
  if (props.type === 'radio') {
    next = props.value
  } else if (isGroup.value) {
    next = checked.value
      ? props.modelValue.filter((v) => v !== props.value)
      : [...props.modelValue, props.value]
  } else {
    next = !checked.value
  }
  emit('update:modelValue', next)
  emit('change', next)
}
</script>

<template>
  <label
    class="group flex items-center gap-3"
    :class="disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'"
  >
    <!-- The real control: invisible but focusable, so tab/space still work. -->
    <input
      :type="type"
      class="peer sr-only"
      :checked="checked"
      :disabled="disabled"
      @change="toggle"
    />
    <span
      class="flex shrink-0 items-center justify-center border-2 transition-colors duration-150 peer-focus-visible:ring-2 peer-focus-visible:ring-brand-500 peer-focus-visible:ring-offset-2 dark:peer-focus-visible:ring-offset-surface"
      :class="[
        dims.box,
        shape === 'square' ? 'rounded-md' : 'rounded-full',
        checked
          ? 'border-brand-600 bg-brand-600 text-white'
          : 'border-slate-300 bg-transparent dark:border-hairline',
        !checked && !disabled ? 'group-hover:border-brand-400' : '',
      ]"
    >
      <!-- Radio reads as a filled dot; checkbox as a tick. -->
      <span v-if="checked && type === 'radio'" class="rounded-full bg-white" :class="dims.dot" />
      <Icon v-else-if="checked" name="check" :class="dims.icon" />
    </span>

    <span
      v-if="label || $slots.default"
      :class="[
        dims.text,
        checked && strikeWhenChecked
          ? 'text-slate-400 line-through'
          : 'text-slate-700 dark:text-slate-200',
      ]"
    >
      <slot>{{ label }}</slot>
    </span>
  </label>
</template>
