"""
Zinvest Daily — five short situations, about two minutes, once a day.

It is the habit loop the rest of the product hangs off: answering counts as
activity, so the streak, the weekly calendar and the league all move from the
same action a learner can finish before their coffee lands.

Nothing here invents a second score. Coins go through ``UserStats.add_coins``
and the day is registered through ``services.record_activity``, exactly as a
finished lesson does, so a Daily and a lesson are worth the same kind of thing.
"""
import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from . import services
from .models import DailyQuestion, DailyRun

SIZE = 5
# Showing up is worth something; getting them right is worth more. The card
# advertises "up to +20", which is base + a perfect round.
COINS_BASE = 10
COINS_PER_CORRECT = 2
# How long before a question can come round again.
COOLDOWN_DAYS = 45


def _recent_question_ids(user, today):
    """What this learner has already seen lately, so a set feels new."""
    seen = set()
    runs = DailyRun.objects.filter(user=user, date__gte=today - timedelta(days=COOLDOWN_DAYS))
    for run in runs.values_list("questions", flat=True):
        seen.update(str(q) for q in (run or []))
    return seen


def pick(user, today):
    """
    Today's five question ids for this learner.

    Seeded by user and date, so the same person reloading gets the same set and
    two people comparing notes at lunch are talking about the same questions.
    """
    pool = list(DailyQuestion.objects.filter(active=True).values_list("id", flat=True))
    if not pool:
        return []
    pool = [str(q) for q in pool]
    seen = _recent_question_ids(user, today)
    fresh = [q for q in pool if q not in seen]
    # Once the bank has been exhausted, start over rather than showing nothing.
    source = fresh if len(fresh) >= SIZE else pool
    shuffler = random.Random(f"{user.pk}:{today.isoformat()}")
    shuffler.shuffle(source)
    return source[:SIZE]


def run_for(user, today=None):
    """This learner's run for today, created on first open."""
    today = today or timezone.localdate()
    run = DailyRun.objects.filter(user=user, date=today).first()
    if run:
        return run
    questions = pick(user, today)
    if not questions:
        return None
    run, _ = DailyRun.objects.get_or_create(
        user=user, date=today, defaults={"questions": questions}
    )
    return run


def _question_map(ids):
    rows = DailyQuestion.objects.filter(id__in=ids)
    return {str(row.id): row for row in rows}


def state(user, lang="ru", today=None):
    """
    What the dashboard card and the Daily screen both render.

    A finished run still returns its questions with the answers attached, so
    the learner can read the bear's explanations again during the day.
    """
    today = today or timezone.localdate()
    run = run_for(user, today)
    if run is None:
        return {"available": False}

    rows = _question_map(run.questions)
    answered = len(run.answers or [])
    items = []
    for index, qid in enumerate(run.questions):
        row = rows.get(str(qid))
        if row is None:
            continue
        text = row.text(lang)
        item = {
            "index": index,
            "topic": row.topic,
            "question": text.get("question", ""),
            "options": text.get("options", []),
        }
        # Only reveal the answer for questions already played.
        if index < answered:
            item["chosen"] = (run.answers or [])[index]
            item["answer"] = row.answer
            item["explain"] = text.get("explain", "")
        items.append(item)

    return {
        "available": True,
        "date": run.date.isoformat(),
        "size": len(run.questions),
        "answered": answered,
        "correct": run.correct,
        "finished": bool(run.finished_at),
        "coins_awarded": run.coins_awarded,
        "max_coins": COINS_BASE + COINS_PER_CORRECT * len(run.questions),
        "items": items,
    }


@transaction.atomic
def answer(user, choice, lang="ru", today=None):
    """
    Grade the next unanswered question.

    The index is not taken from the client: the run knows how far it has got,
    so a replayed request cannot re-answer a question or pay twice.
    """
    today = today or timezone.localdate()
    # Create the run if this is the first thing the client does, then take the
    # row lock: two taps landing together must not both grade the same question.
    if run_for(user, today) is None:
        return None
    run = DailyRun.objects.select_for_update().filter(user=user, date=today).first()
    if run is None or run.finished_at:
        return None

    answers = list(run.answers or [])
    index = len(answers)
    if index >= len(run.questions):
        return None

    row = _question_map([run.questions[index]]).get(str(run.questions[index]))
    if row is None:
        return None

    try:
        choice = int(choice)
    except (TypeError, ValueError):
        return None
    options = row.text(lang).get("options", [])
    if not 0 <= choice < max(1, len(options)):
        return None

    correct = choice == row.answer
    answers.append(choice)
    run.answers = answers
    if correct:
        run.correct += 1

    result = {
        "index": index,
        "chosen": choice,
        "answer": row.answer,
        "correct": correct,
        "explain": row.text(lang).get("explain", ""),
        "answered": len(answers),
        "size": len(run.questions),
        "finished": False,
        "coins_awarded": 0,
        "streak": None,
    }

    if len(answers) >= len(run.questions):
        result.update(_finish(user, run, today))

    run.save(update_fields=["answers", "correct", "coins_awarded", "finished_at"])
    return result


def _finish(user, run, today):
    """Close the run: pay once, and register the day the way a lesson does."""
    from .models import UserStats

    run.finished_at = timezone.now()
    run.coins_awarded = COINS_BASE + COINS_PER_CORRECT * run.correct

    stats = UserStats.objects.select_for_update().filter(user=user).first()
    if stats is None:
        stats = services.get_or_create_stats(user, today)
    stats.add_coins(run.coins_awarded)
    services.record_activity(user, stats, today)
    stats.save()

    return {
        "finished": True,
        "coins_awarded": run.coins_awarded,
        "correct": run.correct,
        "streak": stats.day_streak,
    }
