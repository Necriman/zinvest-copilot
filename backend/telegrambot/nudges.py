"""
The bear's check-in.

Rules it obeys, so it stays welcome:
  * at most one message a day, and only around the hour the learner chose;
  * never on a day they already studied — the nudge is for empty days;
  * never the same line twice running (texts.nudge_line remembers the last);
  * "Later" silences it for an hour, "Not today" until tomorrow;
  * after two weeks of silence it quietly drops to the Sunday summary only,
    instead of writing into the void every evening;
  * Sunday is a recap of the week, not a nudge — good news, not pressure.
Each reminder ends with a matching bear sticker.
"""
import logging
import random
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from config import languages
from learning import league as league_service
from learning import services as learning_services
from learning.models import DailyActivity, LessonProgress

from . import api, reactions, texts
from .handlers import _lesson_url
from .models import TelegramLink

log = logging.getLogger("telegrambot")

QUIET_AFTER = 22  # nothing after this hour, whatever the setting says
QUIET_BEFORE = 8
GONE_DAYS = 14    # no activity for this long → Sunday only
MILESTONES = (3, 7, 14, 30, 50, 100)


def _studied_today(user, today):
    return DailyActivity.objects.filter(user=user, date=today).exists()


def _lessons_this_week(user, start):
    return LessonProgress.objects.filter(
        user=user,
        status=LessonProgress.Status.COMPLETED,
        completed_at__date__gte=start,
    ).count()


def _away_for_long(link, today):
    """True once an established chat has had no activity for two weeks."""
    if link.created_at.date() > today - timedelta(days=GONE_DAYS):
        return False  # freshly linked: the bear still gets to introduce itself
    since = today - timedelta(days=GONE_DAYS)
    return not DailyActivity.objects.filter(user=link.user, date__gte=since).exists()


def due(now=None):
    """Chats that may hear from the bear in this hour."""
    now = now or timezone.localtime()
    if not (QUIET_BEFORE <= now.hour < QUIET_AFTER):
        return TelegramLink.objects.none()
    return (
        TelegramLink.objects.exclude(nudges="off")
        .filter(nudge_hour=now.hour, user__is_active=True)
        .exclude(last_nudge_on=now.date())
        .filter(Q(snooze_until__isnull=True) | Q(snooze_until__lte=now))
        .select_related("user")
    )


def send_for(link, now=None):
    """Send this chat's message for today. Returns what was sent, or ''."""
    with languages.using(link.lang):  # the lesson it names, in the chat's language
        return _send_for(link, now)


def _send_for(link, now=None):
    now = now or timezone.localtime()
    today = now.date()
    sunday = now.weekday() == 6

    # The same guards the queryset applies, repeated here so a direct call
    # (a retry, a management command, a test) cannot double up on a chat.
    if link.nudges == "off" or link.last_nudge_on == today:
        return ""
    if link.snooze_until and link.snooze_until > now:
        return ""

    if sunday:
        sent = _send_weekly(link, today)
    elif link.nudges == "weekly" or _away_for_long(link, today):
        return ""  # they hear from the bear on Sundays only
    elif _studied_today(link.user, today):
        return ""  # the day is done; nothing to nudge about
    else:
        sent = _send_nudge(link, now)

    if sent:
        link.last_nudge_on = today
        link.save(update_fields=["last_nudge_on", "last_nudge_key"])
    return sent


def _keyboard(link, url):
    lang = link.lang
    return [
        [{"text": "▶ " + texts.pick(texts.BTN["lesson"], lang), "url": url}],
        [
            {"text": texts.pick(texts.BTN["later"], lang), "callback_data": "nudge:later"},
            {"text": texts.pick(texts.BTN["not_today"], lang), "callback_data": "nudge:skip"},
        ],
        [{"text": texts.pick(texts.BTN["weekly"], lang), "callback_data": "nudge:weekly"}],
    ]


def _situation(link, now, streak):
    """Which pool the line comes from, and the numbers it can mention."""
    if streak == 0:
        return "first", {}
    if now.hour >= 20 and streak >= 3:
        return "risk", {}
    if streak >= 3 and random.random() < 0.35:
        return "league", _league_numbers(link)
    return ("keep" if streak < 3 else "streak"), {}


def _league_numbers(link):
    seat, rows = league_service.standings(link.user)
    mine = next((r for r in rows if r["seat"].user_id == link.user.pk), None)
    rank = mine["rank"] if mine else len(rows) or 1
    points = mine["points"] if mine else 0
    top = rows[league_service.PROMOTE - 1]["points"] if len(rows) >= league_service.PROMOTE else points
    return {
        "rank": rank,
        "division": seat.division.title(),
        "gap": max(1, top - points + 1),
        "lesson_points": league_service.POINTS_PER_LESSON,
    }


def _send_nudge(link, now):
    step = learning_services.next_step_payload(link.user)
    if not step or step.get("kind") == "done":
        return ""  # nothing left to point at
    stats = learning_services.get_or_create_stats(link.user)
    from .handlers import _minutes_of

    situation, extra = _situation(link, now, stats.day_streak)
    try:
        line, key = texts.nudge_line(
            situation, link.lang, avoid=link.last_nudge_key,
            title=step.get("title") or "", minutes=_minutes_of(step), streak=stats.day_streak, **extra,
        )
    except KeyError:  # a pool that wants league numbers we could not get
        line, key = texts.nudge_line(
            "keep", link.lang, avoid=link.last_nudge_key,
            title=step.get("title") or "", minutes=_minutes_of(step), streak=stats.day_streak,
        )

    sent = api.send_message(link.chat_id, f"🐻 {line}", keyboard=_keyboard(link, _lesson_url(step)))
    if sent:
        reactions.send(link.chat_id, "milestone" if stats.day_streak in MILESTONES else "nudge")
        link.last_nudge_key = key
    return "nudge" if sent else ""


def _send_weekly(link, today):
    """Sunday: how the week went, with no ask attached."""
    start = league_service.week_start(today)
    seat, rows = league_service.standings(link.user, start)
    mine = next((r for r in rows if r["seat"].user_id == link.user.pk), None)
    stats = learning_services.get_or_create_stats(link.user)
    lessons = _lessons_this_week(link.user, start)
    if not lessons and not (mine and mine["points"]):
        return ""  # an empty week does not need a report card

    text = texts.pick(texts.WEEKLY, link.lang).format(
        lessons=lessons,
        points=mine["points"] if mine else 0,
        division=seat.division.title(),
        rank=mine["rank"] if mine else len(rows),
        coins=stats.coins,
        streak=stats.day_streak,
        closing=random.choice(texts.pick(texts.WEEKLY_CLOSING, link.lang)),
    )
    keyboard = [[{"text": texts.pick(texts.BTN["league"], link.lang), "url": f"{settings.APP_ORIGIN}/app/leaderboard"}]]
    sent = api.send_message(link.chat_id, text, keyboard=keyboard)
    if sent:
        reactions.send(link.chat_id, "weekly")
        link.last_nudge_key = "weekly"
    return "weekly" if sent else ""


def run(now=None):
    """Everything due this hour. Returns {'nudge': n, 'weekly': n}."""
    now = now or timezone.localtime()
    counts = {"nudge": 0, "weekly": 0}
    for link in due(now):
        try:
            sent = send_for(link, now)
        except Exception:  # noqa: BLE001 — one bad chat must not stop the round
            log.exception("nudge failed for chat %s", link.chat_id)
            continue
        if sent:
            counts[sent] += 1
    return counts
