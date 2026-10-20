"""
Getting into the admin panel: who am I, confirm it's me (password + second
factor), set up the authenticator app, lock the panel again.
"""
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from accounts import security, totp
from accounts.auth import require_auth
from accounts.models import SecurityEvent
from accounts.views import _check_password, _signed_in_recently

from ..audit import audit
from ..models import SudoGrant
from ..permissions import grant_state, open_grant, permissions_for
from .common import body, method_not_allowed


def _staff(request):
    role = request.auth_user.admin_role
    if not role:
        security.record(SecurityEvent.Kind.ADMIN_DENIED, request, user=request.auth_user, path=request.path)
        return None, JsonResponse({"detail": "The admin panel is for the Zinvest team.", "code": "forbidden"}, status=403)
    return role, None


def _no_password_proof(request, user):
    """
    The step-up for an account with no password (signed up with Google). Once
    two-factor is on, the authenticator code is the proof and is checked by the
    caller. Before that, only a sign-in from the last few minutes will do: the
    person has just proven the Google account again. Returns an error or None.
    """
    if user.totp_enabled or _signed_in_recently(request):
        return None
    security.record(SecurityEvent.Kind.ADMIN_SUDO_FAILED, request, user=user, reason="stale_sign_in")
    return JsonResponse(
        {"detail": "Sign in with Google again, then open the panel within 15 minutes.", "code": "reauth_required"},
        status=403,
    )


def _me(request, role):
    user = request.auth_user
    return {
        "email": user.email,
        "name": user.full_name,
        "role": role,
        "permissions": permissions_for(role),
        "totp_enabled": user.totp_enabled,
        # A Google-only account has no password to confirm with (see _no_password_proof).
        "has_password": user.has_usable_password(),
        "require_2fa": settings.ADMIN_REQUIRE_2FA,
        "sudo_minutes": settings.ADMIN_SUDO_MINUTES,
        **grant_state(request),
    }


@csrf_exempt
@require_auth
def me(request):
    if request.method != "GET":
        return method_not_allowed()
    role, err = _staff(request)
    if err:
        return err
    return JsonResponse(_me(request, role))


@csrf_exempt
@require_auth
def unlock(request):
    """POST {password, code} → open the panel on this device."""
    if request.method != "POST":
        return method_not_allowed()
    role, err = _staff(request)
    if err:
        return err
    data, err = body(request)
    if err:
        return err
    user = request.auth_user
    if user.has_usable_password():
        ok = _check_password(request, user, data.get("password") or "")
        if ok is None:
            return JsonResponse({"detail": "Too many wrong attempts. Try again in 15 minutes.", "code": "rate_limited"}, status=429)
        if not ok:
            security.record(SecurityEvent.Kind.ADMIN_SUDO_FAILED, request, user=user, reason="password")
            return JsonResponse({"detail": "Wrong password.", "code": "bad_password"}, status=400)
    else:
        err = _no_password_proof(request, user)
        if err:
            return err
    if user.totp_enabled:
        if security.over("pwcheck", user.pk, settings.PASSWORD_CHECK_MAX):
            return JsonResponse({"detail": "Too many wrong attempts. Try again in 15 minutes.", "code": "rate_limited"}, status=429)
        if not totp.verify(totp.decrypt(user.totp_secret), data.get("code"), user_id=user.pk):
            security.hit("pwcheck", user.pk, settings.PASSWORD_CHECK_MAX, 15 * 60)
            security.record(SecurityEvent.Kind.ADMIN_SUDO_FAILED, request, user=user, reason="code")
            return JsonResponse({"detail": "Wrong or expired code from the authenticator app.", "code": "bad_code"}, status=400)
    elif settings.ADMIN_REQUIRE_2FA:
        return JsonResponse({"detail": "Turn on two-factor sign-in first.", "code": "totp_setup_required"}, status=403)
    open_grant(request)
    security.record(SecurityEvent.Kind.ADMIN_SUDO, request, user=user, role=role)
    return JsonResponse(_me(request, role))


@csrf_exempt
@require_auth
def lock(request):
    """POST → close the panel on this device."""
    if request.method != "POST":
        return method_not_allowed()
    role, err = _staff(request)
    if err:
        return err
    family = str((request.auth_payload or {}).get("fam") or "")
    SudoGrant.objects.filter(user=request.auth_user, family_id=family).delete()
    return JsonResponse(_me(request, role))


@csrf_exempt
@require_auth
def totp_setup(request):
    """
    POST {password} → a new secret and its otpauth:// link for the app. It is
    not active until confirmed with a code (totp_enable).
    """
    if request.method != "POST":
        return method_not_allowed()
    role, err = _staff(request)
    if err:
        return err
    user = request.auth_user
    if user.totp_enabled:
        return JsonResponse({"detail": "Two-factor sign-in is already on.", "code": "already_enabled"}, status=400)
    data, err = body(request)
    if err:
        return err
    if user.has_usable_password():
        ok = _check_password(request, user, data.get("password") or "")
        if ok is None:
            return JsonResponse({"detail": "Too many wrong attempts. Try again in 15 minutes.", "code": "rate_limited"}, status=429)
        if not ok:
            return JsonResponse({"detail": "Wrong password.", "code": "bad_password"}, status=400)
    else:
        err = _no_password_proof(request, user)
        if err:
            return err
    secret = totp.new_secret()
    user.totp_secret = totp.encrypt(secret)
    user.save(update_fields=["totp_secret"])
    return JsonResponse({"secret": secret, "otpauth_uri": totp.provisioning_uri(secret, user.email)})


@csrf_exempt
@require_auth
def totp_enable(request):
    """POST {code} → turn two-factor on; this also opens the panel."""
    if request.method != "POST":
        return method_not_allowed()
    role, err = _staff(request)
    if err:
        return err
    user = request.auth_user
    data, err = body(request)
    if err:
        return err
    secret = totp.decrypt(user.totp_secret)
    if not secret:
        return JsonResponse({"detail": "Start the setup again.", "code": "no_setup"}, status=400)
    if not totp.verify(secret, data.get("code"), user_id=user.pk):
        return JsonResponse({"detail": "That code does not match. Check the time on your phone and try again.", "code": "bad_code"}, status=400)
    user.totp_enabled = True
    user.save(update_fields=["totp_enabled"])
    security.record(SecurityEvent.Kind.TOTP_ENABLED, request, user=user)
    audit(request, "staff.totp_enabled", target_type="user", target_id=user.pk, summary="Two-factor sign-in turned on")
    open_grant(request)
    return JsonResponse(_me(request, role))
