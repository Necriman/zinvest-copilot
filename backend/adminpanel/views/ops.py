"""
Running the platform: AI spend, announcements, switches, the audit log, the
security log and the team list.
"""
import ipaddress
import time
import uuid
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.db.models import Count, OuterRef, Q, Subquery, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts import bans as autoban
from accounts.models import Ban, RateBucket, RefreshToken, SecurityEvent, User
from config import ratelimit
from ai_engine.models import AIUsageLog, UserAIQuota

from ..audit import audit
from ..models import Announcement, AuditLog, PlatformSettings
from ..permissions import ALL, PERMISSIONS, staff_required
from .common import body, iso, method_not_allowed, paginate

# Rough list prices per million tokens (input, output), USD, for an estimate only.
PRICE_PER_MILLION = {
    "pro": (1.25, 10.0),
    "flash": (0.30, 2.50),
    "flash-lite": (0.10, 0.40),
    "tts": (0.50, 10.0),
}


def _price_key(model):
    model = (model or "").lower()
    if "tts" in model:
        return "tts"
    if "lite" in model:
        return "flash-lite"
    if "pro" in model:
        return "pro"
    return "flash"


@staff_required("ai.view")
def ai_usage(request):
    if request.method != "GET":
        return method_not_allowed()
    try:
        days = min(90, max(1, int(request.GET.get("days", 30))))
    except ValueError:
        days = 30
    since = timezone.now() - timedelta(days=days)
    logs = AIUsageLog.objects.filter(created_at__gte=since).exclude(model_version="stub")
    by_model = logs.values("model_version").annotate(i=Sum("input_tokens"), o=Sum("output_tokens"), n=Count("pk"))
    cost = 0.0
    for row in by_model:
        price_in, price_out = PRICE_PER_MILLION[_price_key(row["model_version"])]
        cost += (row["i"] or 0) / 1e6 * price_in + (row["o"] or 0) / 1e6 * price_out
    totals = logs.aggregate(i=Sum("input_tokens"), o=Sum("output_tokens"), n=Count("pk"), users=Count("user", distinct=True))
    start = timezone.localdate() - timedelta(days=days - 1)
    daily = {r["day"]: r for r in logs.annotate(day=TruncDate("created_at")).values("day").annotate(n=Count("pk"), t=Sum("input_tokens") + Sum("output_tokens"))}
    top = (
        logs.values("user", "user__email").annotate(n=Count("pk"), t=Sum("input_tokens") + Sum("output_tokens")).order_by("-t")[:10]
    )
    return JsonResponse({
        "days": days,
        "requests": totals["n"] or 0,
        "tokens": (totals["i"] or 0) + (totals["o"] or 0),
        "users": totals["users"] or 0,
        "estimated_cost_usd": round(cost, 2),
        "stub_requests": AIUsageLog.objects.filter(created_at__gte=since, model_version="stub").count(),
        "by_feature": list(logs.values("feature").annotate(requests=Count("pk"), tokens=Sum("input_tokens") + Sum("output_tokens")).order_by("-tokens")),
        "daily": [
            {"date": (start + timedelta(days=i)).isoformat(), "requests": daily.get(start + timedelta(days=i), {}).get("n", 0),
             "tokens": daily.get(start + timedelta(days=i), {}).get("t", 0) or 0}
            for i in range(days)
        ],
        "top_users": [{"id": str(r["user"]), "email": r["user__email"], "requests": r["n"], "tokens": r["t"] or 0} for r in top],
        "quotas": {
            "default_limit": settings.AI_DEFAULT_MONTHLY_TOKEN_LIMIT,
            "exhausted": sum(1 for q in UserAIQuota.objects.all().only("monthly_token_limit", "tokens_used_this_cycle") if q.tokens_used_this_cycle >= q.monthly_token_limit),
            "by_tier": list(UserAIQuota.objects.values("tier").annotate(n=Count("pk")).order_by("tier")),
        },
    })


# --------------------------------------------------------------------------- #
# Announcements
def _announcement_dict(a):
    return {
        "id": str(a.id), "title": a.title, "body": a.body, "link_url": a.link_url, "link_label": a.link_label,
        "level": a.level, "audience": a.audience, "starts_at": iso(a.starts_at), "ends_at": iso(a.ends_at),
        "is_active": a.is_active, "live": a.live(), "created_by": a.created_by.email if a.created_by else None,
        "created_at": iso(a.created_at),
    }


def _safe_link(url):
    """Internal paths or https links only: no javascript:, data: or http:."""
    url = (url or "").strip()
    if not url:
        return ""
    if "\\" in url or any(ord(ch) < 32 for ch in url):  # "/\evil.com" is read as "//evil.com"
        return None
    if url.startswith("/") and not url.startswith("//"):
        return url[:300]
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.netloc:
        return url[:300]
    return None


def _apply_announcement(a, data):
    if "title" in data:
        title = str(data["title"] or "").strip()
        if not 1 <= len(title) <= 120:
            return "Title: 1-120 characters."
        a.title = title
    if "body" in data:
        a.body = str(data["body"] or "").strip()[:500]
    if "link_url" in data:
        link = _safe_link(data["link_url"])
        if link is None:
            return "The link must be a path inside the app (/app/...) or an https:// address."
        a.link_url = link
    if "link_label" in data:
        a.link_label = str(data["link_label"] or "").strip()[:40]
    if "level" in data:
        if data["level"] not in dict(Announcement.Level.choices):
            return "Unknown style."
        a.level = data["level"]
    if "audience" in data:
        if data["audience"] not in dict(Announcement.Audience.choices):
            return "Unknown audience."
        a.audience = data["audience"]
    for key in ("starts_at", "ends_at"):
        if key in data:
            value = data[key]
            if value in (None, ""):
                if key == "starts_at":
                    return "Start time is required."
                setattr(a, key, None)
                continue
            parsed = parse_datetime(str(value))
            if parsed is None:
                return f"{key} is not a valid date and time."
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed)
            setattr(a, key, parsed)
    if a.ends_at and a.ends_at <= a.starts_at:
        return "The end must be after the start."
    if "is_active" in data:
        a.is_active = bool(data["is_active"])
    return None


@staff_required("announcements.view")
def announcements(request):
    if request.method == "GET":
        return JsonResponse({"results": [_announcement_dict(a) for a in Announcement.objects.select_related("created_by").order_by("-created_at")[:100]]})
    if request.method != "POST":
        return method_not_allowed()
    from ..permissions import can, latest_grant
    if not can(request.auth_user, "announcements.manage"):
        return JsonResponse({"detail": "You can view announcements but not publish them.", "code": "forbidden"}, status=403)
    grant = latest_grant(request)
    if grant is None or grant.created_at < timezone.now() - timedelta(minutes=settings.ADMIN_SUDO_MINUTES):
        return JsonResponse({"detail": "Confirm it's you again to make changes.", "code": "sudo_required"}, status=403)
    data, err = body(request)
    if err:
        return err
    a = Announcement(created_by=request.auth_user)
    problem = _apply_announcement(a, {"starts_at": timezone.now().isoformat(), **data})
    if problem:
        return JsonResponse({"detail": problem}, status=400)
    a.save()
    audit(request, "announcement.created", target_type="announcement", target_id=a.pk, summary=f"Published “{a.title}”")
    return JsonResponse(_announcement_dict(a), status=201)


@staff_required("announcements.manage", write=True)
def announcement_detail(request, announcement_id):
    a = get_object_or_404(Announcement, pk=announcement_id)
    if request.method == "DELETE":
        title = a.title
        a.delete()
        audit(request, "announcement.deleted", target_type="announcement", target_id=announcement_id, summary=f"Deleted “{title}”")
        return JsonResponse({"ok": True})
    if request.method != "PATCH":
        return method_not_allowed()
    data, err = body(request)
    if err:
        return err
    problem = _apply_announcement(a, data)
    if problem:
        return JsonResponse({"detail": problem}, status=400)
    a.save()
    audit(request, "announcement.updated", target_type="announcement", target_id=a.pk, summary=f"Edited “{a.title}”")
    return JsonResponse(_announcement_dict(a))


# --------------------------------------------------------------------------- #
# Platform switches
SWITCHES = ("registration_open", "ai_enabled", "tts_enabled", "network_posting_enabled")


def _settings_dict(s):
    return {
        **{key: getattr(s, key) for key in SWITCHES},
        "maintenance_message": s.maintenance_message,
        "updated_by": s.updated_by.email if s.updated_by else None,
        "updated_at": iso(s.updated_at),
        "server": {  # read-only facts about this deployment
            "debug": settings.DEBUG,
            "require_2fa": settings.ADMIN_REQUIRE_2FA,
            "ai_key": bool(settings.GEMINI_API_KEY),
            "shared_cache": "redis" in settings.CACHES["default"]["BACKEND"].lower(),
            "database": settings.DATABASES["default"]["ENGINE"].rsplit(".", 1)[-1],
        },
    }


@staff_required("settings.view")
def platform_settings(request):
    current = PlatformSettings.current()
    if request.method == "GET":
        return JsonResponse(_settings_dict(current))
    if request.method != "PATCH":
        return method_not_allowed()
    from ..permissions import can, latest_grant
    if not can(request.auth_user, "settings.manage"):
        return JsonResponse({"detail": "You cannot change platform settings.", "code": "forbidden"}, status=403)
    grant = latest_grant(request)
    if grant is None or grant.created_at < timezone.now() - timedelta(minutes=settings.ADMIN_SUDO_MINUTES):
        return JsonResponse({"detail": "Confirm it's you again to make changes.", "code": "sudo_required"}, status=403)
    data, err = body(request)
    if err:
        return err
    changed = {}
    for key in SWITCHES:
        if key in data:
            value = bool(data[key])
            if getattr(current, key) != value:
                changed[key] = value
                setattr(current, key, value)
    if "maintenance_message" in data:
        message = str(data["maintenance_message"] or "").strip()[:300]
        if message != current.maintenance_message:
            changed["maintenance_message"] = message
            current.maintenance_message = message
    current.updated_by = request.auth_user
    current.save()
    if changed:
        audit(request, "settings.updated", target_type="settings", target_id="platform",
              summary="Changed: " + ", ".join(f"{k}={v}" for k, v in changed.items()), changes=changed)
    return JsonResponse(_settings_dict(current))


# --------------------------------------------------------------------------- #
# Logs and the team
@staff_required("audit.view")
def audit_log(request):
    if request.method != "GET":
        return method_not_allowed()
    qs = AuditLog.objects.order_by("-created_at")
    q = request.GET.get("q", "").strip()[:120]
    if q:
        qs = qs.filter(Q(summary__icontains=q) | Q(actor_email__icontains=q) | Q(action__icontains=q) | Q(target_id=q))
    action = request.GET.get("action", "").strip()
    if action:
        qs = qs.filter(action__startswith=action)
    return JsonResponse(paginate(request, qs, lambda a: {
        "id": str(a.id), "actor": a.actor_email, "action": a.action, "target_type": a.target_type,
        "target_id": a.target_id, "summary": a.summary, "ip": a.ip_address, "at": iso(a.created_at),
    }, per_page=40))


@staff_required("security.view")
def security_events(request):
    if request.method != "GET":
        return method_not_allowed()
    qs = SecurityEvent.objects.order_by("-created_at")
    kind = request.GET.get("kind", "")
    if kind in dict(SecurityEvent.Kind.choices):
        qs = qs.filter(kind=kind)
    q = request.GET.get("q", "").strip()[:120]
    if q:
        try:
            ipaddress.ip_address(q)
            qs = qs.filter(ip_address=q)
        except ValueError:
            qs = qs.filter(email__icontains=q)
    day = timezone.now() - timedelta(days=1)
    week = timezone.now() - timedelta(days=7)
    top_ips = (
        SecurityEvent.objects.filter(kind__in=[SecurityEvent.Kind.LOGIN_FAILED, SecurityEvent.Kind.LOGIN_LOCKED], created_at__gte=day)
        .exclude(ip_address=None).values("ip_address").annotate(n=Count("pk")).order_by("-n")[:5]
    )
    page = paginate(request, qs, lambda e: {
        "id": str(e.id), "kind": e.kind, "label": e.get_kind_display(), "email": e.email,
        "ip": e.ip_address, "details": e.details, "at": iso(e.created_at),
    }, per_page=40)
    page["summary"] = {
        "failed_day": SecurityEvent.objects.filter(kind=SecurityEvent.Kind.LOGIN_FAILED, created_at__gte=day).count(),
        "locked_day": SecurityEvent.objects.filter(kind=SecurityEvent.Kind.LOGIN_LOCKED, created_at__gte=day).count(),
        "token_reuse_week": SecurityEvent.objects.filter(kind=SecurityEvent.Kind.TOKEN_REUSE, created_at__gte=week).count(),
        "admin_denied_week": SecurityEvent.objects.filter(kind=SecurityEvent.Kind.ADMIN_DENIED, created_at__gte=week).count(),
        "live_sessions": RefreshToken.objects.filter(is_revoked=False, expires_at__gt=timezone.now()).values("family_id").distinct().count(),
        "staff_without_2fa": User.objects.filter(is_active=True, totp_enabled=False).filter(Q(is_superuser=True) | ~Q(staff_role="")).count(),
        "top_ips": [{"ip": r["ip_address"], "count": r["n"]} for r in top_ips],
    }
    page["kinds"] = [{"value": k, "label": label} for k, label in SecurityEvent.Kind.choices]
    return JsonResponse(page)


def _ban_dict(b):
    return {
        "id": str(b.id), "kind": b.kind, "value": b.value, "reason": b.reason, "hits": b.hits, "limit": b.limit,
        "strike": b.strike, "at": iso(b.created_at), "expires_at": iso(b.expires_at) if b.expires_at else None,
        "forever": b.expires_at is None, "active": b.is_active,
        "lifted_at": iso(b.lifted_at) if b.lifted_at else None, "lifted_by": b.lifted_by,
        "user": {"id": str(b.user_id), "email": b.user.email, "name": b.user.full_name} if b.user_id else None,
    }


def _live_counters():
    """The busiest rate-limit windows right now (RateBucket, the database store only)."""
    if settings.RATE_LIMIT_STORE != "db":
        return None
    now = int(time.time())
    rows = list(RateBucket.objects.filter(resets_at__gt=now).order_by("-hits")[:12])
    caps = ratelimit.limits()
    def account_id(key):  # "u:<id>" from the API counters, a bare id from the per-view ones
        key = key.removeprefix("u:")
        try:
            return str(uuid.UUID(key))
        except ValueError:
            return None

    keys = [r.name.partition(":")[2] for r in rows]
    ids = [i for i in map(account_id, keys) if i]
    emails = {str(pk): email for pk, email in User.objects.filter(pk__in=ids).values_list("pk", "email")} if ids else {}
    out = []
    for r, key in zip(rows, keys):
        scope = r.name.partition(":")[0]
        limit = None
        if scope.startswith("api-"):
            kind = scope[4:]
            limit = caps["guest_write"] if kind == "write" and key.startswith("ip:") else caps.get(kind)
        who = emails.get(account_id(key) or "", key.removeprefix("ip:"))
        out.append({"scope": scope, "who": who, "hits": r.hits, "limit": limit,
                    "ban_at": autoban.threshold(limit) if limit and scope in autoban.ACTORS else None,
                    "resets_in": max(0, r.resets_at - now)})
    return out


@staff_required("security.view")
def bans(request):
    """Automatic bans (accounts.bans) and the live counters behind them."""
    if request.method != "GET":
        return method_not_allowed()
    now = timezone.now()
    active = Q(lifted_at=None) & (Q(expires_at=None) | Q(expires_at__gt=now))
    qs = Ban.objects.select_related("user").order_by("-created_at")
    if request.GET.get("show", "active") == "active":
        qs = qs.filter(active)
    page = paginate(request, qs, _ban_dict, per_page=20)
    page["summary"] = {
        "accounts": Ban.objects.filter(active, kind=Ban.Kind.USER).count(),
        "addresses": Ban.objects.filter(active, kind=Ban.Kind.IP).count(),
        "week": Ban.objects.filter(created_at__gte=now - timedelta(days=7)).count(),
    }
    page["counters"] = _live_counters()
    page["policy"] = {"enabled": settings.AUTO_BAN_ENABLED, "factor": settings.AUTO_BAN_FACTOR}
    return JsonResponse(page)


@staff_required("security.manage", write=True)
def ban_lift(request, ban_id):
    if request.method != "POST":
        return method_not_allowed()
    ban = get_object_or_404(Ban.objects.select_related("user"), pk=ban_id)
    if ban.lifted_at:
        return JsonResponse({"detail": "This ban is already lifted."}, status=409)
    autoban.lift(ban, request.auth_user.email)
    who = ban.user.email if ban.user_id else ban.value
    audit(request, "ban.lifted", target_type="user" if ban.kind == Ban.Kind.USER else "ip", target_id=ban.user_id or ban.value,
          summary=f"Lifted the {ban.get_kind_display().lower()} ban on {who} ({ban.reason})")
    return JsonResponse({"ok": True, "ban": _ban_dict(ban)})


@staff_required("users.view")
def staff(request):
    if request.method != "GET":
        return method_not_allowed()
    last_seen = RefreshToken.objects.filter(user=OuterRef("pk")).order_by("-created_at").values("created_at")[:1]
    team = User.objects.filter(Q(is_superuser=True) | ~Q(staff_role="")).annotate(last_seen=Subquery(last_seen)).order_by("email")
    return JsonResponse({
        "results": [{
            "id": str(u.pk), "email": u.email, "name": u.full_name, "role": u.admin_role or u.staff_role,
            "is_active": u.is_active, "is_superuser": u.is_superuser, "totp_enabled": u.totp_enabled,
            "last_seen": iso(u.last_seen),
        } for u in team],
        # Who may do what, straight from the rules the API enforces.
        "roles": list(ALL),
        "permissions": {perm: list(roles) for perm, roles in PERMISSIONS.items()},
    })
