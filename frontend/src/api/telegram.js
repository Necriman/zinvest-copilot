// The Telegram bot: pairing this account with a chat.
import http from '@/api/http'

export const getTelegram = () => http.get('/telegram/link').then((r) => r.data)
export const createTelegramCode = () => http.post('/telegram/link').then((r) => r.data)
export const unlinkTelegram = () => http.delete('/telegram/link').then((r) => r.data)
