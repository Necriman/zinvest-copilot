"""
Everything Zinvest holds about one person, as plain JSON.

Used by "Download my data" in Settings (GET /api/auth/me/export) and by the
admin panel's data-request export, so both always hand over the same thing.
Secrets are left out on purpose: the password hash, the two-factor secret and
refresh-token hashes are not "data about you", and handing them out would only
make a leaked export more dangerous. The bot never stores receipt photos or
voice notes, and AI conversations are not stored either (only how many tokens
each request used), so neither can appear here.
"""
from django.utils import timezone

from ai_engine.models import AIUsageLog, UserAIQuota
from learning.models import (
    DailyRun,
    LeagueMembership,
    LessonProgress,
    OnboardingAssessment,
    PracticeAttempt,
    PredictionAttempt,
    StudyPlan,
    Task,
    UnitProgress,
    UnitTestResult,
    UserStats,
)
from notes.models import Note
from copilot.models import CopilotAction
from startup.models import (
    Assignment,
    BusinessPost,
    CashFlowEntry,
    Employee,
    FounderConnection,
    FounderMessage,
    Product,
    StartupProfile,
    StartupTodo,
)
from telegrambot.models import TelegramLink

from .models import RefreshToken, SecurityEvent


def _iso(value):
    return value.isoformat() if value else None


def _money(value):
    return str(value) if value is not None else None


def _sessions(user):
    # A refresh token is rotated on every refresh, so one sign-in is a family of
    # rows; one entry per sign-in is what a person would recognise.
    families = {}
    for t in RefreshToken.objects.filter(user=user).order_by("created_at"):
        f = families.setdefault(t.family_id, {"device": t.device_name, "ip": t.ip_address, "signed_in_at": _iso(t.created_at)})
        f["last_used_at"] = _iso(t.created_at)
        f["ended"] = t.is_revoked or t.expires_at <= timezone.now()
    return list(families.values())


def collect(user):
    stats = UserStats.objects.filter(user=user).first()
    assessment = OnboardingAssessment.objects.filter(user=user).first()
    plan = StudyPlan.objects.filter(user=user).prefetch_related("items__lesson").first()
    startup = StartupProfile.objects.filter(user=user).first()
    quota = UserAIQuota.objects.filter(user=user).first()
    link = TelegramLink.objects.filter(user=user).first()

    return {
        "exported_at": timezone.now().isoformat(),
        "account": {
            "id": str(user.pk),
            "email": user.email,
            "email_verified_at": _iso(user.email_verified_at),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "joined": _iso(user.date_joined),
            "active": user.is_active,
            "theme": user.theme,
            "brand_color": user.brand_color,
            "has_avatar": bool(user.avatar),
            "two_factor": user.totp_enabled,
        },
        "progress": {
            "coins": stats.coins if stats else 0,
            "day_streak": stats.day_streak if stats else 0,
            "longest_streak": stats.longest_streak if stats else 0,
            "financial_goal": stats.financial_goal if stats else "",
            "league_weeks": [
                {"week": _iso(m.week_start), "division": m.division, "points": m.points, "rank": m.rank, "result": m.result}
                for m in LeagueMembership.objects.filter(user=user).order_by("week_start")
            ],
        },
        "learning": {
            "onboarding": {
                "answers": assessment.answers,
                "quiz_score": assessment.quiz_score,
                "level": assessment.level,
                "completed_at": _iso(assessment.completed_at),
            } if assessment else None,
            "study_plan": {
                "level": plan.level,
                "rationale": plan.rationale,
                "generated_at": _iso(plan.generated_at),
                "lessons": [item.lesson.title for item in plan.items.all()],
            } if plan else None,
            "lessons": [
                {
                    "lesson": p.lesson.title,
                    "status": p.status,
                    "completed_at": _iso(p.completed_at),
                    "worksheet_answers": p.worksheet_answers,
                    "your_edited_copy": p.edited_content or None,
                }
                for p in LessonProgress.objects.filter(user=user).select_related("lesson")
            ],
            "units": [
                {"unit": u.unit.title, "status": u.status, "best_test_score": u.best_test_score, "passed": u.test_passed}
                for u in UnitProgress.objects.filter(user=user).select_related("unit")
            ],
            "tests": [
                {"unit": t.unit.title, "score": t.score, "passed": t.passed, "answers": t.answers, "at": _iso(t.created_at)}
                for t in UnitTestResult.objects.filter(user=user).select_related("unit")
            ],
            "tasks": [
                {"title": t.title, "done": t.done, "completed_at": _iso(t.completed_at)}
                for t in Task.objects.filter(user=user)
            ],
            "daily_runs": [
                {"date": _iso(r.date), "correct": r.correct, "answered": len(r.answers or []), "coins": r.coins_awarded}
                for r in DailyRun.objects.filter(user=user).order_by("date")
            ],
            "practice_answers": PracticeAttempt.objects.filter(user=user).count(),
            "market_predictions": [
                {"choice": p.choice, "correct": p.correct, "at": _iso(p.created_at)}
                for p in PredictionAttempt.objects.filter(user=user).order_by("created_at")
            ],
        },
        "notes": [
            {"title": n.title, "content": n.content, "updated_at": _iso(n.updated_at)}
            for n in Note.objects.filter(user=user)
        ],
        "startup": {
            "profile": {
                "name": startup.name,
                "industry": startup.industry,
                "currency": startup.currency,
                "operating_mode": startup.operating_mode,
                "locations": startup.locations,
                "demand": startup.demand,
                "onboarding": startup.onboarding,
                "public": startup.public_visible,
                "public_summary": startup.public_summary,
                "roadmap": startup.roadmap,
            } if startup else None,
            "cashflow": [
                {"type": e.entry_type, "category": e.category, "amount": _money(e.amount), "description": e.description, "date": _iso(e.occurred_on)}
                for e in CashFlowEntry.objects.filter(user=user)
            ],
            "employees": [
                {"name": e.full_name, "position": e.position, "role": e.role, "team": e.team, "salary": _money(e.salary)}
                for e in Employee.objects.filter(user=user)
            ],
            "assignments": [
                {"employee": a.employee.full_name, "title": a.title, "done": a.done, "start": _iso(a.start_date), "end": _iso(a.end_date)}
                for a in Assignment.objects.filter(employee__user=user).select_related("employee")
            ],
            "products": [
                {"name": p.name, "kind": p.kind, "price": _money(p.price)}
                for p in Product.objects.filter(user=user)
            ],
            "todos": [{"title": t.title, "done": t.done} for t in StartupTodo.objects.filter(user=user)],
            "copilot": {
                "settings_and_results": startup.copilot if startup else {},
                "actions": [
                    {"kind": a.kind, "status": a.status, "summary": a.summary, "proposal": a.payload,
                     "outcome": a.outcome, "at": _iso(a.created_at), "decided_at": _iso(a.decided_at)}
                    for a in CopilotAction.objects.filter(user=user)
                ],
            },
            "posts": [
                {"title": p.title, "text": p.text, "at": _iso(p.created_at)}
                for p in BusinessPost.objects.filter(user=user)
            ],
            "connections": FounderConnection.objects.filter(sender=user).count()
            + FounderConnection.objects.filter(recipient=user).count(),
            "messages_sent": [
                {"text": m.text, "at": _iso(m.created_at)} for m in FounderMessage.objects.filter(sender=user)
            ],
        },
        "telegram": {
            "username": link.username,
            "language": link.lang,
            "nudges": link.nudges,
            "nudge_hour": link.nudge_hour,
            "linked_at": _iso(link.created_at),
        } if link else None,
        "ai": {
            "plan": quota.tier if quota else None,
            "tokens_used_this_cycle": quota.tokens_used_this_cycle if quota else 0,
            "requests": [
                {"feature": a.feature, "tokens": a.total_tokens, "at": _iso(a.created_at)}
                for a in AIUsageLog.objects.filter(user=user).order_by("created_at")
            ],
        },
        "security": {
            "sessions": _sessions(user),
            "events": [
                {"kind": e.kind, "ip": e.ip_address, "at": _iso(e.created_at)}
                for e in SecurityEvent.objects.filter(user=user).order_by("created_at")
            ],
        },
    }
