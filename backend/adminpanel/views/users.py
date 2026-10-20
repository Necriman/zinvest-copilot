"""
Learners and team accounts: find, look after, and in rare cases remove.

Rule of thumb: anything done *to a team account* (disable, reset link, sign
out, role, two-factor reset) needs an owner, so a support account can never be
used to take over an admin.
"""
import csv
import io
import secrets
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, F, IntegerField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts import bans, security, sessions
from accounts.export import collect as collect_user_data
from accounts.models import PasswordResetToken, RefreshToken, SecurityEvent, User
from accounts.views import delete_uploads
from accounts.tokens import hash_refresh_token
from ai_engine.models import AIUsageLog, UserAIQuota
from learning.models import Lesson, LessonProgress, OnboardingAssessment, UnitProgress, UnitTestResult, UserStats
from startup.models import BusinessPost, Employee, Product, StartupProfile

from ..audit import audit
from ..models import AuditLog, Report
from ..permissions import OWNER, can, staff_required
from .common import body, iso, method_not_allowed, paginate

ROLES = {"", "owner", "admin", "support", "content", "analyst"}


def _annotated():
    last_seen = RefreshToken.objects.filter(user=OuterRef("pk")).order_by("-created_at").values("created_at")[:1]
    lessons = (
        LessonProgress.objects.filter(user=OuterRef("pk"), status=LessonProgress.Status.COMPLETED)
        .values("user").annotate(n=Count("pk")).values("n")[:1]
    )
    coins = UserStats.objects.filter(user=OuterRef("pk")).values("coins")[:1]
    startup = StartupProfile.objects.filter(user=OuterRef("pk")).values("name")[:1]
    return User.objects.annotate(
        last_seen=Subquery(last_seen),
        lessons_done=Coalesce(Subquery(lessons, output_field=IntegerField()), Value(0)),
        coins_total=Coalesce(Subquery(coins, output_field=IntegerField()), Value(0)),
        startup_name=Subquery(startup),
    )


def _row(u):
    return {
        "id": str(u.id),
        "email": u.email,
        "name": u.full_name,
        "avatar_url": u.avatar.url if u.avatar else None,
        "is_active": u.is_active,
        "role": u.admin_role if u.is_active else (u.staff_role or ("owner" if u.is_superuser else "")),
        "totp_enabled": u.totp_enabled,
        "date_joined": iso(u.date_joined),
        "last_seen": iso(getattr(u, "last_seen", None)),
        "lessons_done": getattr(u, "lessons_done", 0),
        "coins": getattr(u, "coins_total", 0),
        "startup": getattr(u, "startup_name", None) or "",
    }


def _is_team(u):
    return bool(u.is_superuser or u.staff_role)


def _guard_team_target(request, target):
    """Only owners act on team accounts, and nobody acts on themselves here."""
    if target.pk == request.auth_user.pk:
        return JsonResponse({"detail": "Use your own settings for your account."}, status=400)
    if _is_team(target) and request.admin_role != OWNER:
        return JsonResponse({"detail": "Only an owner can change a team account."}, status=403)
    return None


@staff_required("users.view")
def users(request):
    if request.method != "GET":
        return method_not_allowed()
    qs = _annotated()
    q = request.GET.get("q", "").strip()[:120]
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(startup__name__icontains=q))
    status = request.GET.get("status")
    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "disabled":
        qs = qs.filter(is_active=False)
    role = request.GET.get("role")
    if role == "team":
        qs = qs.filter(Q(is_superuser=True) | ~Q(staff_role=""))
    elif role == "learners":
        qs = qs.filter(is_superuser=False, staff_role="")
    joined = request.GET.get("joined")
    if joined in {"1", "7", "30"}:
        qs = qs.filter(date_joined__gte=timezone.now() - timedelta(days=int(joined)))
    sort = {
        "joined": "-date_joined", "joined_asc": "date_joined", "email": "email",
        "seen": "-last_seen", "lessons": "-lessons_done", "coins": "-coins_total",
    }.get(request.GET.get("sort", "joined"), "-date_joined")
    qs = qs.order_by(F("last_seen").desc(nulls_last=True), "pk") if sort == "-last_seen" else qs.order_by(sort, "pk")
    return JsonResponse(paginate(request, qs, _row))


def _sessions(u):
    now = timezone.now()
    live = RefreshToken.objects.filter(user=u, is_revoked=False, expires_at__gt=now).order_by("-created_at")
    seen, out = set(), []
    for t in live:
        if t.family_id in seen:
            continue
        seen.add(t.family_id)
        out.append({"device": t.device_name or "Unknown device", "ip": t.ip_address, "last_active": iso(t.created_at), "expires": iso(t.expires_at)})
    return out


@staff_required("users.view")
def user_detail(request, user_id):
    u = get_object_or_404(_annotated(), pk=user_id)
    if request.method == "DELETE":
        return _delete(request, u)
    if request.method != "GET":
        return method_not_allowed()
    stats = UserStats.objects.filter(user=u).first()
    quota = UserAIQuota.get_or_create_for(u)
    onboarding = OnboardingAssessment.objects.filter(user=u).first()
    startup = StartupProfile.objects.filter(user=u).first()
    month = timezone.now() - timedelta(days=30)
    tests = UnitTestResult.objects.filter(user=u)
    ai_by_feature = list(
        AIUsageLog.objects.filter(user=u, created_at__gte=month).values("feature")
        .annotate(requests=Count("pk"), tokens=Sum("input_tokens") + Sum("output_tokens")).order_by("-requests")
    )
    return JsonResponse({
        **_row(u),
        "first_name": u.first_name,
        "last_name": u.last_name,
        "is_superuser": u.is_superuser,
        "disabled_reason": u.disabled_reason,
        "learning": {
            "lessons_done": u.lessons_done,
            "lessons_total": Lesson.objects.count(),
            "units_passed": UnitProgress.objects.filter(user=u, test_passed=True).count(),
            "tests_taken": tests.count(),
            "best_score": round(100 * max([t.score for t in tests] or [0])),
            "coins": stats.coins if stats else 0,
            "streak": stats.day_streak if stats else 0,
            "longest_streak": stats.longest_streak if stats else 0,
            "last_activity": iso(stats.last_activity_date) if stats else None,
            "level": onboarding.level if onboarding else None,
        },
        "ai": {
            "tier": quota.tier,
            "limit": quota.monthly_token_limit,
            "used": quota.tokens_used_this_cycle,
            "reset_date": iso(quota.reset_date),
            "by_feature": ai_by_feature,
        },
        "startup": {
            "name": startup.name,
            "industry": startup.industry,
            "public": startup.public_visible,
            "employees": Employee.objects.filter(user=u).count(),
            "products": Product.objects.filter(user=u).count(),
            "posts": BusinessPost.objects.filter(user=u).count(),
        } if startup else None,
        "sessions": _sessions(u),
        "security": [
            {"kind": e.kind, "label": e.get_kind_display(), "ip": e.ip_address, "at": iso(e.created_at)}
            for e in SecurityEvent.objects.filter(user=u).order_by("-created_at")[:15]
        ],
        "reports_open": Report.objects.filter(target_user=u, status=Report.Status.OPEN).count(),
        "history": [
            {"action": a.action, "summary": a.summary, "actor": a.actor_email, "at": iso(a.created_at)}
            for a in AuditLog.objects.filter(target_type="user", target_id=str(u.pk)).order_by("-created_at")[:15]
        ],
    })


def _revoke_everything(u):
    return sessions.sign_out(u)


@staff_required("users.manage", write=True)
def user_status(request, user_id):
    """POST {active: bool, reason} → ban or restore an account."""
    if request.method != "POST":
        return method_not_allowed()
    u = get_object_or_404(User, pk=user_id)
    err = _guard_team_target(request, u)
    if err:
        return err
    data, err = body(request)
    if err:
        return err
    active = bool(data.get("active"))
    reason = str(data.get("reason") or "").strip()[:300]
    if not active and not reason:
        return JsonResponse({"detail": "Say why the account is disabled (staff see it later)."}, status=400)
    u.is_active = active
    u.disabled_reason = "" if active else reason
    u.save(update_fields=["is_active", "disabled_reason"])
    if not active:
        _revoke_everything(u)
    else:
        bans.lift_for_user(u, request.auth_user.email)
    audit(request, "user.enabled" if active else "user.disabled", target_type="user", target_id=u.pk,
          summary=f"{'Enabled' if active else 'Disabled'} {u.email}" + (f": {reason}" if reason else ""), reason=reason)
    return JsonResponse({"ok": True, "is_active": u.is_active})


@staff_required("users.manage", write=True)
def user_revoke_sessions(request, user_id):
    if request.method != "POST":
        return method_not_allowed()
    u = get_object_or_404(User, pk=user_id)
    err = _guard_team_target(request, u)
    if err:
        return err
    revoked = _revoke_everything(u)
    security.record(SecurityEvent.Kind.SESSIONS_REVOKED, request, user=u, by=request.auth_user.email, count=revoked)
    audit(request, "user.sessions_revoked", target_type="user", target_id=u.pk, summary=f"Signed {u.email} out everywhere ({revoked})")
    return JsonResponse({"ok": True, "sessions_revoked": revoked})


@staff_required("users.manage", write=True)
def user_reset_link(request, user_id):
    """POST → a one-time password link (1 hour) to pass to the learner."""
    if request.method != "POST":
        return method_not_allowed()
    u = get_object_or_404(User, pk=user_id, is_active=True)
    err = _guard_team_target(request, u)
    if err:
        return err
    raw = secrets.token_urlsafe(32)
    row = PasswordResetToken.objects.create(
        user=u, token_hash=hash_refresh_token(raw), created_by=request.auth_user,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    security.record(SecurityEvent.Kind.PASSWORD_RESET_CREATED, request, user=u, by=request.auth_user.email)
    audit(request, "user.reset_link", target_type="user", target_id=u.pk, summary=f"Created a password reset link for {u.email}")
    return JsonResponse({"url": f"{settings.APP_ORIGIN}/reset-password?token={raw}", "expires_at": iso(row.expires_at)})


@staff_required("users.quota", write=True)
def user_quota(request, user_id):
    """POST {tier, monthly_token_limit, reset_usage} → change the AI allowance."""
    if request.method != "POST":
        return method_not_allowed()
    u = get_object_or_404(User, pk=user_id)
    data, err = body(request)
    if err:
        return err
    quota = UserAIQuota.get_or_create_for(u)
    before = {"tier": quota.tier, "limit": quota.monthly_token_limit, "used": quota.tokens_used_this_cycle}
    tier = data.get("tier", quota.tier)
    if tier not in dict(UserAIQuota.Tier.choices):
        return JsonResponse({"detail": "Unknown plan."}, status=400)
    try:
        limit = int(data.get("monthly_token_limit", quota.monthly_token_limit))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "The limit must be a whole number."}, status=400)
    if not 0 <= limit <= 100_000_000:
        return JsonResponse({"detail": "The limit must be between 0 and 100 000 000 tokens."}, status=400)
    quota.tier = tier
    quota.monthly_token_limit = limit
    if data.get("reset_usage"):
        quota.tokens_used_this_cycle = 0
    quota.save(update_fields=["tier", "monthly_token_limit", "tokens_used_this_cycle", "updated_at"])
    after = {"tier": quota.tier, "limit": quota.monthly_token_limit, "used": quota.tokens_used_this_cycle}
    audit(request, "user.ai_quota", target_type="user", target_id=u.pk, summary=f"AI allowance for {u.email}: {before['tier']}/{before['limit']} → {tier}/{limit}", before=before, after=after)
    return JsonResponse({"ok": True, **after})


@staff_required("users.coins", write=True)
def user_coins(request, user_id):
    """POST {delta, reason} → add or take coins (never below zero)."""
    if request.method != "POST":
        return method_not_allowed()
    u = get_object_or_404(User, pk=user_id)
    data, err = body(request)
    if err:
        return err
    try:
        delta = int(data.get("delta"))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Enter a whole number of coins."}, status=400)
    reason = str(data.get("reason") or "").strip()[:200]
    if not delta or abs(delta) > 100_000:
        return JsonResponse({"detail": "Change by 1 to 100 000 coins."}, status=400)
    if not reason:
        return JsonResponse({"detail": "Say why (it goes to the audit log)."}, status=400)
    stats, _ = UserStats.objects.get_or_create(user=u)
    before = stats.coins
    stats.coins = max(0, stats.coins + delta)
    stats.save(update_fields=["coins", "updated_at"])
    audit(request, "user.coins", target_type="user", target_id=u.pk, summary=f"Coins for {u.email}: {before} → {stats.coins} ({reason})", before=before, after=stats.coins, reason=reason)
    return JsonResponse({"ok": True, "coins": stats.coins})


@staff_required("staff.manage", write=True)
def user_role(request, user_id):
    """POST {role} → give or take a team role. Owners only."""
    if request.method != "POST":
        return method_not_allowed()
    u = get_object_or_404(User, pk=user_id, is_active=True)
    data, err = body(request)
    if err:
        return err
    role = str(data.get("role") or "")
    if role not in ROLES:
        return JsonResponse({"detail": "Unknown role."}, status=400)
    if u.pk == request.auth_user.pk:
        return JsonResponse({"detail": "Ask another owner to change your own role."}, status=400)
    if u.is_superuser:
        return JsonResponse({"detail": "This account is a superuser; change it on the server."}, status=400)
    before = u.staff_role
    u.staff_role = role
    u.save(update_fields=["staff_role"])
    if before and not role:
        # Leaving the team: close any open admin sessions on their devices.
        u.sudo_grants.all().delete()
    audit(request, "staff.role", target_type="user", target_id=u.pk, summary=f"{u.email}: {before or 'learner'} → {role or 'learner'}", before=before, after=role)
    return JsonResponse({"ok": True, "role": u.admin_role})


@staff_required("staff.manage", write=True)
def user_totp_reset(request, user_id):
    """POST → turn off a team member's two-factor (lost phone). Owners only."""
    if request.method != "POST":
        return method_not_allowed()
    u = get_object_or_404(User, pk=user_id)
    if u.pk == request.auth_user.pk:
        return JsonResponse({"detail": "You cannot reset your own two-factor here."}, status=400)
    u.totp_enabled = False
    u.totp_secret = ""
    u.save(update_fields=["totp_enabled", "totp_secret"])
    u.sudo_grants.all().delete()
    security.record(SecurityEvent.Kind.TOTP_DISABLED, request, user=u, by=request.auth_user.email)
    audit(request, "staff.totp_reset", target_type="user", target_id=u.pk, summary=f"Reset two-factor for {u.email}")
    return JsonResponse({"ok": True})


def _delete(request, u):
    if not can(request.auth_user, "users.delete"):
        return JsonResponse({"detail": "Only an owner can delete accounts."}, status=403)
    from ..permissions import latest_grant
    grant = latest_grant(request)
    if grant is None or grant.created_at < timezone.now() - timedelta(minutes=settings.ADMIN_SUDO_MINUTES):
        return JsonResponse({"detail": "Confirm it's you again to make changes.", "code": "sudo_required"}, status=403)
    err = _guard_team_target(request, u)
    if err:
        return err
    if u.is_superuser:
        return JsonResponse({"detail": "Superusers are removed on the server."}, status=400)
    data, err = body(request)
    if err:
        return err
    if str(data.get("confirm") or "").strip().lower() != u.email.lower():
        return JsonResponse({"detail": "Type the account's email to confirm."}, status=400)
    email, pk = u.email, u.pk
    delete_uploads(u)
    User.objects.filter(pk=pk).delete()
    security.record(SecurityEvent.Kind.ACCOUNT_DELETED, request, email=email, by=request.auth_user.email)
    audit(request, "user.deleted", target_type="user", target_id=pk, summary=f"Deleted the account {email}")
    return JsonResponse({"ok": True})


@staff_required("users.export", write=True)
def user_export(request, user_id):
    """GET → everything we hold about one person (for a data request)."""
    if request.method != "GET":
        return method_not_allowed()
    u = get_object_or_404(User, pk=user_id)
    # The same file the person gets from Settings → "Download my data".
    data = collect_user_data(u)
    audit(request, "user.exported", target_type="user", target_id=u.pk, summary=f"Exported the data of {u.email}")
    response = JsonResponse(data, json_dumps_params={"ensure_ascii": False, "indent": 1})
    response["Content-Disposition"] = f'attachment; filename="zinvest-user-{u.pk}.json"'
    return response


def _cell(value):
    """CSV cell safe to open in Excel: no formulas from user input."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@staff_required("users.export", write=True)
def users_csv(request):
    if request.method != "GET":
        return method_not_allowed()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "email", "name", "joined", "active", "role", "last_seen", "lessons_done", "coins", "startup"])
    for u in _annotated().order_by("date_joined").iterator(chunk_size=500):
        r = _row(u)
        writer.writerow([_cell(r[k]) for k in ("id", "email", "name", "date_joined", "is_active", "role", "last_seen", "lessons_done", "coins", "startup")])
    audit(request, "users.exported_csv", summary="Exported the user list (CSV)")
    response = HttpResponse("﻿" + buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="zinvest-users.csv"'
    return response
