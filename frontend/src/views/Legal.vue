<script setup>
/**
 * /legal/:doc — Privacy Policy, Terms, Cookie Policy, Refund Policy and
 * Licences, in the reader's language. The texts live in src/legal/docs.*.js;
 * who runs Zinvest comes from src/legal/business.js and is shown at the end of
 * every page, with only the fields that are filled in.
 */
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { BUSINESS, LEGAL_DOCS, LEGAL_UPDATED } from '@/legal/business'
import en from '@/legal/docs.en'
import ru from '@/legal/docs.ru'
import uz from '@/legal/docs.uz'

const TEXTS = { en, ru, uz }

const route = useRoute()
const router = useRouter()
const { locale, t } = useI18n()

const key = computed(() => (LEGAL_DOCS.includes(route.params.doc) ? route.params.doc : 'privacy'))
const doc = computed(() => (TEXTS[locale.value] || TEXTS.en)[key.value])
const updated = computed(() =>
  new Date(`${LEGAL_UPDATED}T00:00:00`).toLocaleDateString(locale.value, { day: 'numeric', month: 'long', year: 'numeric' }),
)
const hasOperator = computed(() => BUSINESS.operator || BUSINESS.regNo || BUSINESS.address || BUSINESS.email)

// An unknown document name lands on the privacy policy instead of a blank page.
watch(
  () => route.params.doc,
  (name) => {
    if (name && !LEGAL_DOCS.includes(name)) router.replace({ name: 'legal', params: { doc: 'privacy' } })
  },
  { immediate: true },
)
watch(
  doc,
  (d) => {
    if (d) document.title = `${d.title} · Zinvest`
  },
  { immediate: true },
)
</script>

<template>
  <main class="lg-page">
    <nav class="lg-tabs" :aria-label="t('legal.nav')">
      <RouterLink
        v-for="name in LEGAL_DOCS"
        :key="name"
        :to="{ name: 'legal', params: { doc: name } }"
        class="lg-tab"
        :aria-current="name === key ? 'page' : undefined"
      >
        {{ $t(`legal.docs.${name}`) }}
      </RouterLink>
    </nav>

    <article v-if="doc" class="lg-doc">
      <h1>{{ doc.title }}</h1>
      <p class="lg-updated">{{ $t('legal.updated', { date: updated }) }}</p>
      <p class="lg-intro">{{ doc.intro }}</p>

      <section v-for="(s, i) in doc.sections" :key="i">
        <h2>{{ s.h }}</h2>
        <ul v-if="s.list">
          <li v-for="(item, j) in s.list" :key="j">{{ item }}</li>
        </ul>
        <p v-for="(para, j) in s.p || []" :key="`p${j}`">{{ para }}</p>
      </section>

      <section id="contact">
        <h2>{{ $t('legal.contact') }}</h2>
        <dl v-if="hasOperator" class="lg-dl">
          <div><dt>{{ $t('legal.service') }}</dt><dd>{{ BUSINESS.brand }}</dd></div>
          <div v-if="BUSINESS.operator"><dt>{{ $t('legal.operator') }}</dt><dd>{{ BUSINESS.operator }}</dd></div>
          <div v-if="BUSINESS.regNo"><dt>{{ $t('legal.regNo') }}</dt><dd>{{ BUSINESS.regNo }}</dd></div>
          <div v-if="BUSINESS.address"><dt>{{ $t('legal.address') }}</dt><dd>{{ BUSINESS.address }}</dd></div>
          <div v-if="BUSINESS.email">
            <dt>{{ $t('legal.email') }}</dt>
            <dd><a :href="`mailto:${BUSINESS.email}`">{{ BUSINESS.email }}</a></dd>
          </div>
        </dl>
        <p>{{ $t('legal.inApp') }}</p>
      </section>
    </article>
  </main>
</template>

<style scoped>
.lg-page {
  max-width: 46rem;
  margin: 0 auto;
  padding: 7rem 1.25rem 4rem;
}
.lg-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.lg-tab {
  display: inline-flex;
  align-items: center;
  min-height: 2.5rem;
  padding: 0 0.9rem;
  border-radius: 99px;
  border: 1px solid var(--border);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted);
  transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;
}
.lg-tab:hover {
  color: var(--text);
}
.lg-tab[aria-current='page'] {
  border-color: var(--brand-600);
  background: var(--brand-600);
  color: #fff;
}
.lg-tab:focus-visible {
  outline: 2px solid var(--brand-500);
  outline-offset: 2px;
}
.lg-doc {
  margin-top: 2.5rem;
  color: var(--text);
}
.lg-doc h1 {
  font-size: clamp(1.8rem, 4vw, 2.4rem);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.15;
}
.lg-updated {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-muted);
}
.lg-intro {
  margin-top: 1.5rem;
  font-size: 1.05rem;
  line-height: 1.65;
}
.lg-doc section {
  margin-top: 2.2rem;
}
.lg-doc h2 {
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: -0.01em;
}
.lg-doc section p,
.lg-doc section li {
  margin-top: 0.7rem;
  font-size: 0.97rem;
  line-height: 1.7;
  color: var(--text);
}
.lg-doc ul {
  padding-left: 1.2rem;
  list-style: disc;
}
.lg-doc ul li::marker {
  color: var(--brand-500);
}
.lg-dl {
  margin-top: 0.8rem;
  display: grid;
  gap: 0.5rem;
  font-size: 0.95rem;
}
.lg-dl div {
  display: grid;
  grid-template-columns: minmax(8rem, auto) 1fr;
  gap: 1rem;
}
.lg-dl dt {
  color: var(--text-muted);
}
.lg-doc a {
  color: var(--brand-600);
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
