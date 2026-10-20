"""
Derived state + serialization helpers for the learning domain.

Lock/unlock and "current" node state are computed here from persisted completion,
never stored, so the rules live in exactly one place:
  * Unit 1 is always unlocked; unit N unlocks once unit N-1's test is passed.
  * Lesson 1 of an unlocked unit is available; lesson M unlocks once M-1 completes.
"""
import re
from datetime import timedelta
from html import unescape

from django.db.models import Q

from config import languages

from .models import (
    DailyActivity,
    Lesson,
    LessonProgress,
    StudyPlan,
    Task,
    Unit,
    UnitProgress,
    UnitTestResult,
    UserStats,
)

WEEKDAYS = ["mo", "tu", "we", "th", "fr", "sa", "su"]

# The unit test's node on the map, in the words the map uses for it.
UNIT_TEST = {"en": "Unit test", "ru": "Контрольная", "uz": "Nazorat"}


def get_or_create_stats(user, today=None):
    """Fetch the stats row, zeroing a lapsed streak on the way out.

    The streak only ever grows inside ``touch_activity`` (lesson/test completion),
    so the *break* has to be detected lazily on read — same shape as the AI
    quota's cycle rollover.
    """
    stats, _ = UserStats.objects.get_or_create(user=user)
    if today is not None and stats.decay_streak(today):
        stats.save(update_fields=["day_streak", "updated_at"])
    return stats


def completed_lesson_ids(user):
    return set(
        LessonProgress.objects.filter(
            user=user, status=LessonProgress.Status.COMPLETED
        ).values_list("lesson_id", flat=True)
    )


def unit_progress_map(user):
    return {up.unit_id: up for up in UnitProgress.objects.filter(user=user)}


def unit_is_locked(index, prev_unit_completed):
    return not (index == 0 or prev_unit_completed)


# --------------------------------------------------------------------------- #
# Serializers
# --------------------------------------------------------------------------- #
def units_payload(user):
    units = list(Unit.objects.prefetch_related("lessons").all())
    completed = completed_lesson_ids(user)
    up_map = unit_progress_map(user)

    out = []
    prev_unit_completed = True
    for idx, unit in enumerate(units):
        locked = unit_is_locked(idx, prev_unit_completed)
        lessons = list(unit.lessons.all())
        total = len(lessons)
        done = sum(1 for les in lessons if les.id in completed)
        up = up_map.get(unit.id)
        test_passed = bool(up and up.test_passed)
        best = float(up.best_test_score) if up else 0.0
        out.append(
            {
                "id": str(unit.id),
                "code": unit.code,
                "title": unit.tr("title"),
                "subtitle": unit.tr("subtitle"),
                "color": unit.accent_color,
                "icon": unit.icon,
                "order": unit.order,
                "locked": locked,
                "progress": round(100 * done / total) if total else 0,
                "lessons_total": total,
                "lessons_completed": done,
                "test": {
                    "available": (not locked) and total > 0 and done == total,
                    "best_score": round(best * 100),
                    "passed": test_passed,
                },
            }
        )
        prev_unit_completed = test_passed
    return out


def unit_lock_map(user):
    """{unit_id: locked} — walks the order chain once instead of per lookup."""
    up_map = unit_progress_map(user)
    out = {}
    prev_completed = True
    for idx, u in enumerate(Unit.objects.all()):
        out[u.id] = unit_is_locked(idx, prev_completed)
        prev_completed = bool(up_map.get(u.id) and up_map[u.id].test_passed)
    return out


def _unit_locked_for(user, unit):
    """Whether a specific unit is locked for this user."""
    return unit_lock_map(user).get(unit.id, True)


def study_plan_payload(user, unit, unit_locked=None, completed=None):
    if completed is None:
        completed = completed_lesson_ids(user)
    if unit_locked is None:
        unit_locked = _unit_locked_for(user, unit)
    lessons = list(unit.lessons.all())

    nodes = []
    reachable = not unit_locked
    current_assigned = False
    for lesson in lessons:
        if lesson.id in completed:
            state = "completed"
        elif reachable and not current_assigned:
            state = "current"
            current_assigned = True
            reachable = False
        else:
            state = "locked"
            reachable = False
        nodes.append(
            {
                "id": str(lesson.id),
                "title": lesson.tr("title"),
                "state": state,
                "kind": "lesson",
                "coin_reward": lesson.coin_reward,
                "minutes": lesson.estimated_minutes,
            }
        )

    # Terminal unit-test node.
    up = UnitProgress.objects.filter(user=user, unit=unit).first()
    all_done = bool(lessons) and all(les.id in completed for les in lessons)
    if up and up.test_passed:
        test_state = "completed"
    elif all_done and not unit_locked:
        test_state = "current"
    else:
        test_state = "locked"
    nodes.append({"id": str(unit.id), "title": languages.pick(UNIT_TEST), "state": test_state, "kind": "test"})

    return {
        "unit": {
            "id": str(unit.id),
            "code": unit.code,
            # The map dresses each unit in its own scenery, keyed by slug.
            "slug": unit.slug,
            "title": unit.tr("title"),
            "subtitle": unit.tr("subtitle"),
            "color": unit.accent_color,
            "icon": unit.icon,
            "locked": unit_locked,
        },
        "nodes": nodes,
    }


def personalised_plan_payload(user, plan):
    """Render a generated plan as unit-grouped node chains.

    Sequencing follows the *plan* order rather than unit order: the first lesson
    the learner hasn't finished is "current", everything after it is upcoming.
    Units are grouped by first appearance so the scrolled map still reads as
    categories. Returns None if the plan has no items (caller falls back).
    """
    items = list(plan.items.select_related("lesson", "lesson__unit"))
    if not items:
        return None

    completed = completed_lesson_ids(user)
    current_id = next((it.lesson_id for it in items if it.lesson_id not in completed), None)

    groups, order = {}, []
    for it in items:
        unit = it.lesson.unit
        if unit.id not in groups:
            groups[unit.id] = {"unit": unit, "nodes": []}
            order.append(unit.id)
        if it.lesson_id in completed:
            state = "completed"
        elif it.lesson_id == current_id:
            state = "current"
        else:
            state = "locked"
        groups[unit.id]["nodes"].append(
            {
                "id": str(it.lesson_id),
                "title": it.lesson.tr("title"),
                "state": state,
                "kind": "lesson",
                "coin_reward": it.lesson.coin_reward,
                "minutes": it.lesson.estimated_minutes,
                "reason": it.reason,
            }
        )

    up_map = unit_progress_map(user)
    units_out = []
    for uid in order:
        unit = groups[uid]["unit"]
        nodes = groups[uid]["nodes"]
        up = up_map.get(uid)
        if up and up.test_passed:
            test_state = "completed"
        elif all(n["state"] == "completed" for n in nodes):
            test_state = "current"
        else:
            test_state = "locked"
        nodes.append(
            {"id": str(unit.id), "title": languages.pick(UNIT_TEST), "state": test_state, "kind": "test"}
        )
        units_out.append(
            {
                "unit": {
                    "id": str(unit.id),
                    "code": unit.code,
                    "slug": unit.slug,
                    "title": unit.tr("title"),
                    "subtitle": unit.tr("subtitle"),
                    "color": unit.accent_color,
                    "icon": unit.icon,
                    # The plan's own order is the gate here, not unit unlocking.
                    "locked": False,
                },
                "nodes": nodes,
            }
        )

    return {
        "units": units_out,
        "source": plan.source,
        "level": plan.level,
        "rationale": plan.rationale,
    }


def full_study_plan_payload(user):
    """Every node in one response, for the continuously-scrolled map.

    Uses the learner's personalised plan when they have one; otherwise the
    default unit-by-unit chain, so the map works before onboarding runs.
    """
    plan = (
        StudyPlan.objects.filter(user=user)
        .prefetch_related("items__lesson__unit")
        .first()
    )
    if plan:
        payload = personalised_plan_payload(user, plan)
        if payload:
            return payload

    locks = unit_lock_map(user)
    completed = completed_lesson_ids(user)
    units = Unit.objects.prefetch_related("lessons").all()
    return {
        "units": [
            study_plan_payload(user, unit, unit_locked=locks.get(unit.id, True), completed=completed)
            for unit in units
        ],
        "source": "default",
        "level": "",
        "rationale": "",
    }


def next_step_payload(user):
    """The one thing to do next, matching the "current" node on the study map.

    {"kind": "lesson" | "test", "id", "title", "unit_id", "unit_title"} or
    {"kind": "done"} once every node is completed.
    """
    plan = full_study_plan_payload(user)
    for group in plan["units"]:
        unit = group["unit"]
        for node in group["nodes"]:
            if node["state"] == "current":
                lessons = [n for n in group["nodes"] if n["kind"] == "lesson"]
                return {
                    "kind": node["kind"],
                    "id": node["id"],
                    "title": unit["title"] if node["kind"] == "test" else node["title"],
                    "unit_id": unit["id"],
                    "unit_title": unit["title"],
                    "unit_code": unit.get("code", ""),
                    "unit_color": unit.get("color", "brand"),
                    "unit_icon": unit.get("icon", ""),
                    # Lessons only: the unit test is the gate, not a step in the count.
                    "unit_done": sum(1 for n in lessons if n["state"] == "completed"),
                    "unit_total": len(lessons),
                    "coin_reward": node.get("coin_reward", 0),
                    "minutes": node.get("minutes"),
                }
    return {"kind": "done"}


def today_plan_payload(user, today):
    """Today's short deck for the dashboard: the next study step, one question
    to the AI and one entry in the startup's books. Each card knows whether it
    was already done today, so the deck can be "cleared" by the evening.
    """
    from ai_engine.models import AIUsageLog
    from startup.models import CashFlowEntry

    step = next_step_payload(user)
    studied_today = (
        LessonProgress.objects.filter(user=user, status=LessonProgress.Status.COMPLETED, completed_at__date=today).exists()
        or UnitTestResult.objects.filter(user=user, created_at__date=today).exists()
    )
    if step["kind"] == "done":
        study = {"key": "challenges", "minutes": 10, "done": studied_today}
    else:
        study = {
            "key": step["kind"],
            "id": step["id"],
            "unit_id": step["unit_id"],
            "title": step["title"],
            "unit_title": step["unit_title"],
            "unit_code": step["unit_code"],
            "unit_color": step["unit_color"],
            "unit_icon": step["unit_icon"],
            "unit_done": step["unit_done"],
            "unit_total": step["unit_total"],
            "coins": step.get("coin_reward", 0),
            # The lesson's own estimate; the unit test has none, and takes ~7.
            "minutes": (step.get("minutes") or 5) if step["kind"] == "lesson" else 7,
            "done": studied_today,
        }
    cards = [
        study,
        {
            "key": "ai",
            "minutes": 2,
            "done": AIUsageLog.objects.filter(user=user, feature=AIUsageLog.Feature.ADVISOR, created_at__date=today).exists(),
        },
        {
            "key": "startup",
            "minutes": 3,
            "done": CashFlowEntry.objects.filter(user=user, created_at__date=today).exists(),
        },
    ]
    return {
        "cards": cards,
        "done": sum(1 for c in cards if c["done"]),
        "total": len(cards),
        "minutes_left": sum(c["minutes"] for c in cards if not c["done"]),
    }


def lessons_catalog_payload(user):
    """Every lesson grouped by unit, freely browsable regardless of plan order.

    The study plan is the *recommended* linear route; this catalogue is the
    "open anything" view, so nothing here is gated — only annotated.
    """
    completed = completed_lesson_ids(user)
    started = set(
        LessonProgress.objects.filter(user=user)
        .exclude(status=LessonProgress.Status.COMPLETED)
        .values_list("lesson_id", flat=True)
    )
    out = []
    for unit in Unit.objects.prefetch_related("lessons").all():
        lessons = list(unit.lessons.all())
        out.append(
            {
                "id": str(unit.id),
                "code": unit.code,
                "title": unit.tr("title"),
                "subtitle": unit.tr("subtitle"),
                "color": unit.accent_color,
                "icon": unit.icon,
                "lessons_total": len(lessons),
                "lessons_completed": sum(1 for les in lessons if les.id in completed),
                "lessons": [
                    {
                        "id": str(les.id),
                        "title": les.tr("title"),
                        "order": les.order,
                        "coin_reward": les.coin_reward,
                        "estimated_minutes": les.estimated_minutes,
                        "status": (
                            "completed"
                            if les.id in completed
                            else "in_progress" if les.id in started else "not_started"
                        ),
                    }
                    for les in lessons
                ],
            }
        )
    return out


def lesson_is_locked(user, lesson):
    if _unit_locked_for(user, lesson.unit):
        return True
    completed = completed_lesson_ids(user)
    earlier = lesson.unit.lessons.filter(order__lt=lesson.order)
    return any(les.id not in completed for les in earlier)


_TAG = re.compile(r"<[^>]+>")
# Markup the lesson itself never contains: its presence means the learner
# formatted or added something of their own.
_OWN_MARKUP = re.compile(r"<(strong|b|em|i|u|s|mark|code|a|img|blockquote|ol|h[3-6]|pre|hr|span|div|input|label|math)\b", re.I)


def _words(html):
    return " ".join(unescape(_TAG.sub(" ", html or "")).split())


def _canvas_words(payload):
    """The words of a lesson canvas in reading order, as the document view shows them."""
    parts = []
    for element in (payload or {}).get("elements", []):
        if element.get("type") == "text" and str(element.get("text") or "").strip():
            parts.append(str(element["text"]).strip().lstrip("•").strip())
        elif element.get("type") == "table":
            parts.extend(str(cell) for row in element.get("rows") or [] for cell in row)
    return " ".join(" ".join(parts).split())


def untouched_copy(lesson, edited):
    """
    True when saved "edits" are only the lesson as it was delivered: the same
    words, in one of its languages, and no formatting of the learner's own.
    Such a copy would pin the lesson to the language it was first opened in,
    so it is not served — the lesson follows the switcher instead.
    """
    if not edited:
        return False
    words = _words(edited)
    # A lesson written as HTML: the copy is untouched when its words are the
    # lesson's own in any language, whatever markup came with them.
    bodies = [lesson.content_html] + [(v or {}).get("content_html") for v in (lesson.i18n or {}).values()]
    if any(words == _words(b) for b in bodies if b):
        return True
    if _OWN_MARKUP.search(edited):
        return False
    payloads = [lesson.canvas_payload] + [(v or {}).get("canvas_payload") for v in (lesson.i18n or {}).values()]
    return any(words == _canvas_words(p) for p in payloads if p)


def lesson_payload(user, lesson):
    lp = LessonProgress.objects.filter(user=user, lesson=lesson).first()
    edited = (lp.edited_content if lp else "") or ""
    if untouched_copy(lesson, edited):
        edited = ""
    nxt = lesson.unit.lessons.filter(order__gt=lesson.order).order_by("order").first()
    prv = lesson.unit.lessons.filter(order__lt=lesson.order).order_by("-order").first()
    return {
        "id": str(lesson.id),
        "unit_id": str(lesson.unit_id),
        "title": lesson.tr("title"),
        "coin_reward": lesson.coin_reward,
        "estimated_minutes": lesson.estimated_minutes,
        "status": lp.status if lp else LessonProgress.Status.NOT_STARTED,
        # Advisory only: the lesson is still readable (the catalogue lets you open
        # anything), but the study plan uses this to show it as off-route.
        "locked": lesson_is_locked(user, lesson),
        # The lesson body: HTML when the lesson has it (the client renders it
        # directly), otherwise the older drawn layout.
        "content_html": lesson.tr("content_html"),
        "canvas_payload": {} if lesson.content_html else lesson.tr("canvas_payload"),
        # A non-empty string means the user has saved their own edits — the client
        # should render this in preference to the canvas-derived HTML.
        "edited_content": edited,
        "next_id": str(nxt.id) if nxt else None,
        "prev_id": str(prv.id) if prv else None,
    }


# --------------------------------------------------------------------------- #
# Streak / calendar / stats
# --------------------------------------------------------------------------- #
def record_activity(user, stats, today):
    """Register today's activity (idempotent), advance the streak on the row and,
    on the first activity of the day, add the streak day's AI bonus."""
    from django.conf import settings

    from ai_engine.quota import add_bonus  # local: ai_engine is a sibling app

    DailyActivity.objects.get_or_create(user=user, date=today)
    if stats.touch_activity(today):
        add_bonus(user, settings.AI_BONUS_PER_STREAK_DAY)


def week_calendar(user, today):
    monday = today - timedelta(days=today.weekday())
    active = set(
        DailyActivity.objects.filter(
            user=user, date__gte=monday, date__lte=monday + timedelta(days=6)
        ).values_list("date", flat=True)
    )
    return [
        {"day": WEEKDAYS[i], "date": (monday + timedelta(days=i)).isoformat(), "active": (monday + timedelta(days=i)) in active}
        for i in range(7)
    ]


def task_payload(task):
    return {
        "id": str(task.id),
        "title": task.title,
        "done": task.done,
        "order": task.order,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


def today_tasks_queryset(user, today):
    """Open tasks plus the ones ticked off today — yesterday's fall away on their own."""
    return Task.objects.filter(user=user).filter(
        Q(done=False) | Q(completed_at__date=today)
    )


def tasks_payload(user, today):
    return [task_payload(t) for t in today_tasks_queryset(user, today)]


def stats_payload(user, today):
    stats = get_or_create_stats(user, today)
    completed = completed_lesson_ids(user)
    total_lessons = Lesson.objects.count()
    units_total = Unit.objects.count()
    units_completed = UnitProgress.objects.filter(user=user, test_passed=True).count()
    quizzes_done = (
        UnitTestResult.objects.filter(user=user).values("unit_id").distinct().count()
    )
    best = (
        UnitProgress.objects.filter(user=user)
        .order_by("-best_test_score")
        .values_list("best_test_score", flat=True)
        .first()
    )
    best_score = round(float(best) * 100) if best else 0

    from . import league as league_service

    return {
        "league": league_service.snapshot(user),
        "coins": stats.coins,
        "day_streak": stats.day_streak,
        "longest_streak": stats.longest_streak,
        # Today's streak day is earned by finishing a lesson or a unit test — the
        # client uses this to show today as "pending" rather than already banked.
        "streak_active_today": stats.is_active_on(today),
        "learning_progress": round(100 * len(completed) / total_lessons) if total_lessons else 0,
        "units_completed": units_completed,
        "units_total": units_total,
        "quizzes_done": quizzes_done,
        "best_score": best_score,
        "coins_earned_week": stats.weekly_xp,
        "weekly_rank": stats.weekly_rank,
        "last_activity_date": stats.last_activity_date.isoformat() if stats.last_activity_date else None,
        "week": week_calendar(user, today),
        "goal": {
            "financial_goal": stats.financial_goal,
            "target_score": stats.target_score,
            "current_score": best_score,
        },
        "tasks": tasks_payload(user, today),
    }
