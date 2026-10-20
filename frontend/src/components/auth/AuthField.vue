<script setup>
/**
 * The sign-in and sign-up field: a floating label that rises out of the way,
 * an icon, a soft brand glow on focus and, for passwords, a show/hide toggle.
 *
 * It tells the bear what is going on (useAuthBear): an address or a name makes
 * him lean in and read along with the caret, a hidden password makes him cover
 * his eyes, a shown one makes him peek. Leaving the field lets him relax.
 */
import { computed, ref, useId } from 'vue'

import Icon from '@/components/ui/Icon.vue'
import { authBear } from '@/composables/useAuthBear'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, required: true },
  type: { type: String, default: 'text' },
  icon: { type: String, default: '' },
  autocomplete: { type: String, default: 'off' },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  revealLabel: { type: String, default: 'Show' },
  hideLabel: { type: String, default: 'Hide' },
  autofocus: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const id = useId()
const input = ref(null)
const focused = ref(false)
const revealed = ref(false)

const isPassword = computed(() => props.type === 'password')
const inputType = computed(() => (isPassword.value && revealed.value ? 'text' : props.type))
const raised = computed(() => focused.value || !!props.modelValue)

function tellBear() {
  if (isPassword.value) authBear.set(revealed.value ? 'peek' : 'shy')
  else authBear.read(input.value)
}

function onInput(e) {
  emit('update:modelValue', e.target.value)
  tellBear()
}

function onFocus() {
  focused.value = true
  tellBear()
}

function onBlur() {
  focused.value = false
  // A beat later, so moving to the next field does not flicker through idle.
  setTimeout(() => {
    if (!document.activeElement?.closest?.('[data-auth-field]')) authBear.set('idle')
  }, 60)
}

function toggle() {
  revealed.value = !revealed.value
  authBear.set(revealed.value ? 'peek' : focused.value ? 'shy' : 'idle')
  input.value?.focus({ preventScroll: true })
}

defineExpose({ focus: () => input.value?.focus() })
</script>

<template>
  <div class="af" data-auth-field :class="{ 'af--raised': raised, 'af--focus': focused, 'af--error': error }">
    <div class="af__box">
      <Icon v-if="icon" :name="icon" class="af__icon" aria-hidden="true" />
      <input
        :id="id"
        ref="input"
        class="af__input"
        :class="{ 'af__input--icon': icon, 'af__input--toggle': isPassword }"
        :type="inputType"
        :value="modelValue"
        :autocomplete="autocomplete"
        :autofocus="autofocus"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="error || hint ? `${id}-note` : undefined"
        placeholder=" "
        spellcheck="false"
        autocapitalize="off"
        @input="onInput"
        @focus="onFocus"
        @blur="onBlur"
        @keyup="tellBear"
        @click="tellBear"
      />
      <label :for="id" class="af__label" :class="{ 'af__label--icon': icon }">{{ label }}</label>
      <button
        v-if="isPassword"
        type="button"
        class="af__toggle"
        :aria-label="revealed ? hideLabel : revealLabel"
        :aria-pressed="revealed"
        @mousedown.prevent
        @click="toggle"
      >
        <Icon :name="revealed ? 'eyeOff' : 'eye'" class="h-[18px] w-[18px]" />
      </button>
    </div>
    <p v-if="error || hint" :id="`${id}-note`" class="af__note" :class="{ 'af__note--error': error }">
      {{ error || hint }}
    </p>
  </div>
</template>

<style scoped>
.af__box {
  position: relative;
}
.af__input {
  display: block;
  width: 100%;
  height: 3.6rem;
  padding: 1.35rem 1rem 0.45rem;
  border-radius: 1rem;
  border: 1.5px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 1rem;
  font-weight: 500;
  outline: none;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    background-color 0.2s ease;
}
.af__input--icon {
  padding-left: 2.9rem;
}
.af__input--toggle {
  padding-right: 3.2rem;
}
.af__input:hover {
  border-color: color-mix(in oklab, var(--brand-500) 35%, var(--border));
}
.af--focus .af__input {
  border-color: var(--brand-500);
  box-shadow: 0 0 0 4px color-mix(in oklab, var(--brand-500) 18%, transparent);
  background: var(--surface);
}
.af--error .af__input {
  border-color: #e5484d;
  box-shadow: 0 0 0 4px rgba(229, 72, 77, 0.14);
}
.af__icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  width: 1.15rem;
  height: 1.15rem;
  transform: translateY(-50%);
  color: var(--text-faint);
  pointer-events: none;
  transition: color 0.2s ease;
}
.af--focus .af__icon {
  color: var(--brand-500);
}
.af__label {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  transform-origin: 0 50%;
  color: var(--text-muted);
  font-size: 1rem;
  pointer-events: none;
  transition:
    transform 0.2s cubic-bezier(0.22, 1, 0.36, 1),
    color 0.2s ease;
}
.af__label--icon {
  left: 2.9rem;
}
.af--raised .af__label {
  transform: translateY(-118%) scale(0.76);
}
.af--focus .af__label {
  color: var(--brand-600);
}
:where(.dark) .af--focus .af__label {
  color: var(--brand-300);
}
.af__toggle {
  position: absolute;
  right: 0.55rem;
  top: 50%;
  display: grid;
  place-items: center;
  width: 2.5rem;
  height: 2.5rem;
  transform: translateY(-50%);
  border-radius: 0.75rem;
  color: var(--text-muted);
  transition:
    color 0.2s ease,
    background-color 0.2s ease;
}
.af__toggle:hover {
  color: var(--text);
  background: var(--surface-2);
}
.af__toggle:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 1px;
}
.af__note {
  margin-top: 0.45rem;
  padding-left: 0.25rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}
.af__note--error {
  color: #d93036;
}
@media (prefers-reduced-motion: reduce) {
  .af__label,
  .af__input {
    transition: none;
  }
}
</style>
