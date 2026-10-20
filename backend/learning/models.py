"""
Learning domain: units, lessons, per-user progress, unit tests, and the
gamification profile (coins / streak / rank / goal) that drives the dashboard.

Conventions match ``accounts``: UUIDv7 PKs, FKs to ``settings.AUTH_USER_MODEL``,
``Meta.indexes`` for hot reads. Lock/unlock state is DERIVED (see
``learning.services``), never stored; only completion is persisted. Coin/streak
mutations happen under ``select_for_update`` on the ``UserStats`` row.
"""
from datetime import timedelta

import uuid6

from django.conf import settings
from django.db import models
from django.utils import timezone

from config import languages


class Translated:
    """
    Words stored in English on the model itself, with the other languages in
    `i18n` as {"ru": {field: value}, "uz": {...}}. `tr(field)` reads the
    current language (see config.languages) and falls back to English, so a
    translation that is missing shows the original rather than an empty card.
    """

    def tr(self, field, lang=None):
        lang = languages.normalize(lang) or languages.current()
        if lang != languages.BASE:
            value = ((self.i18n or {}).get(lang) or {}).get(field)
            if value:
                return value
        return getattr(self, field)


class Unit(Translated, models.Model):
    """A top-level course unit (e.g. "01 · Finance Fundamentals")."""

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    code = models.CharField(max_length=8, unique=True)          # "01".."04"
    slug = models.SlugField(max_length=64, unique=True)
    title = models.CharField(max_length=120)
    subtitle = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(unique=True)       # drives sequencing/unlock
    accent_color = models.CharField(max_length=20, default="brand")  # cosmetic token key
    icon = models.CharField(max_length=40, blank=True)

    # The quiz definition lives on the unit to keep the model set small.
    # Each item: {id, prompt, choices:[...], answer_index, explanation}
    test_questions = models.JSONField(default=list, blank=True)
    test_pass_threshold = models.FloatField(default=0.7)         # 0..1

    # title, subtitle and the test's words in other languages (see Translated).
    i18n = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.code} · {self.title}"

    def questions(self, lang=None):
        """
        The test in `lang`: translated words laid over the English questions,
        matched by id. A translation may carry its own answer_index: a version
        written for that language can order its options differently (or ask
        with local numbers), so the right answer is the one in the version
        shown. Grade with the same language the test was taken in.
        """
        lang = languages.normalize(lang) or languages.current()
        words = {}
        if lang != languages.BASE:
            words = {q.get("id"): q for q in ((self.i18n or {}).get(lang) or {}).get("test_questions") or []}
        out = []
        for question in self.test_questions or []:
            said = words.get(question.get("id")) or {}
            choices = said.get("choices")
            if not choices or len(choices) != len(question.get("choices") or []):
                choices = question.get("choices") or []
            answer = question.get("answer_index")
            own = said.get("answer_index")
            if choices is said.get("choices") and isinstance(own, int) and 0 <= own < len(choices):
                answer = own
            out.append({
                **question,
                "prompt": said.get("prompt") or question.get("prompt", ""),
                "choices": choices,
                "answer_index": answer,
                "explanation": said.get("explanation") or question.get("explanation", ""),
            })
        return out


class Lesson(Translated, models.Model):
    """A single lesson node inside a unit; carries the Canvas render payload."""

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="lessons")
    slug = models.SlugField(max_length=80)
    title = models.CharField(max_length=140)
    order = models.PositiveSmallIntegerField()
    coin_reward = models.PositiveIntegerField(default=10)
    estimated_minutes = models.PositiveSmallIntegerField(default=5)

    # Coordinate-based draw list rendered by the HTML5 Canvas workspace:
    # {width, height, background, elements:[{type,...}]}
    canvas_payload = models.JSONField(default=dict, blank=True)

    # The lesson body as editor HTML: English here, the other languages in
    # i18n[lang]["content_html"]. When present it is the lesson; canvas_payload
    # is the older drawn layout, kept for lessons that have no HTML yet.
    content_html = models.TextField(blank=True, default="")

    # title, canvas_payload and content_html in other languages (see Translated).
    i18n = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["unit", "order"]
        unique_together = [("unit", "order"), ("unit", "slug")]
        indexes = [models.Index(fields=["unit", "order"])]

    def __str__(self):
        return f"{self.unit.code}.{self.order} · {self.title}"


class LessonProgress(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.IN_PROGRESS)
    worksheet_answers = models.JSONField(null=True, blank=True)
    # Per-user edited lesson HTML from the document editor (manual "Save").
    edited_content = models.TextField(blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "lesson")]
        indexes = [models.Index(fields=["user", "lesson"])]

    def __str__(self):
        return f"{self.user_id} · {self.lesson_id} · {self.status}"


class UnitProgress(models.Model):
    class Status(models.TextChoices):
        LOCKED = "locked", "Locked"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="unit_progress")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="progress")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.IN_PROGRESS)
    best_test_score = models.FloatField(default=0.0)  # 0..1
    test_passed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "unit")]
        indexes = [models.Index(fields=["user", "unit"])]

    def __str__(self):
        return f"{self.user_id} · {self.unit_id} · passed={self.test_passed}"


class UnitTestResult(models.Model):
    """One row per unit-test attempt (best score is cached on UnitProgress)."""

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="test_results")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="test_results")
    score = models.FloatField()          # 0..1
    correct_count = models.PositiveSmallIntegerField()
    total_count = models.PositiveSmallIntegerField()
    passed = models.BooleanField()
    answers = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "unit", "-created_at"])]

    def __str__(self):
        return f"{self.user_id} · {self.unit_id} · {self.score:.2f}"


class UserStats(models.Model):
    """Gamification profile — one row per user. Mutated under a row lock."""

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stats")
    coins = models.PositiveIntegerField(default=0)
    day_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    weekly_rank = models.PositiveIntegerField(null=True, blank=True)
    weekly_xp = models.PositiveIntegerField(default=0)
    financial_goal = models.CharField(max_length=120, blank=True)
    target_score = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id} · {self.coins} coins · {self.day_streak}d"

    def add_coins(self, amount):
        amount = max(0, int(amount))
        self.coins += amount
        self.weekly_xp += amount

    def touch_activity(self, today):
        """Advance the daily streak. Idempotent within a single day."""
        if self.last_activity_date == today:
            return False
        if self.last_activity_date == today - timedelta(days=1):
            self.day_streak += 1
        else:
            self.day_streak = 1
        self.last_activity_date = today
        self.longest_streak = max(self.longest_streak, self.day_streak)
        return True

    def streak_has_lapsed(self, today):
        """True once a whole day has passed with no activity — the streak is broken.

        ``touch_activity`` only ever runs when the user *does* something, so
        without this a lapsed streak would sit frozen at its old number forever.
        """
        if self.day_streak == 0:
            return False
        if self.last_activity_date is None:
            return True
        return self.last_activity_date < today - timedelta(days=1)

    def decay_streak(self, today):
        """Zero a lapsed streak, lazily on read (mirrors UserAIQuota.maybe_rollover)."""
        if not self.streak_has_lapsed(today):
            return False
        self.day_streak = 0
        return True

    def is_active_on(self, today):
        """Whether today's streak has already been earned."""
        return self.last_activity_date == today


class DailyActivity(models.Model):
    """One row per day the user was active — source of the weekly calendar."""

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_activity")
    date = models.DateField(default=timezone.localdate)

    class Meta:
        unique_together = [("user", "date")]
        indexes = [models.Index(fields=["user", "date"])]

    def __str__(self):
        return f"{self.user_id} · {self.date}"


class OnboardingAssessment(models.Model):
    """What the learner told us at sign-up, plus how they did on the quick quiz.

    Feeds the personalised study plan. Kept separate from ``StudyPlan`` so the
    plan can be regenerated from the same answers without re-asking.
    """

    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="onboarding"
    )
    # {"profile": {experience, goal, time}, "quiz": [{id, choice_index, correct}]}
    answers = models.JSONField(default=dict, blank=True)
    quiz_score = models.FloatField(default=0.0)  # 0..1
    level = models.CharField(max_length=16, choices=Level.choices, default=Level.BEGINNER)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id} · {self.level} · {self.quiz_score:.0%}"


class StudyPlan(models.Model):
    """A learner's personalised route through the lessons.

    Absence of a row simply means "follow the default unit order" — the plan is
    an override, never a prerequisite, so the app works before onboarding runs.
    """

    class Source(models.TextChoices):
        DEFAULT = "default", "Default order"
        AI = "ai", "AI generated"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_plan"
    )
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.DEFAULT)
    level = models.CharField(max_length=16, blank=True)
    rationale = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id} · {self.source} · {self.items.count()} lessons"


class StudyPlanItem(models.Model):
    """One lesson's slot in the personalised sequence."""

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name="items")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="plan_items")
    order = models.PositiveSmallIntegerField()
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["order"]
        unique_together = [("plan", "lesson")]
        indexes = [models.Index(fields=["plan", "order"])]

    def __str__(self):
        return f"{self.plan_id} · {self.order} · {self.lesson_id}"


class Task(models.Model):
    """A user-authored to-do for the dashboard's "Today" tab.

    Deliberately flat (no due date): the rail shows every open task plus the ones
    finished today, so yesterday's completed items fall away on their own while
    unfinished work carries over.
    """

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    done = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["done", "order", "created_at"]
        indexes = [
            models.Index(fields=["user", "done", "order"]),
            models.Index(fields=["user", "-completed_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} · {'x' if self.done else ' '} {self.title}"

    def set_done(self, done, now):
        """Flip completion, keeping ``completed_at`` in sync."""
        done = bool(done)
        if done == self.done:
            return False
        self.done = done
        self.completed_at = now if done else None
        return True


class LeagueMembership(models.Model):
    """
    One learner's seat in one week's league group (see learning/league.py).

    Only the grouping lives here: the points are derived from real activity, so
    a seat row cannot be edited into a better place on the board. Once the week
    is closed the numbers are frozen here as history.
    """

    class Result(models.TextChoices):
        STAYED = "stayed", "Stayed"
        PROMOTED = "promoted", "Promoted"
        DEMOTED = "demoted", "Demoted"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="league_seats")
    week_start = models.DateField()  # the Monday this group is racing
    division = models.CharField(max_length=16, default="bronze")
    group_id = models.UUIDField()
    points = models.PositiveIntegerField(default=0)   # frozen when the week closes
    rank = models.PositiveSmallIntegerField(null=True, blank=True)
    result = models.CharField(max_length=10, choices=Result.choices, blank=True, default="")
    closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "week_start"], name="one_league_seat_per_week")]
        indexes = [
            models.Index(fields=["week_start", "group_id"]),
            models.Index(fields=["user", "-week_start"]),
        ]

    def __str__(self):
        return f"{self.user_id} · {self.week_start} · {self.division}"


class DailyQuestion(models.Model):
    """
    One short situation for Zinvest Daily.

    The body carries every language, because a daily question is two sentences
    and translating it costs nothing, while a learner switching to Uzbek and
    finding today's question in Russian would simply stop opening it:

        {"ru": {"question": "...", "options": ["...", ...], "explain": "..."},
         "en": {...}, "uz": {...}}

    `explain` is the bear talking, not a textbook: it says what the answer means
    and why, in the voice the rest of the product uses.
    """

    class Topic(models.TextChoices):
        BUDGETING = "budgeting", "Budgeting"
        INVESTING = "investing", "Investing"
        RISK = "risk", "Risk"
        CREDIT = "credit", "Credit"
        STARTUP = "startup", "Startup"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    slug = models.SlugField(max_length=64, unique=True)
    topic = models.CharField(max_length=16, choices=Topic.choices, default=Topic.INVESTING)
    body = models.JSONField(default=dict)
    answer = models.PositiveSmallIntegerField(default=0)  # index into options
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["slug"]
        indexes = [models.Index(fields=["active", "topic"])]

    def __str__(self):
        return f"{self.slug} · {self.topic}"

    def text(self, lang):
        """The question in `lang`, falling back rather than showing an empty card."""
        body = self.body or {}
        return body.get(lang) or body.get("en") or body.get("ru") or {}


class DailyRun(models.Model):
    """
    One learner's Daily for one date.

    The question list is fixed when the run is created, so reloading the page
    or coming back in the evening shows the same five — a set that reshuffled
    on refresh would be a way to farm coins, and would stop feeling like *the*
    daily question.
    """

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_runs")
    date = models.DateField(default=timezone.localdate)
    questions = models.JSONField(default=list)  # question ids, in order
    answers = models.JSONField(default=list)    # chosen option index per question
    correct = models.PositiveSmallIntegerField(default=0)
    coins_awarded = models.PositiveIntegerField(default=0)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "date")]
        ordering = ["-date"]
        indexes = [models.Index(fields=["user", "date"])]

    def __str__(self):
        return f"{self.user_id} · {self.date} · {self.correct}/{len(self.questions)}"


class PracticeAttempt(models.Model):
    """
    One answer in the practice trainer, on the site or in the bot.

    The trainer draws on the same bank as Zinvest Daily but pays nothing and
    counts nothing towards the streak: it is for learning, and a reward would
    turn it into a farm. What it does feed is the AI's "recently tricky" — a
    question missed here is exactly what a learner wants explained.
    """

    class Source(models.TextChoices):
        WEB = "web", "Web"
        BOT = "bot", "Telegram"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="practice_attempts")
    question = models.ForeignKey(DailyQuestion, on_delete=models.CASCADE, related_name="practice_attempts")
    # None: the learner asked for the answer instead of giving one.
    choice = models.PositiveSmallIntegerField(null=True, blank=True)
    correct = models.BooleanField()
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.WEB)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user_id} · {self.question_id} · {'✓' if self.correct else '✗'}"


class MarketEpisode(models.Model):
    """
    A real moment in a real market, cut where the learner has to call it.

    `before` is the price up to the decision, `after` is what happened next,
    both in the asset's own units. The line between the known points is
    smoothed rather than tick-accurate, and the page says so; the key levels —
    the peak, the drop, where it ended — are the real ones.

        body = {"ru": {"when": "март 2020", "headline": "...", "question": "...",
                       "explain": "...", "lesson": "..."}, "en": {...}, "uz": {...}}
    """

    class Direction(models.TextChoices):
        UP = "up", "Up"
        DOWN = "down", "Down"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    slug = models.SlugField(max_length=64, unique=True)
    asset = models.CharField(max_length=80)
    unit = models.CharField(max_length=8, default="$")  # shown before the price
    before = models.JSONField(default=list)
    after = models.JSONField(default=list)
    direction = models.CharField(max_length=4, choices=Direction.choices)
    body = models.JSONField(default=dict)
    order = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "slug"]

    def __str__(self):
        return f"{self.slug} · {self.direction}"

    def text(self, lang):
        body = self.body or {}
        return body.get(lang) or body.get("en") or body.get("ru") or {}

    @property
    def change_pct(self):
        """From the decision point to the end of the story."""
        if not self.before or not self.after or not self.before[-1]:
            return 0.0
        return round(100 * (self.after[-1] - self.before[-1]) / abs(self.before[-1]), 1)


class PredictionAttempt(models.Model):
    """One call on one episode. An episode is played once per learner, ever."""

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="predictions")
    episode = models.ForeignKey(MarketEpisode, on_delete=models.CASCADE, related_name="attempts")
    choice = models.CharField(max_length=4, choices=MarketEpisode.Direction.choices)
    correct = models.BooleanField()
    coins_awarded = models.PositiveIntegerField(default=0)
    source = models.CharField(max_length=8, choices=PracticeAttempt.Source.choices, default=PracticeAttempt.Source.WEB)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "episode")]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user_id} · {self.episode_id} · {self.choice}"
