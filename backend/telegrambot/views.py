"""
Two doors into the bot:

  POST /api/telegram/webhook/   Telegram calls this (secret header required)
  POST /api/telegram/link       the app asks for a code to pair a chat
  GET  /api/telegram/link       is this account linked, and to whom
  DELETE /api/telegram/link     unlink from the app side
"""
import json
import logging
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts import security
from accounts.auth import require_auth

from . import api, handlers
from .models import TelegramLink, TelegramLinkCode

log = logging.getLogger("telegrambot")

CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_TTL_MINUTES = 15


@csrf_exempt
@require_POST
def webhook(request):
    """
    Telegram's updates. Two gates before anything is parsed: the shared secret
    header Telegram echoes for us, and a size cap — an update is a small JSON.
    """
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        return HttpResponse(status=404)  # webhook not configured: pretend it isn't there
    given = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not secrets.compare_digest(given.encode(), settings.TELEGRAM_WEBHOOK_SECRET.encode()):  # bytes: a non-ASCII header must not 500
        log.warning("telegram webhook called without the secret from %s", security.client_ip(request))
        return HttpResponse(status=403)
    if len(request.body or b"") > 200_000:
        return HttpResponse(status=413)
    try:
        update = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponse(status=400)
    if isinstance(update, dict):
        handlers.handle_update(update)
    # Always 200: a non-200 makes Telegram retry the same update for hours.
    return HttpResponse(status=200)


def _new_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


def _state(user):
    link = TelegramLink.objects.filter(user=user).first()
    return {
        "enabled": api.enabled(),
        "bot": settings.TELEGRAM_BOT_USERNAME,
        "linked": link is not None,
        "chat": {
            "username": link.username,
            "first_name": link.first_name,
            "nudges": link.nudges,
            "nudge_hour": link.nudge_hour,
            "linked_at": link.created_at.isoformat(),
        } if link else None,
    }


@csrf_exempt
@require_auth
def link(request):
    """GET the state, POST for a fresh pairing code, DELETE to unlink."""
    user = request.auth_user

    if request.method == "GET":
        return JsonResponse(_state(user))

    if request.method == "DELETE":
        TelegramLink.objects.filter(user=user).delete()
        return JsonResponse(_state(user))

    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    if not api.enabled():
        return JsonResponse({"detail": "The Telegram bot is not configured.", "code": "telegram_off"}, status=503)
    if not security.hit("tg-code", user.pk, 5, 600):
        return JsonResponse({"detail": "Too many attempts. Please try again later.", "code": "rate_limited"}, status=429)

    # One live code per account: asking again replaces the old one.
    TelegramLinkCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    code = _new_code()
    row = TelegramLinkCode.objects.create(
        user=user, code=code, expires_at=timezone.now() + timedelta(minutes=CODE_TTL_MINUTES)
    )
    return JsonResponse({
        **_state(user),
        "code": code,
        "expires_at": row.expires_at.isoformat(),
        "deep_link": f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={code}",
    })
