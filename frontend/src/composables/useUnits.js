import { listUnits } from '@/api/units'
import { useAsyncData } from './useAsyncData'

export function useUnits() {
  return useAsyncData(listUnits)
}
