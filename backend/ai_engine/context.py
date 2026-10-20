"""
What Zinvest AI knows about the learner before they type anything.

Two things, both read from what the learner actually did — nothing inferred,
nothing invented:

  * learning — the lesson they are on, or the one they asked about from inside
    a lesson;
  * mistake  — the most recent question they got wrong, in a unit test or the
    Daily, with the answer they gave and the right one.

The AI screen uses this to offer the explanations worth asking for, and the
"analyse my mistake" action sends the mistake along with the question. No
model is called here: opening the screen must not spend the learner's quota.
"""
import uuid
from datetime import datetime, time, timedelta

from django.utils import timezone

from config import languages

# Older than this and a mistake is history rather than a current difficulty.
LOOKBACK_DAYS = 30
LANGS = ("ru", "en", "uz")


def _pick(options, index):
    """The option text at `index`, or "" when the stored index is unusable."""
    if isinstance(index, int) and 0 <= index < len(options or []):
        return options[index]
    return ""


def _lesson(lesson_id, lang):
    from learning.models import Lesson

    try:
        pk = uuid.UUID(str(lesson_id))
    except (TypeError, ValueError):
        return None
    lesson = Lesson.objects.select_related("unit").filter(pk=pk).first()
    if lesson is None:
        return None
    return {
        "kind": "lesson",
        "id": str(lesson.id),
        "title": lesson.tr("title", lang),
        "unit_title": lesson.unit.tr("title", lang),
        "unit_code": lesson.unit.code,
    }


def _current(user, lang):
    from learning.services import next_step_payload

    with languages.using(lang):
        step = next_step_payload(user)
    if step["kind"] == "done":
        return None
    return {
        "kind": step["kind"],
        "id": step["id"],
        "title": step["title"],
        "unit_title": step["unit_title"],
        "unit_code": step.get("unit_code", ""),
    }


def _test_mistake(user, since, lang):
    """The first wrong answer in the learner's most recent unit tests."""
    from learning.models import UnitTestResult

    results = (
        UnitTestResult.objects.filter(user=user, created_at__gte=since)
        .select_related("unit").order_by("-created_at")[:5]
    )
    for result in results:
        questions = {str(q.get("id")): q for q in result.unit.questions(lang)}
        for answer in result.answers or []:
            question = questions.get(str(answer.get("question_id")))
            if question is None:
                continue
            chosen = answer.get("choice_index")
            if chosen is None or chosen == question.get("answer_index"):
                continue
            choices = question.get("choices") or []
            return {
                "source": "test",
                "at": result.created_at,
                "where": result.unit.tr("title", lang),
                "question": question.get("prompt", ""),
                "chosen": _pick(choices, chosen),
                "correct": _pick(choices, question.get("answer_index")),
                "explain": question.get("explanation", ""),
            }
    return None


def _daily_mistake(user, since, lang):
    """The latest wrong answer in the learner's recent Daily runs."""
    from learning.models import DailyQuestion, DailyRun

    runs = DailyRun.objects.filter(user=user, date__gte=since.date()).order_by("-date")[:7]
    for run in runs:
        answers = run.answers or []
        asked = [str(q) for q in (run.questions or [])[: len(answers)]]
        rows = {str(row.id): row for row in DailyQuestion.objects.filter(id__in=asked)}
        # Latest answer first: the one the learner will remember.
        for index in range(len(answers) - 1, -1, -1):
            row = rows.get(asked[index])
            if row is None or answers[index] == row.answer:
                continue
            text = row.text(lang)
            options = text.get("options", [])
            at = run.finished_at or timezone.make_aware(datetime.combine(run.date, time(23, 59)))
            return {
                "source": "daily",
                "at": at,
                "where": "Zinvest Daily",
                "question": text.get("question", ""),
                "chosen": _pick(options, answers[index]),
                "correct": _pick(options, row.answer),
                "explain": text.get("explain", ""),
            }
    return None


# How the trainer is named where the mistake is shown.
PRACTICE_NAME = {"ru": "Тренажёр", "en": "Practice", "uz": "Mashq"}


def _practice_mistake(user, since, lang):
    """
    The latest wrong answer in the practice trainer, on the site or in the bot.
    A question whose answer was simply looked up has no reasoning to analyse.
    """
    from learning.models import PracticeAttempt

    attempt = (
        PracticeAttempt.objects.filter(user=user, correct=False, choice__isnull=False, created_at__gte=since)
        .select_related("question").order_by("-created_at").first()
    )
    if attempt is None:
        return None
    text = attempt.question.text(lang)
    options = text.get("options", [])
    return {
        "source": "practice",
        "at": attempt.created_at,
        "where": PRACTICE_NAME.get(lang, PRACTICE_NAME["en"]),
        "question": text.get("question", ""),
        "chosen": _pick(options, attempt.choice),
        "correct": _pick(options, attempt.question.answer),
        "explain": text.get("explain", ""),
    }


def learner_context(user, lesson_id=None, lang="ru"):
    lang = lang if lang in LANGS else "ru"
    since = timezone.now() - timedelta(days=LOOKBACK_DAYS)

    asked = _lesson(lesson_id, lang) if lesson_id else None
    learning = asked or _current(user, lang)

    found = [
        m
        for m in (_test_mistake(user, since, lang), _daily_mistake(user, since, lang), _practice_mistake(user, since, lang))
        if m
    ]
    mistake = max(found, key=lambda m: m["at"]) if found else None
    if mistake:
        mistake = {**mistake, "at": mistake["at"].isoformat()}

    return {
        "learning": learning,
        # True when the learner came from a lesson's "ask about this" button,
        # so the screen can say "about this lesson" instead of "you're on".
        "from_lesson": asked is not None,
        "mistake": mistake,
    }
