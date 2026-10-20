"""
AI usage accounting: a per-user monthly token quota and an append-only usage log.

Both mirror the ``accounts`` conventions: UUIDv7 primary keys (time-ordered, non
-enumerable), FKs to ``settings.AUTH_USER_MODEL``, and ``Meta.indexes`` for the
hot read paths. Quota mutation is always done under ``select_for_update`` by the
callers in ``ai_engine.quota`` — the model methods assume the row is locked.
"""
from datetime import date

import uuid6

from django.conf import settings
from django.db import models
from django.utils import timezone


def first_of_next_month(d):
    """First day of the month after ``d`` — the next quota reset boundary."""
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


class UserAIQuota(models.Model):
    """One row per user: how many AI tokens they may spend this monthly cycle."""

    class Tier(models.TextChoices):
        FREE = "free", "Free"
        PLUS = "plus", "Plus"
        PRO = "pro", "Pro"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_quota"
    )
    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.FREE)
    monthly_token_limit = models.PositiveIntegerField(default=30_000)
    # Earned this cycle by learning (a new lesson, a new streak day); lapses with the cycle.
    bonus_tokens = models.PositiveIntegerField(default=0)
    tokens_used_this_cycle = models.PositiveIntegerField(default=0)
    reset_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id} · {self.tier} · {self.tokens_used_this_cycle}/{self.monthly_token_limit}"

    @classmethod
    def get_or_create_for(cls, user):
        """
        Ensure a quota row exists for ``user`` (unlocked). Callers that mutate the
        row re-fetch it with ``select_for_update`` inside a transaction afterwards.
        """
        obj, _ = cls.objects.get_or_create(
            user=user,
            defaults={
                "tier": settings.AI_DEFAULT_TIER,
                "monthly_token_limit": settings.AI_DEFAULT_MONTHLY_TOKEN_LIMIT,
                "reset_date": first_of_next_month(timezone.localdate()),
            },
        )
        return obj

    def maybe_rollover(self, today):
        """
        If the cycle boundary has passed, zero the counter and advance the reset
        date to the first of next month. Returns True when a rollover happened
        (so the caller knows to persist). Assumes the row is locked.
        """
        if today >= self.reset_date:
            self.tokens_used_this_cycle = 0
            self.bonus_tokens = 0
            self.reset_date = first_of_next_month(today)
            return True
        return False

    def total_limit(self):
        """The monthly allowance plus what learning earned this cycle."""
        return self.monthly_token_limit + self.bonus_tokens

    def remaining(self):
        return max(0, self.total_limit() - self.tokens_used_this_cycle)

    def has_allowance(self):
        return self.remaining() > 0

    def consume(self, total_tokens):
        """Add spent tokens to the cycle counter. Assumes the row is locked."""
        self.tokens_used_this_cycle += max(0, int(total_tokens))


class AIUsageLog(models.Model):
    """Append-only record of a single AI generation, for billing/auditing."""

    class Feature(models.TextChoices):
        ADVISOR = "ADVISOR", "AI Advisor"
        ONBOARDING_PARSE = "ONBOARDING_PARSE", "Startup onboarding parse"
        CEO_MATCH = "CEO_MATCH", "CEO matchmaking"
        STUDY_PLAN = "STUDY_PLAN", "Personalised study plan"
        TTS = "TTS", "Bear voice (text to speech)"
        ROADMAP = "ROADMAP", "Startup roadmap"
        COPILOT = "COPILOT", "Zinvest Copilot"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_usage_logs"
    )
    feature = models.CharField(max_length=32, choices=Feature.choices)
    model_version = models.CharField(max_length=100)  # resolved model id, or "stub"
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["feature", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} · {self.feature} · {self.model_version} · {self.total_tokens}t"

    @property
    def total_tokens(self):
        return self.input_tokens + self.output_tokens
