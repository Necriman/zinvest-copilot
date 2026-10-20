<script setup>
/**
 * Products block: the founder's catalogue of products / services / subscriptions.
 * Name (with an optional image) on the left, price on the right — so prices can
 * be scanned and compared at a glance.
 */
import { computed, reactive, ref } from 'vue'
import i18n from '@/i18n'

import Icon from '@/components/ui/Icon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import BlockCard from './BlockCard.vue'
import BulkImport from './BulkImport.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import {
  createProduct,
  importProducts,
  deleteProduct,
  listProducts,
  updateProduct,
  uploadProductImage,
} from '@/api/startup'
import { money } from '@/utils/format'

const { data, reload } = useAsyncData(listProducts)
const products = computed(() => data.value?.products || [])

const adding = ref(false)
const form = reactive({ name: '', price: '', kind:'product' })
const busy = ref(false)
const error = ref('')

async function save() {
  if (!form.name.trim() || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await createProduct({ name: form.name, price: form.price || 0, kind:form.kind })
    form.name = ''
    form.price = ''
    form.kind = 'product'
    adding.value = false
    await reload()
  } catch (e) {
    error.value = e?.response?.data?.detail || i18n.global.t('misc.saveFailed')
  } finally {
    busy.value = false
  }
}

async function remove(id) {
  try{await deleteProduct(id);await reload()}catch(e){error.value=e?.response?.data?.detail||e.message}
}

async function onPriceBlur(prod, value) {
  const next = value === '' ? '0' : value
  if (next === prod.price) return
  try{await updateProduct(prod.id, { price: next });await reload()}catch(e){error.value=e?.response?.data?.detail||e.message}
}

const fileInput = ref(null)
const uploadingFor = ref(null)

function pickImage(id) {
  uploadingFor.value = id
  fileInput.value?.click()
}

async function onFile(e) {
  const file = e.target.files?.[0]
  const id = uploadingFor.value
  e.target.value = ''
  if (!file || !id) return
  try {
    await uploadProductImage(id, file)
    await reload()
  } catch (err) {
    error.value = err?.response?.data?.detail || i18n.global.t('misc.uploadFailed')
  } finally {
    uploadingFor.value = null
  }
}
</script>

<template>
  <BlockCard
    icon="store"
    iconColor="text-amber-600"
    iconBg="bg-amber-50 dark:bg-amber-500/15"
    :title="$t('startup.products.title')"
    :subtitle="$t('startup.products.subtitle')"
  >
    <template #action>
      <div class="flex items-center gap-1">
      <BulkImport kind="products" :importer="importProducts" @imported="reload" />
      <button
        type="button"
        class="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-sm font-semibold text-brand-600 transition hover:bg-brand-50 dark:hover:bg-brand-500/10"
        @click="adding = !adding"
      >
        <Icon :name="adding ? 'x' : 'plus'" class="h-4 w-4" />
        {{ adding ? $t('common.cancel') : $t('startup.products.add') }}
      </button>
      </div>
    </template>

    <div id="import-slot-products" />

    <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFile" />

    <form v-if="adding" class="mb-4 flex flex-wrap items-center gap-2 rounded-2xl bg-slate-50 p-3 dark:bg-surface-2" @submit.prevent="save">
      <label class="block w-full text-sm">{{ $t('business.kind') }}<select v-model="form.kind" class="zx-input mt-1 w-full"><option v-for="kind in ['product','service','subscription']" :key="kind" :value="kind">{{ $t(`business.${kind}`) }}</option></select></label>
      <input v-model="form.name" :placeholder="$t('startup.products.namePlaceholder')" class="zx-input min-w-0 flex-1 py-2" />
      <input v-model="form.price" type="number" min="0" step="0.01" :placeholder="$t('startup.products.pricePlaceholder')" class="zx-input w-28 py-2" />
      <button type="submit" :disabled="busy || !form.name.trim()" class="pill shrink-0 bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40">
        {{ $t('common.save') }}
      </button>
    </form>

    <EmptyState v-if="!products.length" bear="coin" :message="$t('startup.products.empty')" />

    <ul v-else class="space-y-2.5">
      <li v-for="prod in products" :key="prod.id" class="group flex items-center gap-3">
        <button
          type="button"
          class="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-slate-100 text-slate-400 dark:bg-surface-2"
          :title="$t('startup.products.changeImage')"
          @click="pickImage(prod.id)"
        >
          <img v-if="prod.image_url" :src="prod.image_url" :alt="prod.name" class="h-full w-full object-cover" />
          <Icon v-else name="image" class="h-4 w-4" />
        </button>
        <div class="min-w-0 flex-1"><p class="truncate font-medium text-slate-800 dark:text-ink">{{ prod.name }}</p><p class="text-xs text-slate-500">{{ $t(`business.${prod.kind||'product'}`) }}</p></div>
        <div class="flex shrink-0 items-center gap-1">
          <div class="flex items-center rounded-lg border border-slate-200 px-2 dark:border-hairline">
            <input
              :value="prod.price"
              type="number"
              min="0"
              step="0.01"
              class="w-24 border-0 bg-transparent px-1 py-1 text-right text-sm font-bold text-slate-800 focus:outline-none dark:text-ink"
              @blur="onPriceBlur(prod, $event.target.value)"
              @keydown.enter="$event.target.blur()"
            />
          </div>
          <button type="button" class="rounded-lg p-1.5 text-slate-300 opacity-0 transition hover:bg-slate-100 hover:text-red-500 group-hover:opacity-100 dark:hover:bg-surface-2" :title="$t('common.delete')" @click="remove(prod.id)">
            <Icon name="trash" class="h-3.5 w-3.5" />
          </button>
        </div>
      </li>
    </ul>

    <p v-if="error" class="mt-2 text-xs text-red-500">{{ error }}</p>
  </BlockCard>
</template>
