<script setup>
/**
 * Appearance — theme and accent colour.
 *
 * Applied locally the instant you click (so it feels immediate) and then
 * mirrored onto the account so the choice follows you to other devices.
 */
import BearSticker from '@/components/mascot/BearSticker.vue'
import Icon from '@/components/ui/Icon.vue'
import { updateProfile } from '@/api/account'
import { useMascot } from '@/composables/useMascot'
import { RATES, useNarrator } from '@/voice/narrator'
import { BRAND_PRESETS, useTheme } from '@/composables/useTheme'
import { useTask } from '@/composables/useTask'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const { theme, brand, setTheme, setBrand } = useTheme()
const { state, run } = useTask()
const { animated, reducedMotion, setAnimated } = useMascot()
const narrator = useNarrator()
const voiceOn = narrator.enabled
const voiceRate = narrator.rate

const THEMES = [
  { key: 'light', icon: 'sun' },
  { key: 'dark', icon: 'moon' },
  { key: 'system', icon: 'globe' },
]

function chooseTheme(value) {
  setTheme(value)
  run(async () => auth.setUser(await updateProfile({ theme: value })))
}

function chooseBrand(hex) {
  setBrand(hex)
  run(async () => auth.setUser(await updateProfile({ brand_color: hex || '' })))
}
</script>

<template>
  <div>
    <h2 class="text-base font-bold text-slate-900 dark:text-white">{{ $t('settings.appearance') }}</h2>
    <p class="mt-1 text-sm text-slate-500">{{ $t('settings.appearanceHint') }}</p>

    <p class="mt-6 text-xs font-semibold text-slate-500">{{ $t('settings.theme') }}</p>
    <div class="mt-3 grid gap-3 sm:grid-cols-3">
      <button
        v-for="option in THEMES"
        :key="option.key"
        type="button"
        class="flex items-center gap-3 rounded-2xl border-2 px-4 py-3 text-left transition"
        :class="
          theme === option.key
            ? 'border-brand-500 bg-brand-50 dark:bg-brand-500/10'
            : 'border-slate-200 hover:border-brand-300 dark:border-hairline'
        "
        @click="chooseTheme(option.key)"
      >
        <Icon :name="option.icon" class="h-4 w-4 text-brand-600" />
        <span class="text-sm font-semibold text-slate-700 dark:text-slate-200">
          {{ $t(`settings.theme_${option.key}`) }}
        </span>
      </button>
    </div>

    <p class="mt-7 text-xs font-semibold text-slate-500">{{ $t('settings.brandColor') }}</p>
    <p class="mt-1 text-xs text-slate-400">{{ $t('settings.brandColorHint') }}</p>
    <div class="mt-3 flex flex-wrap items-center gap-2.5">
      <button
        v-for="preset in BRAND_PRESETS"
        :key="preset.key"
        type="button"
        class="h-9 w-9 rounded-full transition-transform hover:scale-110"
        :class="
          brand.toLowerCase() === preset.hex
            ? 'ring-2 ring-offset-2 dark:ring-offset-surface'
            : 'ring-1 ring-inset ring-black/10 dark:ring-white/15'
        "
        :style="{ background: preset.hex, '--tw-ring-color': preset.hex }"
        :title="$t(`settings.color_${preset.key}`)"
        @click="chooseBrand(preset.hex)"
      />

      <label
        class="flex h-9 cursor-pointer items-center gap-2 rounded-full border border-slate-200 px-3 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 dark:border-hairline dark:text-slate-300 dark:hover:bg-surface-2"
        :title="$t('settings.customColor')"
      >
        <span
          class="h-4 w-4 rounded-full ring-1 ring-inset ring-black/10"
          :style="{ background: brand || 'transparent' }"
        />
        {{ $t('settings.customColor') }}
        <input type="color" class="sr-only" :value="brand || '#6943cc'" @input="chooseBrand($event.target.value)" />
      </label>

      <button
        v-if="brand"
        type="button"
        class="h-9 rounded-full px-3 text-xs font-semibold text-slate-500 transition hover:bg-slate-100 dark:hover:bg-surface-2"
        @click="chooseBrand('')"
      >
        {{ $t('settings.resetColor') }}
      </button>
    </div>
    <div class="mt-7 flex items-center gap-4 rounded-2xl border border-slate-200 p-4 dark:border-hairline">
      <BearSticker :name="animated && !reducedMotion ? 'happy' : 'idle'" class="h-16 w-16 shrink-0" />
      <div class="min-w-0 flex-1">
        <p class="text-sm font-semibold text-slate-700 dark:text-slate-200" id="mascot-animated-label">{{ $t('mascot.animated') }}</p>
        <p class="mt-0.5 text-xs text-slate-500">{{ reducedMotion ? $t('mascot.reducedMotion') : $t('mascot.animatedHint') }}</p>
      </div>
      <button
        type="button"
        role="switch"
        :aria-checked="animated"
        aria-labelledby="mascot-animated-label"
        :disabled="reducedMotion"
        class="relative h-7 w-12 shrink-0 rounded-full transition disabled:opacity-50"
        :class="animated ? 'bg-brand-600' : 'bg-slate-300 dark:bg-slate-600'"
        @click="setAnimated(!animated)"
      >
        <span class="absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition-all" :class="animated ? 'left-[22px]' : 'left-0.5'" />
      </button>
    </div>
    <div class="mt-3 rounded-2xl border border-slate-200 p-4 dark:border-hairline">
      <div class="flex items-center gap-4">
        <span class="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300" aria-hidden="true">
          <Icon :name="voiceOn ? 'volume' : 'volumeOff'" class="h-7 w-7" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold text-slate-700 dark:text-slate-200" id="mascot-voice-label">{{ $t('voice.on') }}</p>
          <p class="mt-0.5 text-xs text-slate-500">{{ $t('voice.hint') }}</p>
        </div>
        <button
          type="button"
          role="switch"
          :aria-checked="voiceOn"
          aria-labelledby="mascot-voice-label"
          class="relative h-7 w-12 shrink-0 rounded-full transition"
          :class="voiceOn ? 'bg-brand-600' : 'bg-slate-300 dark:bg-slate-600'"
          @click="narrator.setEnabled(!voiceOn)"
        >
          <span class="absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition-all" :class="voiceOn ? 'left-[22px]' : 'left-0.5'" />
        </button>
      </div>
      <div v-if="voiceOn" class="mt-4 flex flex-wrap items-center gap-3 pl-20">
        <span class="text-xs font-semibold text-slate-500" id="mascot-voice-speed">{{ $t('voice.speed') }}</span>
        <div class="inline-flex rounded-xl bg-slate-100 p-1 dark:bg-surface-2" role="radiogroup" aria-labelledby="mascot-voice-speed">
          <button
            v-for="r in RATES"
            :key="r"
            type="button"
            role="radio"
            :aria-checked="voiceRate === r"
            class="min-h-9 rounded-lg px-3 text-xs font-semibold tabular-nums transition"
            :class="voiceRate === r ? 'bg-white text-slate-900 shadow-sm dark:bg-surface dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200'"
            @click="narrator.setRate(r)"
          >
            {{ r }}×
          </button>
        </div>
      </div>
    </div>
    <p v-if="state.error" class="mt-3 text-sm text-red-500">{{ state.error }}</p>
  </div>
</template>
