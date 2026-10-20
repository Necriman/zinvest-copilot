<script setup>
import { reactive, ref, watch } from 'vue'
import BlockCard from './BlockCard.vue'
import Icon from '@/components/ui/Icon.vue'
import { updateStartupProfile } from '@/api/startup'
const props=defineProps({profile:Object,kind:String})
const emit=defineEmits(['saved'])
const form=reactive({operating_mode:'online',locations:[],demand:{}})
const busy=ref(false),error=ref(''),saved=ref(false)
watch(()=>props.profile,p=>{const now=new Date();const today=[now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),String(now.getDate()).padStart(2,'0')].join('-');form.operating_mode=p?.operating_mode||'online';form.locations=JSON.parse(JSON.stringify(p?.locations||[]));form.demand={level:'moderate',evidence:'',observed_on:today,inquiries:0,orders:0,...p?.demand}},{immediate:true})
async function save(){busy.value=true;error.value='';saved.value=false;try{const res=await updateStartupProfile(props.kind==='demand'?{demand:form.demand}:{operating_mode:form.operating_mode,locations:form.locations});emit('saved',res);saved.value=true}catch(e){error.value=e?.response?.data?.detail||e.message}finally{busy.value=false}}
</script>
<template>
  <BlockCard :icon="kind==='demand'?'trending':'map'" :title="$t(`business.${kind}`)" :subtitle="$t(`business.${kind}Hint`)">
    <form class="space-y-4 text-sm" @submit.prevent="save">
      <template v-if="kind==='demand'">
        <p v-if="!profile.demand?.level" class="rounded-xl bg-slate-50 p-3 text-slate-500 dark:bg-surface-2">{{ $t('business.noDemand') }}</p>
        <label class="block">{{ $t('business.demandLevel') }}<select v-model="form.demand.level" class="zx-input mt-1 w-full"><option v-for="level in ['none','low','moderate','high','excess']" :value="level" :key="level">{{ $t(`business.${level}`) }}</option></select></label>
        <div class="grid grid-cols-2 gap-3"><label>{{ $t('business.inquiries') }}<input v-model.number="form.demand.inquiries" type="number" min="0" step="1" required class="zx-input mt-1 w-full" /></label><label>{{ $t('business.orders') }}<input v-model.number="form.demand.orders" type="number" min="0" step="1" required class="zx-input mt-1 w-full" /></label></div>
        <label class="block">{{ $t('business.observed') }}<input v-model="form.demand.observed_on" type="date" required class="zx-input mt-1 w-full" /></label>
        <label class="block">{{ $t('business.evidence') }}<textarea v-model="form.demand.evidence" rows="3" maxlength="5000" required class="zx-input mt-1 w-full" /></label>
      </template>
      <template v-else>
        <label class="block">{{ $t('business.mode') }}<select v-model="form.operating_mode" class="zx-input mt-1 w-full"><option v-for="m in ['online','offline','hybrid']" :key="m" :value="m">{{ $t(`business.${m}`) }}</option></select></label>
        <div v-for="(location,index) in form.locations" :key="index" class="space-y-2 rounded-xl bg-slate-50 p-3 dark:bg-surface-2">
          <label class="block">{{ $t('business.country') }}<input v-model="location.country" required maxlength="240" class="zx-input mt-1 w-full" /></label>
          <template v-if="form.operating_mode!=='online'"><label class="block">{{ $t('business.region') }}<input v-model="location.region" maxlength="240" class="zx-input mt-1 w-full" /></label><label class="block">{{ $t('business.address') }}<input v-model="location.address" required maxlength="240" class="zx-input mt-1 w-full" /></label></template>
          <button type="button" class="min-h-11 text-red-600" @click="form.locations.splice(index,1)">{{ $t('common.delete') }}</button>
        </div>
        <button type="button" class="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-dashed border-hairline font-semibold text-brand-600 transition hover:bg-brand-50 dark:text-brand-300 dark:hover:bg-brand-500/10" @click="form.locations.push({country:'',region:'',address:''})"><Icon name="plus" class="h-4 w-4" /> {{ $t('business.addLocation') }}</button>
      </template>
      <p v-if="error" role="alert" class="text-red-600">{{ error }}</p><p v-if="saved" role="status" class="text-emerald-700 dark:text-emerald-400">{{ $t('business.saved') }}</p>
      <button :disabled="busy" class="min-h-11 rounded-xl bg-brand-600 px-5 font-semibold text-white disabled:opacity-50">{{ $t('common.save') }}</button>
    </form>
  </BlockCard>
</template>
