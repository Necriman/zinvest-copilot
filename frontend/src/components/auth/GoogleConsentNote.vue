<script setup>
// Under the Google button: Google can create an account in one click, so the
// same consent the sign-up form asks for is stated here before the click.
</script>

<template>
  <i18n-t keypath="auth.consent.google" tag="p" class="gcn" scope="global">
    <template #terms>
      <RouterLink :to="{ name: 'legal', params: { doc: 'terms' } }" target="_blank">{{ $t('auth.consent.termsLink') }}</RouterLink>
    </template>
    <template #privacy>
      <RouterLink :to="{ name: 'legal', params: { doc: 'privacy' } }" target="_blank">{{ $t('auth.consent.privacyLink') }}</RouterLink>
    </template>
  </i18n-t>
</template>

<style scoped>
.gcn {
  margin-top: 0.6rem;
  text-align: center;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--text-muted);
}
.gcn a {
  color: var(--brand-600);
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
