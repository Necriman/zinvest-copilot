<script setup>
// The Zinvest logo tile. Size and corner radius come from the caller's class.
import { MARK_PATHS, MARK_STROKE, MARK_VIEWBOX } from './brandMark'
</script>

<template>
  <span class="flex shrink-0 items-center justify-center bg-brand-600 text-white" aria-hidden="true">
    <svg :viewBox="MARK_VIEWBOX" class="h-[64%] w-[64%]" fill="none" stroke="currentColor" :stroke-width="MARK_STROKE" stroke-linecap="round" stroke-linejoin="round">
      <path v-for="d in MARK_PATHS" :key="d" :d="d" />
    </svg>
  </span>
</template>
