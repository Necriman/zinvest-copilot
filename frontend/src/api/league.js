// The weekly league: one group of learners, points earned this week.
import http from '@/api/http'

export const getLeague = () => http.get('/learning/league').then((r) => r.data)
