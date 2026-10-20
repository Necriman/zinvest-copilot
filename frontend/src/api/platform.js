// What the Zinvest team pushes to learners (announcements, the maintenance
// note) and what learners send back (reports about posts, founders, messages).
import http from './http'

export const getAnnouncements = () => http.get('/announcements').then((r) => r.data)

/** { target_type: 'post' | 'user' | 'message', target_id, reason, comment } */
export const sendReport = (payload) => http.post('/reports', payload).then((r) => r.data)
