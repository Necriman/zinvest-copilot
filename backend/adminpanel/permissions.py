"""
Who on the team may do what in the admin panel, and the step-up rule.

Roles (accounts.User.StaffRole; superusers count as owners):
  owner    everything, including the team and deleting accounts
  admin    users, content, moderation, AI, announcements, settings, logs
  support  looks after learners: accounts, sessions, reset links, reports
  content  units, lessons and tests
  analyst  read-only numbers

Step-up: before any admin endpoint answers, the staff member confirms their
password (and a two-factor code once enrolled) on this device. The confirmation
opens the panel for ADMIN_SESSION_HOURS; changes need one younger than
ADMIN_SUDO_MINUTES. It is tied to the device's session (the refresh-token
family), so a leaked access token from elsewhere does not carry it.
"""
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts import security
from accounts.auth import require_auth
from accounts.models import SecurityEvent

from .models import SudoGrant

OWNER, ADMIN, SUPPORT, CONTENT, ANALYST = "owner", "admin", "support", "content", "analyst"
ALL = (OWNER, ADMIN, SUPPORT, CONTENT, ANALYST)

PERMISSIONS = {
    "overview.view": ALL,
    "users.view": (OWNER, ADMIN, SUPPORT, ANALYST),
    "users.manage": (OWNER, ADMIN, SUPPORT),
    "users.quota": (OWNER, ADMIN),
    "users.coins": (OWNER, ADMIN),
    "users.export": (OWNER, ADMIN),
    "users.delete": (OWNER,),
    "staff.manage": (OWNER,),
    "content.view": (OWNER, ADMIN, CONTENT, ANALYST),
    "content.manage": (OWNER, ADMIN, CONTENT),
    "moderation.view": (OWNER, ADMIN, SUPPORT),
    "moderation.manage": (OWNER, ADMIN, SUPPORT),
    "ai.view": (OWNER, ADMIN, ANALYST),
    "announcements.view": (OWNER, ADMIN, SUPPORT),
    "announcements.manage": (OWNER, ADMIN),
    "audit.view": (OWNER, ADMIN),
    "security.view": (OWNER, ADMIN),
    "security.manage": (OWNER, ADMIN),
    "settings.view": (OWNER, ADMIN),
    "settings.manage": (OWNER, ADMIN),
    "system.view": (OWNER, ADMIN),
    "startups.view": (OWNER, ADMIN, SUPPORT, ANALYST),
}

ADMIN_SESSION_HOURS = 8


def permissions_for(role):
    return sorted(p for p, roles in PERMISSIONS.items() if role in roles)


def can(user, perm):
    role = user.admin_role
    return bool(role) and role in PERMISSIONS.get(perm, ())


def _family(request):
    return str((getattr(request, "auth_payload", None) or {}).get("fam") or "")


def latest_grant(request):
    family = _family(request)
    if not family:
        return None
    return (
        SudoGrant.objects.filter(user=request.auth_user, family_id=family, expires_at__gt=timezone.now())
        .order_by("-created_at").first()
    )


def grant_state(request):
    """{'unlocked': bool, 'sudo_until': iso|None, 'session_until': iso|None}"""
    grant = latest_grant(request)
    if grant is None:
        return {"unlocked": False, "sudo_until": None, "session_until": None}
    sudo_until = grant.created_at + timedelta(minutes=settings.ADMIN_SUDO_MINUTES)
    return {
        "unlocked": True,
        "sudo_until": sudo_until.isoformat() if sudo_until > timezone.now() else None,
        "session_until": grant.expires_at.isoformat(),
    }


def open_grant(request):
    now = timezone.now()
    SudoGrant.objects.filter(user=request.auth_user, expires_at__lte=now).delete()
    return SudoGrant.objects.create(
        user=request.auth_user, family_id=_family(request), expires_at=now + timedelta(hours=ADMIN_SESSION_HOURS)
    )


def _deny(status, detail, code):
    return JsonResponse({"detail": detail, "code": code}, status=status)


def staff_required(perm, *, write=False):
    """
    Guard an admin endpoint: signed in, a staff role with ``perm``, a step-up
    on this device (a fresh one for ``write``), and a sane request rate.
    """
    if perm not in PERMISSIONS:
        raise ValueError(f"unknown admin permission {perm}")

    def decorator(view):
        @csrf_exempt
        @require_auth
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = request.auth_user
            if not can(user, perm):
                security.record(SecurityEvent.Kind.ADMIN_DENIED, request, user=user, permission=perm, path=request.path)
                return _deny(403, "You do not have access to this part of the admin panel.", "forbidden")
            if not security.hit("admin", user.pk, 600, 60):
                return _deny(429, "Too many requests. Slow down a little.", "rate_limited")
            grant = latest_grant(request)
            if grant is None:
                return _deny(403, "Confirm it's you to open the admin panel.", "unlock_required")
            if write and grant.created_at < timezone.now() - timedelta(minutes=settings.ADMIN_SUDO_MINUTES):
                return _deny(403, "Confirm it's you again to make changes.", "sudo_required")
            request.admin_role = user.admin_role
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
