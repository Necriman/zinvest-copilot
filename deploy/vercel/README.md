# Zinvest on Vercel + Supabase

One Vercel project (`zinvest`) serves both halves:

- the SPA, built by Vercel from the frontend;
- the Django backend as one Python function (`api/index.py`), which answers
  `/api/*`, `/media/*` and the Django admin (`/admin/`).

Supabase provides Postgres. Django keeps everything there: its tables (in the
`zinvest` schema, which Supabase's REST API does not expose), the cache
(`CACHE_BACKEND=db`) and uploaded files and voice clips (`MEDIA_STORAGE=db`,
the `files` app). Vercel functions have no disk that outlives a request.

## Environment (Vercel project, Production)

| Name | Value |
| --- | --- |
| `DATABASE_URL` | `postgresql://zinvest_app.<project-ref>:<password>@<pooler-host>:6543/postgres` (transaction pooler) |
| `DEBUG` | `0` |
| `SECRET_KEY`, `JWT_SIGNING_KEY`, `TOTP_ENCRYPTION_KEY` | random, different from each other |
| `ALLOWED_HOSTS` | `.vercel.app` (plus a custom domain, if any) |
| `APP_ORIGIN`, `CSRF_TRUSTED_ORIGINS` | `https://zinvest-kappa.vercel.app` |
| `TRUSTED_PROXIES` | `0.0.0.0/0,::/0` (Vercel's edge overwrites X-Real-IP / X-Forwarded-For) |
| `CACHE_BACKEND` | `db` |
| `MEDIA_STORAGE` | `db` |
| `CRON_SECRET` | random; Vercel Cron and pg_cron send it as a bearer token |
| `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET` | the AI and the bot |

The local copy of these lives in `backend/.env.production` (never bundled).

## Database (once, in the Supabase SQL editor)

```sql
create schema if not exists zinvest;
create role zinvest_app login password '<password>';
grant usage, create on schema zinvest to zinvest_app;
alter role zinvest_app set search_path = zinvest;
```

Then, from this machine, with `DATABASE_URL` pointing at the **session**
pooler (port 5432) for the long-running commands:

```bash
cd backend
python manage.py migrate
python manage.py createcachetable
python manage.py seed_learning && python manage.py seed_daily && python manage.py seed_market
```

## Scheduled jobs

`config/cron.py` runs them over HTTP (`/api/cron/<job>`, bearer `CRON_SECRET`):

- `cleanup` daily and `league` on Mondays: Vercel Cron (`crons` in vercel.json);
- `nudges` hourly: Vercel's free plan runs crons once a day at most, so the
  database calls it:

```sql
create extension if not exists pg_cron;
create extension if not exists pg_net;
select cron.schedule('zinvest-nudges', '0 * * * *', $$
  select net.http_get(
    url := 'https://zinvest-kappa.vercel.app/api/cron/nudges',
    headers := jsonb_build_object('Authorization', 'Bearer <CRON_SECRET>'),
    timeout_milliseconds := 60000)
$$);
```

## Deploy

```bash
cd backend && python manage.py collectstatic --noinput && cd ..
python deploy/vercel/bundle.py <out-dir>
cd <out-dir> && CI=1 vercel deploy --prod
```

Then point the bot at the new backend (from `backend/`, with the production
environment loaded):

```bash
python manage.py telegram_webhook --set https://zinvest-kappa.vercel.app/api/telegram/webhook
python manage.py telegram_setup
```
