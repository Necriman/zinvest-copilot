"""
"Up or down?" — real moments in real markets, cut where the learner has to
call it.

The game is not the point; the reveal is. After the call the chart carries on
to what actually happened, and the bear says why — the crash that turned into
a recovery, the report that wiped a third off a stock, the bubble at its top.
Half the episodes end the opposite way to what the headline suggests, which is
the lesson in itself: nobody times the market.

Three rounds a day, like the Daily, so the episodes last and the habit forms.
A right call pays a few coins; a wrong one costs nothing. Each episode is
played once per learner, ever — the second time you would know the answer.
"""
import uuid

from django.db import IntegrityError, transaction
from django.utils import timezone

from . import services
from .models import MarketEpisode, PracticeAttempt, PredictionAttempt, UserStats

ROUNDS_PER_DAY = 3
COINS_RIGHT = 5
CHOICES = (MarketEpisode.Direction.UP, MarketEpisode.Direction.DOWN)


def public(episode, lang):
    """The round as it is played: the chart so far, the moment and the question."""
    text = episode.text(lang)
    return {
        "id": str(episode.id),
        "asset": episode.asset,
        "unit": episode.unit,
        "before": episode.before,
        "when": text.get("when", ""),
        "headline": text.get("headline", ""),
        "question": text.get("question", ""),
    }


def reveal(episode, lang):
    """What happened next, and why."""
    text = episode.text(lang)
    return {
        "after": episode.after,
        "direction": episode.direction,
        "change_pct": episode.change_pct,
        "explain": text.get("explain", ""),
        "lesson": text.get("lesson", ""),
    }


def _stats(user):
    rows = list(PredictionAttempt.objects.filter(user=user).order_by("-created_at").values_list("correct", "coins_awarded"))
    streak = 0
    for correct, _coins in rows:
        if not correct:
            break
        streak += 1
    return {
        "played": len(rows),
        "correct": sum(1 for correct, _ in rows if correct),
        "streak": streak,
        "coins": sum(coins for _, coins in rows),
    }


def _played_today(user, today):
    return PredictionAttempt.objects.filter(user=user, created_at__date=today).count()


def state(user, lang="ru", today=None):
    today = today or timezone.localdate()
    played = set(PredictionAttempt.objects.filter(user=user).values_list("episode_id", flat=True))
    unplayed = MarketEpisode.objects.filter(active=True).exclude(id__in=played)
    left_today = max(0, ROUNDS_PER_DAY - _played_today(user, today))
    upcoming = unplayed.first()
    return {
        "rounds_per_day": ROUNDS_PER_DAY,
        "coins_right": COINS_RIGHT,
        "left_today": left_today,
        "remaining": unplayed.count(),
        "round": public(upcoming, lang) if upcoming and left_today else None,
        "stats": _stats(user),
    }


@transaction.atomic
def answer(user, episode_id, choice, lang="ru", source=PracticeAttempt.Source.WEB, today=None):
    """
    Grade one call. Returns (result, error): error is "invalid", "played" or
    "limit", and the view turns it into the matching status.
    """
    today = today or timezone.localdate()
    if choice not in CHOICES:
        return None, "invalid"
    try:
        pk = uuid.UUID(str(episode_id))
    except (TypeError, ValueError):
        return None, "invalid"
    episode = MarketEpisode.objects.filter(pk=pk, active=True).first()
    if episode is None:
        return None, "invalid"

    # The stats row is the lock: two taps landing together must not both get
    # past the daily limit or both pay.
    stats = UserStats.objects.select_for_update().filter(user=user).first()
    if stats is None:
        services.get_or_create_stats(user, today)
        stats = UserStats.objects.select_for_update().get(user=user)
    if PredictionAttempt.objects.filter(user=user, episode=episode).exists():
        return None, "played"
    if _played_today(user, today) >= ROUNDS_PER_DAY:
        return None, "limit"

    correct = choice == episode.direction
    coins = COINS_RIGHT if correct else 0
    try:
        with transaction.atomic():
            PredictionAttempt.objects.create(
                user=user, episode=episode, choice=choice, correct=correct, coins_awarded=coins, source=source
            )
    except IntegrityError:
        return None, "played"
    if coins:
        stats.add_coins(coins)
        stats.save()

    return {
        "id": str(episode.id),
        "choice": choice,
        "correct": correct,
        "coins": coins,
        **reveal(episode, lang),
        "left_today": max(0, ROUNDS_PER_DAY - _played_today(user, today)),
        "stats": _stats(user),
    }, None
