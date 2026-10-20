"""
Sign in with Google (OAuth 2.0 authorization code flow with PKCE).

    GET /api/auth/google/start?origin=…&next=…&device=…
        Remembers a random state and a PKCE verifier in a short-lived signed
        cookie, then sends the browser to Google's consent screen.
    GET /api/auth/google/callback?code=…&state=…
        Checks the state, trades the code for Google's ID token, finds or
        creates the account (_account_for: by Google account, then by email,
        so a password account with the same address is the same account),
        opens a session (the same refresh cookie a password sign-in sets) and
        sends the browser back to the app: new accounts to the questionnaire,
        everyone else to ``next``.

No Google script runs on our pages, so the site's CSP stays 'self'-only. The
ID token comes straight from Google's token endpoint over TLS, which OpenID
Connect accepts in place of checking its signature; its issuer, audience,
expiry and email_verified are still checked.

The redirect URI is the page's own origin plus /api/auth/google/callback, and
only origins in GOOGLE_ALLOWED_ORIGINS are accepted. Each one must also be
listed under "Authorized redirect URIs" in the Google Cloud console.
"""
import base64
import hashlib
import json
import logging
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core import signing
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.http import require_GET

from . import security, sessions
from .models import SecurityEvent, User
from .views import _issue_session, _set_refresh_cookie

log = logging.getLogger("accounts.security")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")
COOKIE = "g_oauth"
COOKIE_PATH = "/api/auth/google"
SALT = "accounts.google"
MAX_AGE = 600  # the round trip through Google's screens, in seconds


def configured():
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def _allowed_origin(origin):
    origin = (origin or "").rstrip("/")
    return origin if origin in settings.GOOGLE_ALLOWED_ORIGINS else settings.APP_ORIGIN


def _safe_next(value):
    # Only a path inside the app: never "//host" or "/\\host".
    value = str(value or "")
    return value if value.startswith("/") and not value.startswith(("//", "/\\")) else ""


def _back(origin, path, **query):
    qs = f"?{urllib.parse.urlencode(query)}" if query else ""
    return HttpResponseRedirect(f"{origin}{path}{qs}")


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@require_GET
def start(request):
    origin = _allowed_origin(request.GET.get("origin"))
    if not configured():
        return _back(origin, "/login", google="unavailable")

    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    redirect_uri = f"{origin}/api/auth/google/callback"
    query = urllib.parse.urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()),
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    response = HttpResponseRedirect(f"{AUTH_URL}?{query}")
    remembered = {
        "s": state,
        "v": verifier,
        "o": origin,
        "n": _safe_next(request.GET.get("next")),
        "d": str(request.GET.get("device") or "")[:255],
    }
    response.set_cookie(
        COOKIE,
        signing.dumps(remembered, salt=SALT),
        max_age=MAX_AGE,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="Lax",  # must come back on the top-level GET from Google
        path=COOKIE_PATH,
    )
    return response


def _exchange(code, verifier, redirect_uri):
    """Trade the authorization code for Google's tokens. Returns the claims or None."""
    body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }
    ).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:  # noqa: S310 — fixed https URL
            tokens = json.loads(res.read().decode())
    except (urllib.error.URLError, ValueError, TimeoutError) as exc:
        log.warning("google token exchange failed: %s", exc)
        return None
    id_token = tokens.get("id_token") or ""
    try:
        payload = id_token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError):
        return None
    if claims.get("iss") not in ISSUERS or claims.get("aud") != settings.GOOGLE_CLIENT_ID:
        return None
    if int(claims.get("exp") or 0) < time.time() or not claims.get("email_verified"):
        return None
    return claims


def _account_for(sub, email, claims):
    """
    One Zinvest account per person, however they sign in.

    Found by the Google account first (its id survives a change of address),
    then by email: someone who signed up with test@gmail.com and a password and
    later presses "Continue with Google" with the same address lands in that
    same account, which is linked to Google from then on.

    Returns (user | "conflict" | "closed" | None, created, linked, password_reset).
    """
    user = User.objects.filter(google_sub=sub).first()
    if user is not None:
        return user, False, False, False

    user = User.objects.filter(email__iexact=email).first()
    if user is not None:
        if user.google_sub:
            # The address is already tied to a different Google account.
            return "conflict", False, False, False
        reset = False
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user.pk)
            user.google_sub = sub
            fields = ["google_sub"]
            if user.email_verified_at is None:
                # Nobody had proven this mailbox until now. If a password was
                # set without that proof it may not be the owner's (anyone can
                # type someone else's address into a sign-up form), so the
                # owner, proven by Google, gets the account without it: the
                # password goes and so does every session it opened. A new one
                # is a "Forgot password?" away.
                user.email_verified_at = timezone.now()
                fields.append("email_verified_at")
                if user.has_usable_password():
                    user.set_unusable_password()
                    fields.append("password")
                    reset = True
            user.save(update_fields=fields)
            if reset:
                sessions.sign_out(user)  # whoever set that password, and any Telegram chat they linked
        return user, False, True, reset

    from adminpanel.models import PlatformSettings  # the admin panel can pause sign-ups

    if not PlatformSettings.current().registration_open:
        return "closed", False, False, False
    try:
        with transaction.atomic():
            user = User(
                email=email,
                first_name=str(claims.get("given_name") or "")[:150],
                last_name=str(claims.get("family_name") or "")[:150],
                email_verified_at=timezone.now(),
                google_sub=sub,
                # The Google button sits under the line saying that continuing
                # accepts the Terms and confirms the age rule.
                terms_accepted_at=timezone.now(),
                age_confirmed=True,
            )
            user.set_unusable_password()  # sign-in is through Google until a password is set
            user.save()
        return user, True, True, False
    except IntegrityError:
        # The same person finishing two sign-ins at once: take the account that won.
        return User.objects.filter(google_sub=sub).first(), False, False, False


@require_GET
def callback(request):
    try:
        remembered = signing.loads(request.COOKIES.get(COOKIE, ""), salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature:
        return _back(settings.APP_ORIGIN, "/login", google="expired")
    origin = _allowed_origin(remembered.get("o"))

    def fail(reason):
        response = _back(origin, "/login", google=reason)
        response.delete_cookie(COOKIE, path=COOKIE_PATH)
        return response

    if request.GET.get("error"):
        return fail("cancelled")
    state = request.GET.get("state") or ""
    if not secrets.compare_digest(state.encode(), str(remembered.get("s", "")).encode()):  # bytes: non-ASCII input must not 500
        return fail("expired")

    claims = _exchange(request.GET.get("code") or "", remembered["v"], f"{origin}/api/auth/google/callback")
    if claims is None:
        return fail("failed")
    email = str(claims.get("email") or "").strip().lower()
    sub = str(claims.get("sub") or "")[:64]
    if not email or not sub:
        return fail("failed")

    user, created, linked, reset = _account_for(sub, email, claims)
    if user == "conflict":
        return fail("conflict")
    if user == "closed":
        return fail("closed")
    if user is None or not user.is_active:
        return fail("disabled")

    security.record(
        SecurityEvent.Kind.GOOGLE_SIGNIN, request, user=user, created=created, linked=linked, password_reset=reset
    )
    raw_refresh, _family = _issue_session(user, request, device_id=remembered.get("d", ""))
    target = "/onboarding" if created else (remembered.get("n") or "/app")
    response = _back(origin, target, **({"welcome": "google"} if created else {}))
    _set_refresh_cookie(response, raw_refresh)
    response.delete_cookie(COOKIE, path=COOKIE_PATH)
    return response
