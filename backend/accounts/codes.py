"""
Six-digit codes mailed to finish a sign-in or a sign-up.

The flow
    POST /api/auth/login or /api/auth/register checks the details and, instead
    of opening a session, mails a code and answers with a ``challenge`` id.
    POST /api/auth/code/verify with that id and the code opens the session
    (and, for a sign-up, creates the account first). POST /api/auth/code/resend
    mails a fresh code after a short cooldown.

What keeps it honest
    - The code is stored only as an HMAC of (challenge id, code) under the
      SECRET_KEY, so a database dump does not hand out working codes.
    - A challenge dies after ``MAX_ATTEMPTS`` wrong codes or ``CODE_TTL``.
    - Letters per address and verify calls per IP are rate limited.
    - Signing up with an address that already has an account gets a decoy
      challenge (a code that can never match) and a letter telling the owner,
      so the form answers the same way for new and taken addresses.
"""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone

from . import mail, security
from .models import LoginCode

CODE_TTL = timedelta(minutes=settings.LOGIN_CODE_TTL_MINUTES)
MAX_ATTEMPTS = 5
RESEND_AFTER = timedelta(seconds=45)
MAX_SENDS = 5


def new_code():
    return f"{secrets.randbelow(10**6):06d}"


def digest(challenge_id, code):
    message = f"{challenge_id}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def matches(row, code):
    code = "".join(ch for ch in str(code or "") if ch.isdigit())
    return len(code) == 6 and hmac.compare_digest(row.code_hash, digest(row.id, code))


def mail_allowed(email):
    """At most LOGIN_CODE_MAX_PER_EMAIL_HOUR letters to one address per hour."""
    return security.hit("code-mail", email, settings.LOGIN_CODE_MAX_PER_EMAIL_HOUR, 3600)


def _mail(row, code, lang):
    if row.payload.get("decoy"):
        mail.send_account_exists(row.email, f"{settings.APP_ORIGIN}/login", lang)
    else:
        mail.send_code(row.email, code, row.purpose, lang, minutes=int(CODE_TTL.total_seconds() // 60))


def start(purpose, email, request, *, user=None, payload=None, lang=None):
    """Create a challenge, mail its code, and return the row."""
    code = new_code()
    row = LoginCode(
        purpose=purpose,
        email=email,
        user=user,
        payload=payload or {},
        expires_at=timezone.now() + CODE_TTL,
        ip_address=security.client_ip(request),
    )
    # A decoy gets a hash of nothing anyone was sent: it can never match.
    row.code_hash = digest(row.id, secrets.token_hex(16) if row.payload.get("decoy") else code)
    row.save()
    _mail(row, code, lang)
    return row


def resend(row, lang=None):
    """Mail a fresh code for ``row``. Returns None, or an error JsonResponse."""
    now = timezone.now()
    wait = RESEND_AFTER - (now - row.sent_at)
    if wait.total_seconds() > 0:
        return JsonResponse(
            {"detail": "Please wait before asking for another code.", "code": "code_cooldown",
             "resend_in": int(wait.total_seconds()) + 1},
            status=429,
        )
    if row.sends >= MAX_SENDS or not mail_allowed(row.email):
        return JsonResponse({"detail": "Too many codes for this address. Try again later.", "code": "rate_limited"}, status=429)
    code = new_code()
    row.code_hash = digest(row.id, secrets.token_hex(16) if row.payload.get("decoy") else code)
    row.attempts = 0
    row.sends += 1
    row.sent_at = now
    row.expires_at = now + CODE_TTL
    row.save(update_fields=["code_hash", "attempts", "sends", "sent_at", "expires_at"])
    _mail(row, code, lang)
    return None


def mask(email):
    """a***@gmail.com: enough to recognise your own address, not to read it off."""
    name, _, domain = email.partition("@")
    return f"{name[:1]}{'*' * max(2, min(len(name) - 1, 6))}@{domain}"


def challenge_response(row, status=200):
    return JsonResponse(
        {
            "detail": "We sent a code to your email.",
            "code_required": True,
            "challenge": str(row.id),
            "purpose": row.purpose,
            "email": mask(row.email),
            "expires_in": int(CODE_TTL.total_seconds()),
            "resend_in": int(RESEND_AFTER.total_seconds()),
            "code_length": 6,
        },
        status=status,
    )
