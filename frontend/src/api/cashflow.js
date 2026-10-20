// Cash-flow entries + derived totals.
import http from '@/api/http'

export function listCashFlow(params = {}) {
  return http.get('/startup/cashflow', { params }).then((r) => r.data)
}

export function addCashFlow(entry) {
  return http.post('/startup/cashflow', entry).then((r) => r.data)
}

export function deleteCashFlow(id) {
  return http.delete(`/startup/cashflow/${id}`).then((r) => r.data)
}
