<script setup>
/**
 * Labelled text input with an optional leading icon, a hint line and — for
 * password fields — a reveal toggle.
 *
 * The toggle swaps the rendered `type`, so the field can't use `v-model` on a
 * dynamically-typed <input> (Vue rejects that). It binds :value/@input instead.
 */
import { computed, ref, useId } from 'vue'

import Icon from './Icon.vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, required: true },
  type: { type: String, default: 'text' },
  icon: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  autocomplete: { type: String, default: '' },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  required: { type: Boolean, default: false },
  // Empty: the translated "Show password" / "Hide password".
  revealLabel: { type: String, default: '' },
  hideLabel: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const id = useId()
const revealed = ref(false)
const isPassword = computed(() => props.type === 'password')
const inputType = computed(() => (isPassword.value && revealed.value ? 'text' : props.type))
const describedBy = computed(() => (props.error || props.hint ? `${id}-note` : undefined))
</script>

<template>
  <div>
    <label :for="id" class="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-200">
      {{ label }}
    </label>

    <div class="relative">
      <Icon
        v-if="icon"
        :name="icon"
        class="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
      />
      <input
        :id="id"
        :type="inputType"
        :value="modelValue"
        :placeholder="placeholder || undefined"
        :autocomplete="autocomplete || undefined"
        :required="required"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="describedBy"
        class="zx-input py-2.5 transition"
        :class="[
          icon ? 'pl-10' : '',
          isPassword ? 'pr-11' : '',
          error
            ? 'border-red-400 focus:border-red-500 dark:border-red-500/60'
            : 'focus:ring-2 focus:ring-brand-500/20',
        ]"
        @input="emit('update:modelValue', $event.target.value)"
      />
      <button
        v-if="isPassword"
        type="button"
        tabindex="-1"
        :aria-label="revealed ? hideLabel || $t('misc.hidePassword') : revealLabel || $t('misc.showPassword')"
        :title="revealed ? hideLabel || $t('misc.hidePassword') : revealLabel || $t('misc.showPassword')"
        class="absolute right-1.5 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-surface-2 dark:hover:text-slate-200"
        @click="revealed = !revealed"
      >
        <Icon :name="revealed ? 'eyeOff' : 'eye'" class="h-4 w-4" />
      </button>
    </div>

    <p
      v-if="error || hint"
      :id="`${id}-note`"
      class="mt-1.5 text-xs"
      :class="error ? 'text-red-600 dark:text-red-400' : 'text-slate-400'"
    >
      {{ error || hint }}
    </p>
  </div>
</template>
