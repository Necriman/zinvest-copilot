"""
Data the admin panel owns: the audit log of staff actions, reports from
learners, in-app announcements, platform switches and step-up grants.
"""
import uuid6

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """Append-only: who on the team did what, to whom, from where."""

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    actor_email = models.CharField(max_length=254, blank=True)  # kept if the actor is deleted
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=32, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    summary = models.CharField(max_length=300, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]


class Report(models.Model):
    """A learner flags a post, a founder or a message for the team to review."""

    class Target(models.TextChoices):
        POST = "post", "Post"
        USER = "user", "Founder"
        MESSAGE = "message", "Message"

    class Reason(models.TextChoices):
        SPAM = "spam", "Spam or ads"
        ABUSE = "abuse", "Harassment or hate"
        FRAUD = "fraud", "Scam or fraud"
        INAPPROPRIATE = "inappropriate", "Inappropriate content"
        OTHER = "other", "Something else"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="reports_made")
    target_type = models.CharField(max_length=16, choices=Target.choices)
    target_id = models.CharField(max_length=64)
    # The reported account, when there is one, so its history is one query away.
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reports_received")
    reason = models.CharField(max_length=16, choices=Reason.choices)
    comment = models.CharField(max_length=1000, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)  # what the reporter saw, in case it is edited later
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    resolution = models.CharField(max_length=500, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["status", "-created_at"])]
        constraints = [
            # One open report per reporter and target: no flooding the queue.
            models.UniqueConstraint(
                fields=["reporter", "target_type", "target_id"],
                condition=models.Q(status="open"),
                name="one_open_report_per_target",
            )
        ]


class Announcement(models.Model):
    """A banner shown inside the app (maintenance, new features, promotions)."""

    class Level(models.TextChoices):
        INFO = "info", "Info"
        SUCCESS = "success", "Good news"
        WARNING = "warning", "Warning"

    class Audience(models.TextChoices):
        ALL = "all", "Everyone"
        NEW = "new", "Joined in the last 14 days"
        FOUNDERS = "founders", "Founders with a startup profile"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=500, blank=True)
    link_url = models.CharField(max_length=300, blank=True)  # internal path or https URL
    link_label = models.CharField(max_length=40, blank=True)
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    audience = models.CharField(max_length=10, choices=Audience.choices, default=Audience.ALL)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["is_active", "starts_at"])]

    def live(self, now=None):
        now = now or timezone.now()
        return self.is_active and self.starts_at <= now and (self.ends_at is None or now < self.ends_at)


class PlatformSettings(models.Model):
    """Switches the team can flip without a deploy. A single row (pk=1)."""

    registration_open = models.BooleanField(default=True)
    ai_enabled = models.BooleanField(default=True)
    tts_enabled = models.BooleanField(default=True)
    network_posting_enabled = models.BooleanField(default=True)
    maintenance_message = models.CharField(max_length=300, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    CACHE_KEY = "platform-settings"

    @classmethod
    def current(cls):
        """The settings row, cached for a few seconds (read on every AI call)."""
        obj = cache.get(cls.CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(cls.CACHE_KEY, obj, 10)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)


class SudoGrant(models.Model):
    """
    A recent step-up (password + second factor) for one device session. Bound
    to the refresh-token family, so a stolen access token from another device
    does not inherit it.
    """

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sudo_grants")
    family_id = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "family_id", "expires_at"])]
