<script setup>
import { RouterLink } from 'vue-router'

import BrandMark from '@/components/ui/BrandMark.vue'
import { BUSINESS, LEGAL_DOCS } from '@/legal/business'
import Icon from '@/components/ui/Icon.vue'
import LanguageSwitcher from '@/components/ui/LanguageSwitcher.vue'

// Only the year is dynamic — everything else is a section of the main landing
// (views/Landing.vue), linked through the router so it also works from pages
// that share this footer (the 404), or a route that already exists.
const year = new Date().getFullYear()

const PRODUCT = [
  { label: 'nav.howItWorks', href: '#how-it-works' },
  { label: 'nav.learningPaths', href: '#learning-paths' },
  { label: 'nav.zinvestAI', href: '#zinvest-ai' },
]
const LEARN = [
  { label: 'nav.learn', href: '#learning' },
  { label: 'nav.whoItsFor', href: '#who-its-for' },
  { label: 'nav.faq', href: '#faq' },
]

// The bear's Telegram bot (TELEGRAM_BOT_USERNAME on the backend). There is no
// Instagram account yet, so no Instagram button: a link to "#" is worse than none.
const TELEGRAM_URL = 'https://t.me/ZinvestAI_bot'
</script>

<template>
  <footer class="border-t border-hairline px-6 py-14">
    <div class="mx-auto max-w-6xl">
      <div class="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
        <!-- Brand -->
        <div class="lg:col-span-2">
          <RouterLink :to="{ name: 'landing' }" class="flex items-center gap-2">
            <BrandMark class="h-7 w-7 rounded-lg" />
            <span class="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white">
              {{ $t('common.appName') }}
            </span>
          </RouterLink>
          <p class="mt-4 max-w-xs text-sm leading-relaxed text-slate-500 dark:text-slate-400">
            {{ $t('landing.footer.tagline') }}
          </p>
          <div class="mt-5 flex items-center gap-2">
            <a
              :href="TELEGRAM_URL"
              target="_blank"
              rel="noopener"
              :aria-label="'Telegram'"
              class="flex h-11 w-11 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-surface-2 dark:hover:text-slate-200"
            >
              <Icon name="send" class="h-[18px] w-[18px]" />
            </a>
          </div>
        </div>

        <div>
          <p class="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">
            {{ $t('landing.footer.product') }}
          </p>
          <ul class="mt-2">
            <li v-for="link in PRODUCT" :key="link.href">
              <RouterLink
                :to="{ name: 'landing', hash: link.href }"
                class="inline-flex min-h-11 items-center text-sm text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              >
                {{ $t(link.label) }}
              </RouterLink>
            </li>
          </ul>
        </div>

        <div>
          <p class="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">
            {{ $t('landing.footer.learn') }}
          </p>
          <ul class="mt-2">
            <li v-for="link in LEARN" :key="link.href">
              <RouterLink
                :to="{ name: 'landing', hash: link.href }"
                class="inline-flex min-h-11 items-center text-sm text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              >
                {{ $t(link.label) }}
              </RouterLink>
            </li>
            <li>
              <RouterLink
                :to="{ name: 'register' }"
                class="inline-flex min-h-11 items-center text-sm text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              >
                {{ $t('nav.register') }}
              </RouterLink>
            </li>
          </ul>
        </div>
      </div>

      <div
        class="mt-12 flex flex-col-reverse items-center justify-between gap-4 border-t border-hairline pt-8 sm:flex-row"
      >
        <div class="text-center text-xs text-slate-500 sm:text-left dark:text-slate-400">
          <p>
            {{ $t('landing.footer.rights', { year }) }}
            <template v-if="BUSINESS.operator"> · {{ BUSINESS.operator }}</template>
            <template v-if="BUSINESS.email">
              · <a :href="`mailto:${BUSINESS.email}`" class="underline-offset-2 hover:underline">{{ BUSINESS.email }}</a>
            </template>
          </p>
          <nav class="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1 sm:justify-start" :aria-label="$t('legal.nav')">
            <RouterLink
              v-for="doc in LEGAL_DOCS"
              :key="doc"
              :to="{ name: 'legal', params: { doc } }"
              class="inline-flex min-h-8 items-center transition hover:text-slate-900 dark:hover:text-white"
            >
              {{ $t(`legal.docs.${doc}`) }}
            </RouterLink>
          </nav>
        </div>
        <LanguageSwitcher />
      </div>
    </div>
  </footer>
</template>
