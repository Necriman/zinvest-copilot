<script setup>
import { computed } from 'vue'

import UnitCard from '@/components/dashboard/UnitCard.vue'
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'
import { useUnits } from '@/composables/useUnits'

const { data, loading } = useUnits()
const units = computed(() => data.value?.units || [])
</script>

<template>
  <div>
    <h1 class="mb-6 text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
      {{ $t('nav.units') }}
    </h1>

    <div v-if="loading" class="grid gap-3 sm:grid-cols-2">
      <LoadingSkeleton v-for="n in 4" :key="n" height="h-20" rounded="rounded-3xl" />
    </div>
    <div v-else class="grid gap-3 sm:grid-cols-2">
      <UnitCard v-for="unit in units" :key="unit.id" :unit="unit" />
    </div>
  </div>
</template>
