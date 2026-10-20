import { getStats } from '@/api/stats'
import { useAsyncData } from './useAsyncData'

export function useStats() {
  return useAsyncData(getStats)
}
