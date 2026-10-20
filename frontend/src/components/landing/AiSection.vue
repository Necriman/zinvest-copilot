<script setup>
/**
 * Zinvest AI. The mock exchange uses the runway/burn question because that's
 * the kind of thing unit 03 actually covers — no capability is claimed here
 * that the advisor endpoint doesn't already serve.
 */
import AiAvatar from '@/components/ai/AiAvatar.vue'
import Icon from '@/components/ui/Icon.vue'
import Reveal from './Reveal.vue'
import SectionHeading from './SectionHeading.vue'

const FEATURES = [
  { key: 'f1', icon: 'map' },
  { key: 'f2', icon: 'comment' },
  { key: 'f3', icon: 'undo' },
]
</script>

<template>
  <section id="zinvest-ai" class="scroll-mt-28 px-6 py-16 sm:py-24">
    <div class="mx-auto max-w-6xl">
      <div
        class="card relative overflow-hidden p-6 sm:p-10 lg:p-12"
      >
        <div class="relative grid items-center gap-8 lg:grid-cols-2 lg:gap-12">
          <div>
            <Reveal>
              <SectionHeading
                align="left"
                :eyebrow="$t('landing.ai.eyebrow')"
                :title="$t('landing.ai.title')"
                :subtitle="$t('landing.ai.subtitle')"
              />
            </Reveal>

            <dl class="mt-9 space-y-5">
              <Reveal v-for="(feature, i) in FEATURES" :key="feature.key" :delay="i * 70">
                <div class="flex gap-4">
                  <div
                    class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-brand-600 shadow-card dark:bg-surface-2 dark:text-brand-300"
                  >
                    <Icon :name="feature.icon" class="h-4 w-4" />
                  </div>
                  <div>
                    <dt class="text-sm font-bold text-slate-900 dark:text-white">
                      {{ $t(`landing.ai.${feature.key}.title`) }}
                    </dt>
                    <dd class="mt-1 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                      {{ $t(`landing.ai.${feature.key}.body`) }}
                    </dd>
                  </div>
                </div>
              </Reveal>
            </dl>
          </div>

          <!-- Conversation mock -->
          <Reveal :delay="140">
            <div class="rounded-3xl border border-hairline bg-white/80 p-5 shadow-float backdrop-blur dark:bg-surface/80">
              <div class="flex items-center gap-2.5 border-b border-hairline pb-4">
                <AiAvatar class="h-9 w-9" />
                <span class="text-sm font-extrabold text-slate-900 dark:text-white">
                  {{ $t('landing.ai.eyebrow') }}
                </span>
                <span
                  class="pill ml-auto bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
                >
                  {{ $t('landing.ai.quota') }}
                </span>
              </div>

              <div class="space-y-4 pt-5">
                <p
                  class="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-md bg-brand-600 px-4 py-2.5 text-sm text-white"
                >
                  {{ $t('landing.ai.chatQ') }}
                </p>
                <div class="flex gap-2.5">
                  <AiAvatar class="mt-0.5 h-8 w-8" />
                  <p
                    class="max-w-[85%] rounded-2xl rounded-tl-md bg-slate-100 px-4 py-2.5 text-sm leading-relaxed text-slate-700 dark:bg-surface-2 dark:text-slate-200"
                  >
                    {{ $t('landing.ai.chatA') }}
                  </p>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </div>
  </section>
</template>
