"""
Native Django auth views (JsonResponse only — no DRF).

Endpoints:
  POST /api/auth/register   check the details and mail a code (enumeration-resistant)
  POST /api/auth/login      validate credentials and mail a code
  POST /api/auth/code/verify   the mailed code opens the session (creates the account on sign-up)
  POST /api/auth/code/resend   mail a fresh code after a short cooldown
  GET  /api/auth/google/start, /callback   sign in with Google (accounts.google)
  POST /api/auth/refresh    rotate the refresh token; family-based theft trap
  POST /api/auth/logout     revoke the current family, clear the cookie
  GET  /api/auth/me         protected; return the current user
  POST /api/auth/forgot-password  mail yourself a password link
  POST /api/auth/password-reset   set a new password with a one-time link
  POST /api/auth/verify-email     confirm an address from the mailed link
"""
import json
import logging
import re
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import codes, mail, security, throttle
from .sessions import sign_out
from .auth import extract_bearer, require_auth
from .jwt_utils import InvalidAccessToken, decode_access_token, encode_access_token
from .models import EmailVerification, LoginCode, PasswordResetToken, RefreshToken, SecurityEvent, User
from .tokens import generate_refresh_token, hash_refresh_token
from .useragent import parse_device_name

log = logging.getLogger("accounts.security")

REFRESH_COOKIE = "refresh_token"
REFRESH_PATH = "/api/auth/refresh"  # MUST equal the real URL of the refresh view


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _json_body(request):
    try:
        return json.loads(request.body or b"{}"), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"detail": "Malformed JSON body."}, status=400)


def _weak_password(error):
    """
    The one answer for a rejected password, wherever it is rejected.

    ``errors`` keeps Django's English sentences for existing clients. ``codes``
    carries the validators' own identifiers (password_too_short and friends),
    so the interface can say which rule was broken in the reader's language —
    an English "does not meet requirements" told a Russian speaker nothing.
    """
    return JsonResponse(
        {
            "detail": "Password does not meet requirements.",
            "errors": error.messages,
            "codes": [item.code for item in error.error_list if item.code],
        },
        status=400,
    )


def _client_ip(request):
    # Proxy headers are believed only from settings.TRUSTED_PROXIES (see
    # accounts.security), so a client cannot spoof its IP around the limits.
    return security.client_ip(request)


def _check_password(request, user, password):
    """
    Verify the current password for a sensitive change. Returns True, False,
    or None when too many wrong answers were given recently (a stolen access
    token must not become a way to guess the password).
    """
    if security.over("pwcheck", user.pk, settings.PASSWORD_CHECK_MAX):
        return None
    if user.check_password(password or ""):
        return True
    security.hit("pwcheck", user.pk, settings.PASSWORD_CHECK_MAX, 15 * 60)
    security.record(SecurityEvent.Kind.PASSWORD_CHECK_FAILED, request, user=user)
    return False


def _too_many_checks():
    return JsonResponse({"detail": "Too many wrong attempts. Try again in 15 minutes.", "code": "rate_limited"}, status=429)


def _sign_out_elsewhere(user, keep_family=None):
    """Revoke every other session (and a linked Telegram chat) and kill their access tokens right away."""
    return sign_out(user, keep_family=keep_family)


def _device_id(data, request):
    return (data.get("unique_device_id") or request.META.get("HTTP_X_DEVICE_ID") or "").strip()


def _set_refresh_cookie(response, raw_token):
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=raw_token,
        max_age=int(settings.REFRESH_TOKEN_TTL.total_seconds()),
        httponly=True,       # JS (and thus XSS) can never read it
        secure=settings.REFRESH_COOKIE_SECURE,   # HTTPS only (see settings)
        samesite="Strict",   # not sent cross-site -> CSRF defense
        path=REFRESH_PATH,   # only transmitted to the refresh endpoint
    )


def _clear_refresh_cookie(response):
    # A response may delete a cookie for any path regardless of request path,
    # so logout (at /api/auth/logout) can still clear the /refresh cookie.
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH, samesite="Strict")


HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")

# Magic bytes → extension. The client's filename and Content-Type are attacker-
# controlled, so the stored extension is derived from the actual bytes instead.
_IMAGE_SIGNATURES = (
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
)


def _sniff_image(header):
    """Return the extension for a recognised image header, else None."""
    for signature, ext in _IMAGE_SIGNATURES:
        if header.startswith(signature):
            return ext
    # WebP is "RIFF" + 4 size bytes + "WEBP".
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def _user_dict(u):
    return {
        "id": str(u.id),
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "avatar_url": u.avatar.url if u.avatar else None,
        "theme": u.theme,
        "brand_color": u.brand_color,
        "staff_role": u.admin_role,  # '' for learners; shows the admin panel link
        "email_verified": u.email_verified_at is not None,
        # How this account signs in: a password, Google, or both (one account
        # either way: accounts.google links by email).
        "has_password": u.has_usable_password(),
        "google_linked": bool(u.google_sub),
    }


def _token_response(access):
    return JsonResponse(
        {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": int(settings.ACCESS_TOKEN_TTL.total_seconds()),
        },
        status=200,
    )


def _issue_session(user, request, *, family_id=None, device_id=""):
    """Create ONE refresh-token row and return (raw_refresh, family_id)."""
    family_id = family_id or uuid.uuid4()
    raw = generate_refresh_token()
    RefreshToken.objects.create(
        user=user,
        token_hash=hash_refresh_token(raw),
        family_id=family_id,
        ip_address=_client_ip(request),
        device_name=parse_device_name(request.META.get("HTTP_USER_AGENT", "")),
        unique_device_id=device_id[:255],
        expires_at=timezone.now() + settings.REFRESH_TOKEN_TTL,
    )
    return raw, family_id


def _rotate_from(row, request):
    """
    Revoke ``row`` and mint its successor under the SAME family_id. Must run
    inside an open transaction with ``row`` row-locked. Returns the new raw token.
    """
    now = timezone.now()
    new_raw = generate_refresh_token()
    successor = RefreshToken.objects.create(
        user=row.user,
        token_hash=hash_refresh_token(new_raw),
        family_id=row.family_id,
        ip_address=_client_ip(request),
        device_name=parse_device_name(request.META.get("HTTP_USER_AGENT", "")),
        unique_device_id=row.unique_device_id,
        expires_at=now + settings.REFRESH_TOKEN_TTL,
    )
    row.is_revoked = True
    row.rotated_at = now
    row.replaced_by = successor
    row.save(update_fields=["is_revoked", "rotated_at", "replaced_by"])
    return new_raw


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------
@csrf_exempt
@require_POST
def register(request):
    data, err = _json_body(request)
    if err:
        return err

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()

    if not email or not password:
        return JsonResponse({"detail": "Email and password are required."}, status=400)
    if data.get("accept_terms") is not True or data.get("age_ok") is not True:
        return JsonResponse(
            {"detail": "Accept the Terms and Privacy Policy and confirm your age to sign up.", "code": "consent_required"},
            status=400,
        )

    from adminpanel.models import PlatformSettings  # the admin panel can pause sign-ups

    if not PlatformSettings.current().registration_open:
        return JsonResponse({"detail": "Sign-ups are paused right now. Please try again later.", "code": "registration_closed"}, status=503)
    ip = _client_ip(request)
    if not security.hit("register", ip, settings.REGISTER_MAX_PER_IP_HOUR, 3600):
        security.record(SecurityEvent.Kind.REGISTER_THROTTLED, request, email=email)
        return JsonResponse({"detail": "Too many sign-ups from this network. Please try again later.", "code": "rate_limited"}, status=429)

    try:
        validate_password(password)
    except ValidationError as e:
        return _weak_password(e)

    try:
        EmailValidator()(email)
    except ValidationError:
        return JsonResponse({"detail": "Enter a valid email address.", "code": "email_invalid"}, status=400)

    exists = User.objects.filter(email__iexact=email).exists()
    if settings.AUTH_REVEAL_EMAIL_EXISTS and exists:
        # Opt-in, UX-friendly (but enumerable) behaviour.
        return JsonResponse({"detail": "An account with this email already exists."}, status=409)

    if settings.LOGIN_EMAIL_CODE:
        # Nothing is created yet: the details wait for the code from the letter.
        # A taken address gets a decoy challenge and a letter to its owner, so
        # the answer is the same for new and existing addresses (review #5).
        if not codes.mail_allowed(email):
            return JsonResponse({"detail": "Too many codes for this address. Try again later.", "code": "rate_limited"}, status=429)
        payload = {"decoy": True} if exists else {
            "first_name": first_name[:150],
            "last_name": last_name[:150],
            "password": make_password(password),
            "consent_at": timezone.now().isoformat(),
        }
        row = codes.start(LoginCode.Purpose.REGISTER, email, request, payload=payload, lang=data.get("lang"))
        return codes.challenge_response(row)

    created = True
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=email, password=password, first_name=first_name, last_name=last_name,
                terms_accepted_at=timezone.now(), age_confirmed=True,
            )
    except IntegrityError:
        created = False  # email already exists

    if created:
        # Outside the transaction: a mail server hiccup must not undo the sign-up.
        _mail_verification(user, data.get("lang"))

    # Default: uniform response for both new and existing emails so the endpoint
    # is not a user-enumeration oracle (security review #5). The account is only
    # actually created when the email is new.
    return JsonResponse(
        {"detail": "If the details are valid, the account has been created. You can now sign in."},
        status=200,
    )


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------
@csrf_exempt
@require_POST
def login(request):
    data, err = _json_body(request)
    if err:
        return err

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    device_id = _device_id(data, request)
    ip = _client_ip(request)

    if not email or not password:
        return JsonResponse({"detail": "Email and password are required."}, status=400)

    if throttle.is_locked(ip, email):
        security.record(SecurityEvent.Kind.LOGIN_LOCKED, request, email=email)
        # Knocking on and on while locked out is a script: it gets this address banned (accounts.bans).
        security.hit("login-locked", ip, settings.LOGIN_MAX_ATTEMPTS * 2, 900)
        return JsonResponse(
            {"detail": "Too many failed attempts. Please try again later.", "code": "rate_limited"}, status=429
        )

    # Exactly one password hash per attempt, whether the account exists, is
    # active or is blocked (like ModelBackend.authenticate), so the response
    # time gives none of that away.
    try:
        candidate = User._default_manager.get_by_natural_key(email)
    except User.DoesNotExist:
        candidate = None
        User().set_password(password)
    right = candidate is not None and candidate.check_password(password)
    if right and not candidate.is_active:
        # Only someone who knows the password learns that the account is blocked.
        security.record(SecurityEvent.Kind.LOGIN_DISABLED, request, user=candidate)
        return JsonResponse(
            {"detail": "This account is blocked. If you think this is a mistake, write to the Zinvest team.", "code": "account_blocked"},
            status=403,
        )
    user = candidate if right else None
    if user is None:
        locked_now = throttle.record_failure(ip, email)
        security.record(
            SecurityEvent.Kind.LOGIN_LOCKED if locked_now else SecurityEvent.Kind.LOGIN_FAILED,
            request, user=User.objects.filter(email=email).first(), email=email,
        )
        return JsonResponse({"detail": "Invalid email or password."}, status=401)

    throttle.clear(ip, email)
    if settings.LOGIN_EMAIL_CODE:
        # The password was right; the code from the letter finishes the sign-in.
        if not codes.mail_allowed(user.email):
            return JsonResponse({"detail": "Too many codes for this address. Try again later.", "code": "rate_limited"}, status=429)
        row = codes.start(LoginCode.Purpose.LOGIN, user.email, request, user=user, lang=data.get("lang"))
        return codes.challenge_response(row)
    return _open_session(user, request, device_id)


def _open_session(user, request, device_id, **extra):
    """Mint the tokens for ``user``: the access token in the body, refresh in the cookie."""
    raw_refresh, family_id = _issue_session(user, request, device_id=device_id)
    access = encode_access_token(user, family_id)
    resp = JsonResponse(
        {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": int(settings.ACCESS_TOKEN_TTL.total_seconds()),
            "user": _user_dict(user),
            **extra,
        },
        status=200,
    )
    _set_refresh_cookie(resp, raw_refresh)
    return resp


# ---------------------------------------------------------------------------
# emailed codes (accounts.codes)
# ---------------------------------------------------------------------------
def _challenge(data):
    try:
        return LoginCode.objects.filter(pk=uuid.UUID(str(data.get("challenge") or ""))).first()
    except ValueError:
        return None


def _code_dead():
    return JsonResponse(
        {"detail": "This code has expired. Ask for a new one.", "code": "code_expired"}, status=400
    )


@csrf_exempt
@require_POST
def code_verify(request):
    data, err = _json_body(request)
    if err:
        return err
    ip = _client_ip(request)
    if not security.hit("code-verify", ip, settings.CODE_VERIFY_MAX_PER_IP, 900):
        return JsonResponse({"detail": "Too many attempts. Try again in 15 minutes.", "code": "rate_limited"}, status=429)

    with transaction.atomic():
        row = _challenge(data)
        if row is None:
            return _code_dead()
        row = LoginCode.objects.select_for_update().get(pk=row.pk)
        if not row.is_usable or row.attempts >= codes.MAX_ATTEMPTS:
            return _code_dead()
        if not codes.matches(row, data.get("code")):
            row.attempts += 1
            if row.attempts >= codes.MAX_ATTEMPTS:
                row.used_at = timezone.now()
            row.save(update_fields=["attempts", "used_at"])
            security.record(SecurityEvent.Kind.CODE_FAILED, request, user=row.user, email=row.email)
            left = codes.MAX_ATTEMPTS - row.attempts
            if left <= 0:
                return _code_dead()
            return JsonResponse(
                {"detail": "Wrong code.", "code": "code_invalid", "attempts_left": left}, status=400
            )
        row.used_at = timezone.now()
        row.save(update_fields=["used_at"])

        created = False
        if row.purpose == LoginCode.Purpose.LOGIN:
            user = row.user
            if user is None or not user.is_active:
                return JsonResponse({"detail": "Invalid email or password."}, status=401)
            if user.email_verified_at is None:
                # The code arrived in that mailbox, so the address is proven.
                user.email_verified_at = timezone.now()
                user.save(update_fields=["email_verified_at"])
        else:
            details = row.payload or {}
            if details.get("decoy") or not details.get("password"):
                return _code_dead()
            try:
                with transaction.atomic():
                    user = User(
                        email=row.email,
                        first_name=details.get("first_name", ""),
                        last_name=details.get("last_name", ""),
                        email_verified_at=timezone.now(),
                        terms_accepted_at=parse_datetime(details.get("consent_at") or "") or timezone.now(),
                        age_confirmed=True,
                    )
                    user.password = details["password"]  # hashed when the code was asked for
                    user.save()
            except IntegrityError:
                return JsonResponse(
                    {"detail": "An account with this email already exists. Sign in instead.", "code": "email_taken"},
                    status=409,
                )
            created = True
            # The password hash has served its purpose; do not keep a copy.
            row.payload = {}
            row.save(update_fields=["payload"])

    return _open_session(user, request, _device_id(data, request), created=created)


@csrf_exempt
@require_POST
def code_resend(request):
    data, err = _json_body(request)
    if err:
        return err
    # Per address of the sender too, not only per inbox: one host must not mail-bomb many inboxes.
    if not security.hit("code-resend", _client_ip(request), settings.CODE_RESEND_MAX_PER_IP_HOUR, 3600):
        return JsonResponse({"detail": "Please wait before asking for another code.", "code": "rate_limited"}, status=429)
    row = _challenge(data)
    if row is None or not row.is_usable:
        return _code_dead()
    problem = codes.resend(row, lang=data.get("lang"))
    return problem or codes.challenge_response(row)


# ---------------------------------------------------------------------------
# refresh — the centerpiece
# ---------------------------------------------------------------------------
@csrf_exempt
@require_POST
def refresh(request):
    raw = request.COOKIES.get(REFRESH_COOKIE)
    if not raw:
        return JsonResponse({"detail": "No refresh token."}, status=401)

    # Body is optional here; a missing/invalid body just means no device id.
    body, _ = _json_body(request)
    presented_device = _device_id(body or {}, request)

    token_hash = hash_refresh_token(raw)

    with transaction.atomic():
        # Row lock serializes concurrent refreshes of the SAME token (Postgres);
        # on SQLite this is a no-op but SQLite serializes writers anyway.
        try:
            # Only select_related the non-nullable FK (user). Joining the
            # nullable self-FK (replaced_by) here would make Postgres reject
            # `FOR UPDATE` on the nullable side of the outer join; the successor
            # is loaded lazily below, only in the revoked branch that needs it.
            current = (
                RefreshToken.objects.select_for_update()
                .select_related("user")
                .get(token_hash=token_hash)
            )
        except RefreshToken.DoesNotExist:
            resp = JsonResponse({"detail": "Invalid refresh token."}, status=401)
            _clear_refresh_cookie(resp)
            return resp

        now = timezone.now()

        if current.is_revoked:
            successor = current.replaced_by
            within_grace = current.rotated_at is not None and (now - current.rotated_at) <= settings.REFRESH_REUSE_GRACE

            # BENIGN concurrent/retried refresh: the token was rotated only
            # seconds ago and its successor is still live. This is the normal
            # multi-tab cold-load or dropped-Set-Cookie case (security review #1).
            # Re-rotate off the live successor instead of nuking the family.
            if within_grace and successor is not None and successor.is_active:
                new_raw = _rotate_from(successor, request)
                access = encode_access_token(successor.user, successor.family_id)
                resp = _token_response(access)
                _set_refresh_cookie(resp, new_raw)
                return resp

            # Otherwise the family is dead to this token. Always revoke the whole
            # family (idempotent, defensive). Only a genuinely ROTATED token
            # replayed outside the grace window is a true reuse signal worth
            # alerting on; a token revoked administratively (logout / prior
            # family-revoke) has rotated_at=None and is not flagged as theft, so
            # the compromise alert stays high-signal.
            RefreshToken.revoke_family(current.family_id)
            if current.rotated_at is not None:
                log.warning(
                    "token_reuse_detected user=%s family=%s ip=%s device=%s",
                    current.user_id, current.family_id, _client_ip(request), current.unique_device_id,
                )
                security.record(
                    SecurityEvent.Kind.TOKEN_REUSE, request, user=current.user,
                    family=str(current.family_id), device=current.unique_device_id,
                )
            resp = JsonResponse(
                {"detail": "Refresh token reuse detected; session revoked."}, status=401
            )
            _clear_refresh_cookie(resp)
            return resp

        if current.is_expired:
            current.is_revoked = True
            current.save(update_fields=["is_revoked"])
            resp = JsonResponse({"detail": "Refresh token expired."}, status=401)
            _clear_refresh_cookie(resp)
            return resp

        if not current.user.is_active:
            RefreshToken.revoke_family(current.family_id)
            resp = JsonResponse({"detail": "Account is disabled."}, status=401)
            _clear_refresh_cookie(resp)
            return resp

        # Anomaly signal (security review #8): a rotation arriving with a
        # different device id than the family's established binding is logged
        # but not blocked (device_id is client-supplied and spoofable).
        if presented_device and current.unique_device_id and presented_device != current.unique_device_id:
            log.info(
                "refresh_device_mismatch user=%s family=%s stored=%s presented=%s ip=%s",
                current.user_id, current.family_id, current.unique_device_id,
                presented_device, _client_ip(request),
            )

        new_raw = _rotate_from(current, request)
        access = encode_access_token(current.user, current.family_id)

    resp = _token_response(access)
    _set_refresh_cookie(resp, new_raw)
    return resp


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------
@csrf_exempt
@require_POST
def logout(request):
    """
    Bearer-authenticated. The refresh cookie is path-scoped to /refresh and is
    NOT sent here, so we read the signed ``fam`` claim from the access token to
    revoke this device's family. Best-effort + always clears the cookie.
    """
    resp = JsonResponse({"detail": "Logged out."}, status=200)
    _clear_refresh_cookie(resp)

    token = extract_bearer(request)
    if token:
        try:
            # Accept a just-expired token, but only within a bounded window so a
            # long-stale leaked token cannot be replayed as a logout-DoS (#6).
            payload = decode_access_token(token, exp_leeway=settings.LOGOUT_EXP_LEEWAY)
            fam, sub = payload.get("fam"), payload.get("sub")
            if fam and sub:
                RefreshToken.objects.filter(
                    user_id=sub, family_id=fam, is_revoked=False
                ).update(is_revoked=True)
        except InvalidAccessToken:
            pass  # unsigned/garbage/too-stale token -> still return 200 + cleared cookie
    return resp


# ---------------------------------------------------------------------------
# me
# ---------------------------------------------------------------------------
def _me_payload(u):
    return {
        **_user_dict(u),
        "full_name": u.full_name,
        "date_joined": u.date_joined.isoformat(),
    }


@csrf_exempt
@require_auth
def me(request):
    """GET → the current user · PATCH → edit name and appearance preferences."""
    u = request.auth_user

    if request.method == "GET":
        return JsonResponse(_me_payload(u), status=200)
    if request.method != "PATCH":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    data, err = _json_body(request)
    if err:
        return err

    fields = []
    if "first_name" in data:
        u.first_name = str(data.get("first_name") or "").strip()[:150]
        fields.append("first_name")
    if "last_name" in data:
        u.last_name = str(data.get("last_name") or "").strip()[:150]
        fields.append("last_name")
    if "theme" in data:
        theme = str(data.get("theme") or "")
        if theme not in User.Theme.values:
            return JsonResponse({"detail": "Unknown theme."}, status=400)
        u.theme = theme
        fields.append("theme")
    if "brand_color" in data:
        colour = str(data.get("brand_color") or "").strip()
        if colour and not HEX_COLOR.fullmatch(colour):
            return JsonResponse({"detail": "brand_color must be a #RRGGBB value."}, status=400)
        u.brand_color = colour.lower()
        fields.append("brand_color")

    if fields:
        u.save(update_fields=fields)
    return JsonResponse(_me_payload(u), status=200)


# ---------------------------------------------------------------------------
# avatar
# ---------------------------------------------------------------------------
@csrf_exempt
@require_auth
def avatar(request):
    """POST (multipart `avatar`) → replace the picture · DELETE → remove it."""
    u = request.auth_user

    if request.method == "DELETE":
        if u.avatar:
            u.avatar.delete(save=False)
            u.avatar = None
            u.save(update_fields=["avatar"])
        return JsonResponse(_me_payload(u), status=200)

    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    upload = request.FILES.get("avatar")
    if not upload:
        return JsonResponse({"detail": "No file uploaded."}, status=400)
    if upload.size > settings.AVATAR_MAX_BYTES:
        limit = settings.AVATAR_MAX_BYTES // (1024 * 1024)
        return JsonResponse({"detail": f"Image must be under {limit}MB."}, status=400)

    # Trust the bytes, not the client's filename or Content-Type.
    ext = _sniff_image(upload.read(16))
    upload.seek(0)
    if not ext:
        return JsonResponse({"detail": "Upload a PNG, JPEG, GIF or WebP image."}, status=400)

    # Keep the old NAME, not the FieldFile: `u.avatar` is a live reference, so a
    # saved handle would point at the *new* file and delete what we just wrote.
    old_name = u.avatar.name if u.avatar else None
    u.avatar.save(f"avatar.{ext}", upload, save=False)
    u.save(update_fields=["avatar"])
    if old_name and old_name != u.avatar.name:
        u.avatar.storage.delete(old_name)  # only once the new one is stored
    return JsonResponse(_me_payload(u), status=200)


# ---------------------------------------------------------------------------
# credentials
# ---------------------------------------------------------------------------
@csrf_exempt
@require_POST
@require_auth
def change_password(request):
    """Change the password, then cut every OTHER session loose."""
    u = request.auth_user
    data, err = _json_body(request)
    if err:
        return err

    current = data.get("current_password") or ""
    new = data.get("new_password") or ""
    ok = _check_password(request, u, current)
    if ok is None:
        return _too_many_checks()
    if not ok:
        return JsonResponse({"detail": "Current password is incorrect."}, status=400)
    if not new:
        return JsonResponse({"detail": "New password is required."}, status=400)
    try:
        validate_password(new, user=u)
    except ValidationError as e:
        return _weak_password(e)

    u.set_password(new)
    u.save(update_fields=["password"])

    # A password change should log out anyone else holding a token. The caller's
    # own family survives (its access token refreshes silently), so they aren't
    # bounced out of the page they're on.
    keep = (getattr(request, "auth_payload", None) or {}).get("fam")
    revoked = _sign_out_elsewhere(u, keep_family=keep)
    security.record(SecurityEvent.Kind.PASSWORD_CHANGED, request, user=u, other_sessions_revoked=revoked)

    return JsonResponse({"status": "updated", "sessions_revoked": revoked}, status=200)


# ---------------------------------------------------------------------------
# sessions (privacy) — one entry per device family, since rotation reuses it
# ---------------------------------------------------------------------------
def _current_family(request):
    return str((getattr(request, "auth_payload", None) or {}).get("fam") or "")


REAUTH_WINDOW = timedelta(minutes=15)


def _signed_in_recently(request):
    """True when this session's sign-in happened within REAUTH_WINDOW. A
    session (refresh-token family) starts with one row at sign-in and keeps
    its family through every rotation, so the family's oldest row is the
    sign-in. Expired rows are cleaned up only after REFRESH_TOKEN_TTL, long
    after the window, so the oldest one left is never younger than it should be."""
    try:
        family = uuid.UUID(_current_family(request))
    except ValueError:
        return False
    signed_in = (
        RefreshToken.objects.filter(user=request.auth_user, family_id=family)
        .order_by("created_at")
        .values_list("created_at", flat=True)
        .first()
    )
    return signed_in is not None and timezone.now() - signed_in < REAUTH_WINDOW


@require_GET
@require_auth
def sessions(request):
    """Every live sign-in. Rotation keeps `family_id`, so one family == one device."""
    newest = {}
    for token in RefreshToken.objects.filter(user=request.auth_user, is_revoked=False):
        if token.is_expired:
            continue
        key = str(token.family_id)
        # Rows within a family are chained by rotation; keep the latest.
        if key not in newest or token.created_at > newest[key].created_at:
            newest[key] = token

    current = _current_family(request)
    rows = sorted(newest.values(), key=lambda t: t.created_at, reverse=True)
    rows.sort(key=lambda t: str(t.family_id) != current)  # stable: current first

    return JsonResponse(
        {
            "sessions": [
                {
                    "family_id": str(t.family_id),
                    "device_name": t.device_name or "Unknown device",
                    "ip_address": t.ip_address,
                    "created_at": t.created_at.isoformat(),
                    "expires_at": t.expires_at.isoformat(),
                    "current": str(t.family_id) == current,
                }
                for t in rows
            ]
        }
    )


@csrf_exempt
@require_auth
def session_detail(request, family_id):
    """DELETE → sign that device out."""
    if request.method != "DELETE":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    if str(family_id) == _current_family(request):
        return JsonResponse({"detail": "Use log out to end the current session."}, status=400)

    revoked = RefreshToken.objects.filter(
        user=request.auth_user, family_id=family_id, is_revoked=False
    ).update(is_revoked=True)
    if not revoked:
        return JsonResponse({"detail": "Session not found."}, status=404)
    return JsonResponse({"status": "revoked"})


@csrf_exempt
@require_POST
@require_auth
def revoke_other_sessions(request):
    """Sign out everywhere except here."""
    revoked = _sign_out_elsewhere(request.auth_user, keep_family=_current_family(request) or uuid.uuid4())
    security.record(SecurityEvent.Kind.SESSIONS_REVOKED, request, user=request.auth_user, count=revoked)
    return JsonResponse({"status": "revoked", "sessions_revoked": revoked})


@csrf_exempt
@require_auth
def delete_account(request):
    """DELETE → erase the account and everything cascading off it."""
    if request.method != "DELETE":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    data, err = _json_body(request)
    if err:
        return err
    user = request.auth_user
    if user.has_usable_password():
        ok = _check_password(request, user, data.get("password") or "")
        if ok is None:
            return _too_many_checks()
        if not ok:
            return JsonResponse({"detail": "Password is incorrect."}, status=400)
    else:
        # A Google-only account has no password to ask for. It types its email
        # address instead, from a sign-in made in the last few minutes, so a
        # session left open on some computer cannot erase the account.
        if str(data.get("confirm") or "").strip().lower() != user.email.lower():
            return JsonResponse({"detail": "Type your email address to confirm.", "code": "confirm_email"}, status=400)
        if not _signed_in_recently(request):
            return JsonResponse(
                {"detail": "For your safety, sign in again and then delete the account.", "code": "reauth_required"},
                status=403,
            )

    user_id = request.auth_user.pk
    security.record(SecurityEvent.Kind.ACCOUNT_DELETED, request, email=request.auth_user.email, user_id=str(user_id))
    delete_uploads(request.auth_user)
    request.auth_user.delete()  # FKs cascade: tokens, notes, progress, stats
    log.info("account_deleted user=%s", user_id)

    resp = JsonResponse({"status": "deleted"})
    _clear_refresh_cookie(resp)
    return resp


def delete_uploads(user):
    """
    The files that go with an account. Rows cascade on delete, but the files
    they point at stay in storage unless they are removed first.
    """
    from startup.models import BusinessPost, Employee, Product

    files = [user.avatar]
    files += [e.photo for e in Employee.objects.filter(user=user)]
    files += [p.image for p in Product.objects.filter(user=user)]
    files += [p.image for p in BusinessPost.objects.filter(user=user)]
    for f in files:
        if f:
            f.delete(save=False)


@require_auth
def export_data(request):
    """GET → a JSON file with everything we hold about the signed-in person."""
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    if not security.hit("export", request.auth_user.pk, 5, 3600):
        return JsonResponse({"detail": "Too many downloads. Try again in an hour."}, status=429)
    from .export import collect

    data = collect(request.auth_user)
    security.record(SecurityEvent.Kind.DATA_EXPORTED, request, user=request.auth_user)
    resp = JsonResponse(data, json_dumps_params={"ensure_ascii": False, "indent": 1})
    stamp = timezone.now().strftime("%Y-%m-%d")
    resp["Content-Disposition"] = f'attachment; filename="zinvest-my-data-{stamp}.json"'
    resp["Cache-Control"] = "no-store"
    return resp


@csrf_exempt
@require_POST
@require_auth
def change_email(request):
    """Change the sign-in email. Requires the current password."""
    u = request.auth_user
    data, err = _json_body(request)
    if err:
        return err

    password = data.get("password") or ""
    new_email = (data.get("new_email") or "").strip().lower()
    ok = _check_password(request, u, password)
    if ok is None:
        return _too_many_checks()
    if not ok:
        return JsonResponse({"detail": "Password is incorrect."}, status=400)
    if not new_email:
        return JsonResponse({"detail": "New email is required."}, status=400)
    try:
        EmailValidator()(new_email)
    except ValidationError:
        return JsonResponse({"detail": "Enter a valid email address."}, status=400)
    if new_email == u.email.lower():
        return JsonResponse(_me_payload(u), status=200)
    if not security.hit("email-change", u.pk, 5, 3600):
        return JsonResponse({"detail": "A letter is already on its way. Try again in an hour.", "code": "rate_limited"}, status=429)

    # Nothing changes yet: the account moves only once the new address opens
    # the link mailed to it, so nobody can claim an address they do not own.
    # The answer is the same whether or not the address is free (no account
    # enumeration); a taken address simply gets no letter.
    lang = data.get("lang")
    if not User.objects.filter(email__iexact=new_email).exists():
        _mail_verification(u, lang, email=new_email)
        mail.send_email_change_requested(u.email, codes.mask(new_email), lang)
    security.record(SecurityEvent.Kind.EMAIL_CHANGED, request, user=u, step="requested", new=codes.mask(new_email))
    return JsonResponse(
        {**_me_payload(u), "pending_email": new_email,
         "detail": "We sent a link to the new address. The email changes once you open it."},
        status=200,
    )


# ---------------------------------------------------------------------------
# password reset with a one-time link created by staff (admin panel)
# ---------------------------------------------------------------------------
@csrf_exempt
@require_POST
def password_reset(request):
    """
    Body: {"token": "...", "new_password": "..."}. The token is single-use and
    short-lived; using it signs the account out everywhere.
    """
    data, err = _json_body(request)
    if err:
        return err
    ip = _client_ip(request)
    if not security.hit("pwreset", ip, 20, 3600):
        return JsonResponse({"detail": "Too many attempts. Please try again later.", "code": "rate_limited"}, status=429)

    raw = str(data.get("token") or "")
    new = data.get("new_password") or ""
    with transaction.atomic():
        row = (
            PasswordResetToken.objects.select_for_update().select_related("user")
            .filter(token_hash=hash_refresh_token(raw)).first()
            if raw else None
        )
        if row is None or not row.is_usable or not row.user.is_active:
            return JsonResponse({"detail": "This link is invalid or has expired. Ask for a new one.", "code": "bad_token"}, status=400)
        try:
            validate_password(new, user=row.user)
        except ValidationError as e:
            return _weak_password(e)
        user = row.user
        user.set_password(new)
        user.save(update_fields=["password"])
        row.used_at = timezone.now()
        row.save(update_fields=["used_at"])
        PasswordResetToken.objects.filter(user=user, used_at__isnull=True).exclude(pk=row.pk).update(used_at=row.used_at)
        _sign_out_elsewhere(user)
    throttle.clear(ip, user.email)
    security.record(SecurityEvent.Kind.PASSWORD_RESET_USED, request, user=user)
    return JsonResponse({"detail": "Password updated. You can sign in now."}, status=200)


# ---------------------------------------------------------------------------
# email confirmation and the self-service password link
# ---------------------------------------------------------------------------
def _mail_verification(user, lang, email=None):
    """
    Mail a fresh confirmation link and retire the older ones. Never raises:
    the caller's answer must not depend on whether mail went out.

    With ``email`` (another address than the account's) the link is an email
    change: opening it moves the account to that address. Only one link is
    open at a time, so an older one can never move the account anywhere.
    """
    now = timezone.now()
    EmailVerification.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    raw = secrets.token_urlsafe(32)
    EmailVerification.objects.create(
        user=user,
        email=email or user.email,
        token_hash=hash_refresh_token(raw),
        expires_at=now + timedelta(hours=settings.EMAIL_VERIFY_TTL_HOURS),
    )
    url = f"{settings.APP_ORIGIN}/verify-email?token={raw}"
    if email:
        mail.send_email_change(email, url, lang, hours=settings.EMAIL_VERIFY_TTL_HOURS)
    else:
        mail.send_verification(user.email, url, lang)


@csrf_exempt
@require_POST
def verify_email(request):
    """Body: {"token": "..."} — public, because the link opens in any browser."""
    data, err = _json_body(request)
    if err:
        return err
    if not security.hit("verify", _client_ip(request), 30, 3600):
        return JsonResponse({"detail": "Too many attempts. Please try again later.", "code": "rate_limited"}, status=429)

    raw = str(data.get("token") or "")
    with transaction.atomic():
        row = (
            EmailVerification.objects.select_for_update().select_related("user")
            .filter(token_hash=hash_refresh_token(raw)).first()
            if raw else None
        )
        if row is None or not row.is_usable or not row.user.is_active:
            return JsonResponse({"detail": "This link is invalid or has expired. Ask for a new one.", "code": "bad_token"}, status=400)
        row.used_at = timezone.now()
        row.save(update_fields=["used_at"])
        user = row.user
        old_email = user.email
        moving = row.email.lower() != old_email.lower()
        if moving:
            # An email change: the new address has now proved itself.
            user.email = row.email.lower()
            user.email_verified_at = row.used_at
            try:
                with transaction.atomic():
                    user.save(update_fields=["email", "email_verified_at"])
            except IntegrityError:  # someone took the address in the meantime
                return JsonResponse({"detail": "That email cannot be used."}, status=400)
            EmailVerification.objects.filter(user=user, used_at__isnull=True).update(used_at=row.used_at)
            sign_out(user)  # whoever had the old address's sessions is out, Telegram included
        elif user.email_verified_at is None:
            user.email_verified_at = row.used_at
            user.save(update_fields=["email_verified_at"])
    if moving:
        security.record(SecurityEvent.Kind.EMAIL_CHANGED, request, user=user, step="confirmed", old=codes.mask(old_email))
        mail.send_email_changed(old_email, codes.mask(user.email), data.get("lang"))
        return JsonResponse(
            {"detail": "Email changed. Sign in with the new address.", "email": user.email, "changed": True}, status=200
        )
    security.record(SecurityEvent.Kind.EMAIL_VERIFIED, request, user=user)
    return JsonResponse({"detail": "Email confirmed. Thank you.", "email": user.email}, status=200)


@csrf_exempt
@require_POST
@require_auth
def resend_verification(request):
    """Mail the confirmation link again (3 an hour, and only while unconfirmed)."""
    user = request.auth_user
    if user.email_verified_at is not None:
        return JsonResponse({"detail": "This address is already confirmed.", "code": "already_verified"}, status=400)
    if not security.hit("verify-send", user.pk, 3, 3600):
        return JsonResponse({"detail": "A letter is already on its way. Try again in an hour.", "code": "rate_limited"}, status=429)
    data, _ = _json_body(request)
    _mail_verification(user, (data or {}).get("lang"))
    return JsonResponse({"detail": "Letter sent."}, status=200)


@csrf_exempt
@require_POST
def forgot_password(request):
    """
    Body: {"email": "...", "lang": "ru"} — mails a one-time password link.

    The answer is the same whatever the address, so this cannot be used to find
    out who has an account; the work only happens for a real, active one.
    """
    data, err = _json_body(request)
    if err:
        return err
    email = (data.get("email") or "").strip().lower()
    ip = _client_ip(request)
    same_answer = JsonResponse(
        {"detail": "If that address has an account, a letter with a link is on its way."}, status=200
    )
    if not email:
        return same_answer
    # Two brakes: one address cannot be spammed with letters, and one network
    # cannot walk a list of addresses.
    if not security.hit("forgot-ip", ip, settings.FORGOT_MAX_PER_IP_HOUR, 3600):
        return JsonResponse({"detail": "Too many attempts. Please try again later.", "code": "rate_limited"}, status=429)
    if not security.hit("forgot-email", email, settings.FORGOT_MAX_PER_EMAIL_HOUR, 3600):
        return same_answer

    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is None:
        return same_answer

    hours = settings.PASSWORD_RESET_TTL_HOURS
    raw = secrets.token_urlsafe(32)
    PasswordResetToken.objects.create(
        user=user,
        token_hash=hash_refresh_token(raw),
        expires_at=timezone.now() + timedelta(hours=hours),
    )
    security.record(SecurityEvent.Kind.PASSWORD_RESET_CREATED, request, user=user, by="self")
    mail.send_password_reset(user.email, f"{settings.APP_ORIGIN}/reset-password?token={raw}", data.get("lang"), hours=hours)
    return same_answer
