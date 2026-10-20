<script setup>
/**
 * Plain data table for admin lists. Cells render `row[col.key]` unless a
 * `#cell-<key>="{ row }"` slot says otherwise. Rows are clickable when the
 * parent listens for `open`; the whole row is a button for keyboards too.
 *
 *   <AdminTable :columns="[{ key: 'email', label: 'Email' }]" :rows="rows" @open="go" />
 */
import LoadingSkeleton from '@/components/ui/LoadingSkeleton.vue'

defineProps({
  columns: { type: Array, required: true }, // [{ key, label, class?, align? }]
  rows: { type: Array, default: () => [] },
  rowKey: { type: String, default: 'id' },
  loading: { type: Boolean, default: false },
  clickable: { type: Boolean, default: false },
  empty: { type: String, default: '' },
})
const emit = defineEmits(['open'])

function onKey(e, row) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    emit('open', row)
  }
}
</script>

<template>
  <div class="card overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full min-w-[640px] border-collapse text-left text-sm">
        <thead>
          <tr class="border-b border-slate-200 bg-slate-50/70 dark:border-hairline dark:bg-surface-2/40">
            <th
              v-for="col in columns"
              :key="col.key"
              scope="col"
              class="whitespace-nowrap px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-400"
              :class="[col.align === 'right' ? 'text-right' : '', col.class]"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading && !rows.length">
            <tr v-for="i in 6" :key="`s${i}`" class="border-b border-slate-100 last:border-0 dark:border-hairline/60">
              <td v-for="col in columns" :key="col.key" class="px-4 py-3.5">
                <LoadingSkeleton height="h-3.5" :width="i % 2 ? 'w-3/4' : 'w-1/2'" />
              </td>
            </tr>
          </template>
          <tr v-else-if="!rows.length">
            <td :colspan="columns.length" class="px-4 py-12 text-center text-sm text-slate-400">
              {{ empty || $t('admin.common.empty') }}
            </td>
          </tr>
          <template v-else>
            <tr
              v-for="row in rows"
              :key="row[rowKey]"
              class="border-b border-slate-100 align-middle transition-colors last:border-0 dark:border-hairline/60"
              :class="[
                clickable ? 'cursor-pointer hover:bg-slate-50 focus-visible:bg-slate-50 focus-visible:outline-none dark:hover:bg-surface-2/60 dark:focus-visible:bg-surface-2/60' : '',
                loading ? 'opacity-60' : '',
              ]"
              :tabindex="clickable ? 0 : undefined"
              @click="clickable && emit('open', row)"
              @keydown="clickable && onKey($event, row)"
            >
              <td
                v-for="col in columns"
                :key="col.key"
                class="px-4 py-3 text-slate-700 dark:text-slate-200"
                :class="[col.align === 'right' ? 'text-right tabular-nums' : '', col.class]"
              >
                <slot :name="`cell-${col.key}`" :row="row">{{ row[col.key] }}</slot>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>
