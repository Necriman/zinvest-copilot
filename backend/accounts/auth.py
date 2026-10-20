"""
Bearer access-token verification decorator.

A decorator (rather than middleware) keeps protection explicit and opt-in per
view, so the public auth endpoints stay unauthenticated by default and only
views that mark themselves protected fail closed.
"""
from functools import wraps

from django.http import JsonResponse

from .jwt_utils import InvalidAccessToken, decode_access_token
from .models import User


def extract_bearer(request):
    header = request.META.get("HTTP_AUTHORIZATION", "")
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def require_auth(view_func):
    """
    Gate a view behind a valid access token. On success attaches:
        request.auth_user     -> the User instance
        request.auth_payload  -> the decoded JWT claims (incl. 'fam')
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = extract_bearer(request)
        if not token:
            return JsonResponse(
                {"detail": "Authentication credentials were not provided."}, status=401
            )
        try:
            payload = decode_access_token(token)
        except InvalidAccessToken:
            return JsonResponse({"detail": "Invalid or expired access token."}, status=401)

        # DB round-trip so a deactivated user's still-valid short-lived token is
        # refused immediately (costs one indexed PK lookup per request).
        try:
            user = User.objects.get(pk=payload["sub"], is_active=True)
        except (User.DoesNotExist, KeyError, ValueError):
            return JsonResponse({"detail": "User not found or inactive."}, status=401)

        # "Sign out everywhere", a password reset or a ban: tokens issued before
        # that moment stop working now, not when they expire.
        issued_ms = payload.get("iat_ms") or int(payload.get("iat", 0)) * 1000
        if user.tokens_valid_after is not None and issued_ms < int(user.tokens_valid_after.timestamp() * 1000):
            return JsonResponse({"detail": "Session was signed out. Please sign in again."}, status=401)

        request.auth_user = user
        request.auth_payload = payload
        return view_func(request, *args, **kwargs)

    return wrapper
