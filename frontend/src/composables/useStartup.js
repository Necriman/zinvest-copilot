import { getStartupSummary } from '@/api/startup'
import { listCashFlow } from '@/api/cashflow'
import { useAsyncData } from './useAsyncData'

export function useStartup() {
  return useAsyncData(getStartupSummary)
}

export function useCashFlow() {
  return useAsyncData(listCashFlow)
}
