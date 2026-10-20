// Zinvest Copilot — the AI does the finance work, the owner approves it.
// Every AI call returns a proposal ({action}) that changes nothing until
// decideAction(id, 'approve'); the history lists all of them.
import http from '@/api/http'

export const getCopilotState = () => http.get('/copilot/state').then((r) => r.data)
export const saveCopilotSettings = (payload) => http.put('/copilot/settings', payload).then((r) => r.data)
export const readEntries = (text, language) => http.post('/copilot/entries', { text, language }).then((r) => r.data)
export const runAnalysis = (language) => http.post('/copilot/analysis', { language }).then((r) => r.data)
export const runRunway = (language) => http.post('/copilot/runway', { language }).then((r) => r.data)
export const findLoan = (payload) => http.post('/copilot/loan', payload).then((r) => r.data)
export const writePlan = (language) => http.post('/copilot/plan', { language }).then((r) => r.data)
export const decideAction = (id, decision) => http.post(`/copilot/actions/${id}/decide`, { decision }).then((r) => r.data)
export const getCopilotHistory = () => http.get('/copilot/history').then((r) => r.data)
export const downloadHistoryCsv = () =>
  http.get('/copilot/history', { params: { format: 'csv' }, responseType: 'blob' }).then((r) => r.data)
