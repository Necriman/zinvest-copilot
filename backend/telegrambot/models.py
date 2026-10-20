"""
The bot's own state: which chat belongs to which learner, the one-time codes
that pair them, what the bear is about to save, and which updates we already
handled.

Nothing here holds money data — entries go straight into startup.CashFlowEntry,
the same table the app writes.
"""
import uuid6
from django.conf import settings
from django.db import models
from django.utils import timezone


class TelegramLink(models.Model):
    """One learner ⇄ one chat. Deleting the row unlinks the chat completely."""

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="telegram")
    chat_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=64, blank=True, default="")
    first_name = models.CharField(max_length=64, blank=True, default="")
    lang = models.CharField(max_length=2, default="ru")

    # The bear's check-in. Defaults are deliberately quiet: one message a day,
    # only in the evening, only when the day is still empty.
    nudges = models.CharField(
        max_length=8,
        choices=[("daily", "Daily"), ("weekly", "Weekly only"), ("off", "Off")],
        default="daily",
    )
    nudge_hour = models.PositiveSmallIntegerField(default=19)  # local hour, 0-23
    snooze_until = models.DateTimeField(null=True, blank=True)
    last_nudge_on = models.DateField(null=True, blank=True)
    last_nudge_key = models.CharField(max_length=32, blank=True, default="")  # never the same line twice running

    # Cards whose banner this chat has already been shown (see cards.ONCE).
    seen_cards = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user_id} ⇄ {self.chat_id}"


class TelegramLinkCode(models.Model):
    """A short code the app shows and the bot swallows once, within 15 minutes."""

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="telegram_codes")
    code = models.CharField(max_length=16, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_usable(self):
        return self.used_at is None and timezone.now() < self.expires_at


class TelegramDraft(models.Model):
    """
    What the bear read out of a receipt or a voice note, waiting for a yes.

    Kept server-side because a Telegram button can only carry 64 bytes — the
    button holds this row's short key, not the money.
    """

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    link = models.ForeignKey(TelegramLink, on_delete=models.CASCADE, related_name="drafts")
    key = models.CharField(max_length=12, unique=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["link", "-created_at"])]


class TelegramUpdate(models.Model):
    """
    Update ids already handled. Telegram retries a webhook it thinks failed, and
    a retried receipt must not be saved twice.
    """

    update_id = models.BigIntegerField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TelegramAsset(models.Model):
    """
    What Telegram gave back when a card was uploaded. Sending a `file_id`
    instead of the bytes is instant and free, so each picture travels once.
    """

    key = models.CharField(max_length=32, primary_key=True)
    file_id = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.key


class TelegramQuiz(models.Model):
    """
    A quiz poll the bot sent. Telegram reports the answer later as a separate
    `poll_answer` update that carries only the poll id, so this row is how the
    answer finds its question — and its learner.
    """

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    poll_id = models.CharField(max_length=64, unique=True)
    link = models.ForeignKey(TelegramLink, on_delete=models.CASCADE, related_name="quizzes")
    question = models.ForeignKey("learning.DailyQuestion", on_delete=models.CASCADE, related_name="+")
    answered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.poll_id} · {self.question_id}"
