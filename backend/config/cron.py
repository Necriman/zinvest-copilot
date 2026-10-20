"""
Scheduled jobs over HTTP, for hosts without cron (Vercel functions).

    GET /api/cron/<job>    Authorization: Bearer <CRON_SECRET>

The schedule lives with the caller (pg_cron in the database, or Vercel Cron):

    nudges    hourly            telegrambot send_nudges
    league    Monday morning    learning close_league_week
    cleanup   daily             accounts cleanup_tokens

Every job is safe to run twice. Without CRON_SECRET the endpoint answers 404.
"""
import hmac
import io

from django.conf import settings
from django.core.management import call_command
from django.http import Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt

JOBS = {
    "nudges": "send_nudges",
    "league": "close_league_week",
    "cleanup": "cleanup_tokens",
}


@csrf_exempt
def run(request, job):
    secret = settings.CRON_SECRET
    given = request.headers.get("Authorization", "")
    if not secret or not hmac.compare_digest(given.encode(), f"Bearer {secret}".encode()):
        raise Http404
    if request.method not in ("GET", "POST") or job not in JOBS:
        raise Http404
    out = io.StringIO()
    call_command(JOBS[job], stdout=out, stderr=out)
    return JsonResponse({"job": job, "output": out.getvalue()[-2000:]})
