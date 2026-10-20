"""
The System page and the Startups list of the admin panel.

System: how this deployment is set up, as a checklist (DEBUG, keys, cookies,
two-factor, mail, Google, Gemini, the database and its migrations) plus who
can sign in how. Every value is a yes/no or a count, never a secret.

Startups: every founder's workspace and the market check from the intake.
"""
import platform
import sys
import time
from datetime import timedelta

import django
from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.models import User
from startup.models import StartupProfile

from ..models import PlatformSettings
from ..permissions import staff_required
from .common import iso, method_not_allowed, paginate

OK, WARN, FAIL, INFO = "ok", "warn", "fail", "info"


def _check(key, status, value=None):
    return {"key": key, "status": status, "value": value}


def _db():
    """Engine, one round trip's latency, and migrations not yet applied."""
    started = time.perf_counter()
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    latency = round((time.perf_counter() - started) * 1000, 1)
    executor = MigrationExecutor(connection)
    pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
    return connection.vendor, latency, [f"{m.app_label}.{m.name}" for m, _ in pending]


def _staff_users():
    return User.objects.filter(is_active=True).filter(Q(is_superuser=True) | ~Q(staff_role=""))


@staff_required("system.view")
def system(request):
    if request.method != "GET":
        return method_not_allowed()
    vendor, latency, pending = _db()
    staff = _staff_users()
    staff_no_2fa = staff.filter(totp_enabled=False).count()
    mail_ready = "smtp" in settings.EMAIL_BACKEND and bool(settings.EMAIL_HOST and settings.EMAIL_HOST_USER)
    telegram_token = bool(getattr(settings, "TELEGRAM_BOT_TOKEN", ""))
    origin = settings.APP_ORIGIN

    checks = [
        # Security
        _check("debug_off", FAIL if settings.DEBUG else OK),
        _check("https_origin", OK if origin.startswith("https://") else (INFO if settings.DEBUG else FAIL), origin),
        _check("secure_cookies", OK if settings.REFRESH_COOKIE_SECURE else (INFO if settings.DEBUG else FAIL)),
        _check("allowed_hosts", FAIL if "*" in settings.ALLOWED_HOSTS else OK, len(settings.ALLOWED_HOSTS)),
        _check("admin_2fa_required", OK if settings.ADMIN_REQUIRE_2FA else (INFO if settings.DEBUG else FAIL)),
        _check("staff_2fa", WARN if staff_no_2fa else OK, staff_no_2fa),
        _check("django_admin_off", WARN if getattr(settings, "DJANGO_ADMIN_ENABLED", False) and not settings.DEBUG else OK),
        _check("superusers", WARN if User.objects.filter(is_superuser=True, is_active=True).exists() else OK,
               User.objects.filter(is_superuser=True, is_active=True).count()),
        _check("access_ttl", OK if settings.ACCESS_TOKEN_TTL <= timedelta(minutes=30) else WARN,
               int(settings.ACCESS_TOKEN_TTL.total_seconds() // 60)),
        _check("telegram_webhook_secret",
               INFO if not telegram_token else (OK if getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") else FAIL)),
        # Sign-in
        _check("mail", OK if mail_ready else WARN),
        _check("login_codes", OK if settings.LOGIN_EMAIL_CODE and mail_ready else (FAIL if settings.LOGIN_EMAIL_CODE else WARN)),
        _check("google", OK if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET else WARN),
        _check("registration", INFO, PlatformSettings.current().registration_open),
        # Services
        _check("gemini", OK if settings.GEMINI_API_KEY else FAIL),
        _check("database", OK if vendor == "postgresql" or settings.DEBUG else WARN, vendor),
        _check("db_latency", OK if latency < 50 else (WARN if latency < 250 else FAIL), latency),
        _check("migrations", FAIL if pending else OK, pending[:10]),
    ]

    users = User.objects.all()
    accounts = {
        "total": users.count(),
        "google_linked": users.exclude(google_sub="").count(),
        "passwordless": users.filter(password__startswith="!").count(),
        "email_verified": users.filter(email_verified_at__isnull=False).count(),
        "consented": users.filter(terms_accepted_at__isnull=False).count(),
        "staff": staff.count(),
        "staff_without_2fa": staff_no_2fa,
    }
    runtime = {
        "python": platform.python_version(),
        "django": django.get_version(),
        "region": _env("VERCEL_REGION"),
        "commit": _env("VERCEL_GIT_COMMIT_SHA")[:7],
        "deployment": _env("VERCEL_URL"),
        "platform": sys.platform,
        "server_time": iso(timezone.now()),
    }
    return JsonResponse({"checks": checks, "accounts": accounts, "runtime": runtime})


def _env(name):
    import os

    return os.environ.get(name, "")


# --------------------------------------------------------------------------- #
# Startups
# --------------------------------------------------------------------------- #
def _research(p):
    blocks = p.blocks if isinstance(p.blocks, dict) else {}
    research = blocks.get("research")
    return research if isinstance(research, dict) else None


def _answers(p):
    return p.onboarding if isinstance(p.onboarding, dict) else {}


def _startup_row(p):
    research = _research(p) or {}
    answers = _answers(p)
    return {
        "id": str(p.id),
        "name": p.name or answers.get("name") or "",
        "owner": {"id": str(p.user_id), "email": p.user.email, "name": p.user.full_name},
        "location": answers.get("location", ""),
        "stage": answers.get("stage", ""),
        "market": answers.get("market", ""),
        "team": answers.get("team", ""),
        "verdict": research.get("verdict", ""),
        "searched": bool(research.get("searched")),
        "competitors": len(research.get("competitors") or []),
        "onboarded": p.onboarding_completed,
        "public": p.public_visible,
        "created_at": iso(p.created_at),
        "updated_at": iso(p.updated_at),
    }


VERDICTS = ("strong", "promising", "uncertain", "weak")


@staff_required("startups.view")
def startups(request):
    if request.method != "GET":
        return method_not_allowed()
    qs = StartupProfile.objects.select_related("user").order_by("-updated_at")
    q = request.GET.get("q", "").strip()[:120]
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(user__email__icontains=q))
    verdict = request.GET.get("verdict", "")
    if verdict in VERDICTS:
        qs = qs.filter(blocks__research__verdict=verdict)
    elif verdict == "none":
        qs = qs.exclude(blocks__has_key="research")
    page = paginate(request, qs, _startup_row)
    all_profiles = StartupProfile.objects.all()
    counts = {v: all_profiles.filter(blocks__research__verdict=v).count() for v in VERDICTS}
    page["summary"] = {
        "total": all_profiles.count(),
        "onboarded": all_profiles.filter(onboarding_completed=True).count(),
        "checked": sum(counts.values()),
        "public": all_profiles.filter(public_visible=True).count(),
        "verdicts": counts,
        "week": all_profiles.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
    }
    return JsonResponse(page)


@staff_required("startups.view")
def startup_detail(request, profile_id):
    if request.method != "GET":
        return method_not_allowed()
    p = get_object_or_404(StartupProfile.objects.select_related("user"), pk=profile_id)
    row = _startup_row(p)
    row["answers"] = _answers(p)
    row["research"] = _research(p)
    row["analysis"] = (p.blocks or {}).get("analysis", "") if isinstance(p.blocks, dict) else ""
    row["counts"] = {
        "employees": p.user.startup_employees.count(),
        "products": p.user.startup_products.count(),
        "todos": p.user.startup_todos.count(),
    }
    return JsonResponse(row)
