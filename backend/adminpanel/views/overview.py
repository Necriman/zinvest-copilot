"""
The numbers a startup team looks at every morning: growth, activity,
activation, learning, the founder network and AI spend.

"Visited" counts people whose app refreshed its session that day (every open
tab does so at least every 15 minutes), "studied" counts people who finished
something in a lesson or a test.
"""
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone

from accounts.models import RefreshToken, SecurityEvent, User
from ai_engine.models import AIUsageLog
from learning.models import DailyActivity, LessonProgress, OnboardingAssessment, UnitTestResult
from startup.models import BusinessPost, FounderConnection, FounderMessage, StartupProfile

from ..models import Report
from ..permissions import staff_required
from .common import method_not_allowed


def _pct(part, whole):
    return round(100 * part / whole) if whole else 0


def _series(qs, field, days, *, distinct_user=False):
    """{date: count} for the last ``days`` days, zero-filled."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    rows = (
        qs.filter(**{f"{field}__date__gte": start})
        .annotate(day=TruncDate(field))
        .values("day")
        .annotate(n=Count("user", distinct=True) if distinct_user else Count("pk"))
    )
    by_day = {r["day"]: r["n"] for r in rows}
    return [{"date": (start + timedelta(days=i)).isoformat(), "value": by_day.get(start + timedelta(days=i), 0)} for i in range(days)]


def _visitors(since):
    return RefreshToken.objects.filter(created_at__gte=since).values("user").distinct().count()


@staff_required("overview.view")
def overview(request):
    if request.method != "GET":
        return method_not_allowed()
    now = timezone.now()
    today = timezone.localdate()
    day, week, month = now - timedelta(days=1), now - timedelta(days=7), now - timedelta(days=30)

    users = User.objects.all()
    total = users.count()
    new_week = users.filter(date_joined__gte=week).count()
    new_prev_week = users.filter(date_joined__gte=week - timedelta(days=7), date_joined__lt=week).count()

    # Week-one retention: people who joined 8-14 days ago and came back in the last 7 days.
    cohort = users.filter(date_joined__gte=now - timedelta(days=14), date_joined__lt=now - timedelta(days=7))
    cohort_size = cohort.count()
    returned = cohort.filter(refresh_tokens__created_at__gte=week).distinct().count()

    onboarded = OnboardingAssessment.objects.filter(completed_at__isnull=False).count()
    learned_any = LessonProgress.objects.filter(status=LessonProgress.Status.COMPLETED).values("user").distinct().count()
    tests_week = UnitTestResult.objects.filter(created_at__gte=week)
    tests_total = tests_week.count()
    tests_passed = tests_week.filter(passed=True).count()

    ai_month = AIUsageLog.objects.filter(created_at__gte=month)
    ai_tokens = ai_month.aggregate(i=Sum("input_tokens"), o=Sum("output_tokens"))

    data = {
        "generated_at": now.isoformat(),
        "users": {
            "total": total,
            "active_accounts": users.filter(is_active=True).count(),
            "disabled": users.filter(is_active=False).count(),
            "new_today": users.filter(date_joined__date=today).count(),
            "new_week": new_week,
            "new_prev_week": new_prev_week,
            "new_month": users.filter(date_joined__gte=month).count(),
        },
        "activity": {
            "visited_day": _visitors(day),
            "visited_week": _visitors(week),
            "visited_month": _visitors(month),
            "studied_day": DailyActivity.objects.filter(date=today).count(),
            "studied_week": DailyActivity.objects.filter(date__gt=today - timedelta(days=7)).values("user").distinct().count(),
            "retention_week1": _pct(returned, cohort_size),
            "retention_cohort": cohort_size,
        },
        "activation": {
            "onboarded": onboarded,
            "onboarded_pct": _pct(onboarded, total),
            "first_lesson": learned_any,
            "first_lesson_pct": _pct(learned_any, total),
            "startup_profiles": StartupProfile.objects.filter(onboarding_completed=True).count(),
        },
        "learning": {
            "lessons_week": LessonProgress.objects.filter(completed_at__gte=week).count(),
            "lessons_month": LessonProgress.objects.filter(completed_at__gte=month).count(),
            "tests_week": tests_total,
            "tests_pass_pct": _pct(tests_passed, tests_total),
        },
        "network": {
            "public_profiles": StartupProfile.objects.filter(public_visible=True).count(),
            "posts_week": BusinessPost.objects.filter(created_at__gte=week).count(),
            "messages_week": FounderMessage.objects.filter(created_at__gte=week).count(),
            "connections_week": FounderConnection.objects.filter(created_at__gte=week).count(),
            "open_reports": Report.objects.filter(status=Report.Status.OPEN).count(),
        },
        "ai": {
            "requests_month": ai_month.count(),
            "tokens_month": (ai_tokens["i"] or 0) + (ai_tokens["o"] or 0),
            "users_month": ai_month.values("user").distinct().count(),
        },
        # How people sign in, and what they agreed to at sign-up.
        "signin": {
            "google_linked": users.exclude(google_sub="").count(),
            "passwordless": users.filter(password__startswith="!").count(),
            "email_verified": users.filter(email_verified_at__isnull=False).count(),
            "email_verified_pct": _pct(users.filter(email_verified_at__isnull=False).count(), total),
            "consented": users.filter(terms_accepted_at__isnull=False).count(),
        },
        # The market check from the startup intake.
        "startups": {
            "checked": StartupProfile.objects.filter(blocks__has_key="research").count(),
            "verdicts": {
                v: StartupProfile.objects.filter(blocks__research__verdict=v).count()
                for v in ("strong", "promising", "uncertain", "weak")
            },
        },
        "security": {
            "failed_logins_day": SecurityEvent.objects.filter(kind=SecurityEvent.Kind.LOGIN_FAILED, created_at__gte=day).count(),
            "lockouts_day": SecurityEvent.objects.filter(kind=SecurityEvent.Kind.LOGIN_LOCKED, created_at__gte=day).count(),
            "token_reuse_week": SecurityEvent.objects.filter(kind=SecurityEvent.Kind.TOKEN_REUSE, created_at__gte=week).count(),
        },
        "series": {
            "signups": _series(User.objects.all(), "date_joined", 30),
            "visitors": _series(RefreshToken.objects.all(), "created_at", 30, distinct_user=True),
            "lessons": _series(LessonProgress.objects.filter(completed_at__isnull=False), "completed_at", 30),
        },
        "top_units": list(
            LessonProgress.objects.filter(status=LessonProgress.Status.COMPLETED, completed_at__gte=month)
            .values("lesson__unit__title").annotate(n=Count("pk")).order_by("-n")[:5]
        ),
    }
    return JsonResponse(data)
