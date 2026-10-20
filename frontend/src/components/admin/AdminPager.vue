<script setup>
import Icon from '@/components/ui/Icon.vue'

defineProps({
  page: { type: Number, default: 1 },
  pages: { type: Number, default: 1 },
  total: { type: Number, default: 0 },
})
const emit = defineEmits(['update:page'])
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-500">
    <span class="tabular-nums">{{ $t('admin.common.total', { n: total }) }}</span>
    <div v-if="pages > 1" class="flex items-center gap-2">
      <button
        type="button"
        class="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 text-slate-600 transition hover:bg-slate-50 disabled:opacity-40 dark:border-hairline dark:text-slate-300 dark:hover:bg-surface-2"
        :disabled="page <= 1"
        :aria-label="$t('admin.common.prev')"
        @click="emit('update:page', page - 1)"
      >
        <Icon name="chevronRight" class="h-4 w-4 rotate-180" />
      </button>
      <span class="min-w-[7rem] text-center tabular-nums">{{ $t('admin.common.page', { page, pages }) }}</span>
      <button
        type="button"
        class="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 text-slate-600 transition hover:bg-slate-50 disabled:opacity-40 dark:border-hairline dark:text-slate-300 dark:hover:bg-surface-2"
        :disabled="page >= pages"
        :aria-label="$t('admin.common.next')"
        @click="emit('update:page', page + 1)"
      >
        <Icon name="chevronRight" class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>
