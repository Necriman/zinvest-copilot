"""
The practice trainer: the question bank, one question at a time, for as long
as the learner likes — on the site and in the bot alike.

It draws on the same bank as Zinvest Daily, but it pays no coins and does not
count towards the streak. The Daily is the habit and is rewarded as one; the
trainer is where you go to get better, and a reward would only turn it into
something to farm. What the trainer does feed is the AI: a question missed
here becomes the "recently tricky" the AI offers to explain.
"""
import random
import uuid
from datetime import timedelta

from django.utils import timezone

from .models import DailyQuestion, PracticeAttempt

# A question answered this recently waits before it comes round again.
RECENT_DAYS = 3
TOPICS = tuple(DailyQuestion.Topic.values)


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def public(question, lang):
    """The question as the learner sees it before answering: no answer."""
    text = question.text(lang)
    return {
        "id": str(question.id),
        "topic": question.topic,
        "question": text.get("question", ""),
        "options": text.get("options", []),
    }


def topics():
    """How many active questions each topic has, for the topic chips."""
    counts = {topic: 0 for topic in TOPICS}
    for topic in DailyQuestion.objects.filter(active=True).values_list("topic", flat=True):
        counts[topic] = counts.get(topic, 0) + 1
    return [{"key": key, "count": counts[key]} for key in TOPICS]


def next_question(user, lang="ru", topic=None, exclude=None):
    """
    A question the learner has not seen lately, from one topic or from all.

    `exclude` is the one just answered: even when the whole topic has been
    seen, the same question never comes straight back.
    """
    questions = DailyQuestion.objects.filter(active=True)
    if topic in TOPICS:
        questions = questions.filter(topic=topic)
    ids = list(questions.values_list("id", flat=True))
    if not ids:
        return None
    since = timezone.now() - timedelta(days=RECENT_DAYS)
    recent = set(
        PracticeAttempt.objects.filter(user=user, created_at__gte=since).values_list("question_id", flat=True)
    )
    skip = _uuid(exclude)
    fresh = [q for q in ids if q not in recent and q != skip]
    pool = fresh or [q for q in ids if q != skip] or ids
    return public(DailyQuestion.objects.get(pk=random.choice(pool)), lang)


def stats(user):
    today = timezone.localdate()
    everything = PracticeAttempt.objects.filter(user=user)
    today_rows = everything.filter(created_at__date=today)
    return {
        "today": today_rows.count(),
        "today_correct": today_rows.filter(correct=True).count(),
        "total": everything.count(),
        "correct": everything.filter(correct=True).count(),
    }


def answer(user, question_id, choice, lang="ru", source=PracticeAttempt.Source.WEB, reveal=False):
    """
    Grade one answer and keep it. None when the question or the choice is not real.

    `reveal` is "just show me the answer": it is kept as an attempt that was
    not right, so the question still counts as one to come back to.
    """
    pk = _uuid(question_id)
    question = DailyQuestion.objects.filter(pk=pk, active=True).first() if pk else None
    if question is None:
        return None
    text = question.text(lang)
    options = text.get("options", [])
    if reveal:
        choice, correct = None, False
    else:
        try:
            choice = int(choice)
        except (TypeError, ValueError):
            return None
        if not 0 <= choice < len(options):
            return None
        correct = choice == question.answer

    PracticeAttempt.objects.create(user=user, question=question, choice=choice, correct=correct, source=source)
    return {
        "id": str(question.id),
        "correct": correct,
        "revealed": reveal,
        "chosen": choice,
        "answer": question.answer,
        "question": text.get("question", ""),
        "options": options,
        "explain": text.get("explain", ""),
        "stats": stats(user),
    }
