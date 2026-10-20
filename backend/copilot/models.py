"""
Zinvest Copilot: an AI that does a small business's finance work — reads its
income and expenses, analyses them, warns when the money will run out, picks a
bank loan and writes a business plan — and changes nothing on its own.

Every piece of work the AI does is a CopilotAction. It starts as a proposal
("pending") that says exactly what it would change; only the owner's
"Approve" applies it, and "Reject" leaves everything as it was. The actions,
with their decisions, are the history page.
"""
import uuid6

from django.conf import settings
from django.db import models


class CopilotAction(models.Model):
    class Kind(models.TextChoices):
        ENTRIES = "entries", "Read income and expenses"
        ANALYSIS = "analysis", "Financial analysis"
        RUNWAY = "runway", "Cash runway warning"
        LOAN = "loan", "Bank loan match"
        PLAN = "plan", "Business plan"

    class Status(models.TextChoices):
        PENDING = "pending", "Waiting for approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="copilot_actions")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    # What the AI produced, and the list of changes an approval would make.
    payload = models.JSONField(default=dict)
    effects = models.JSONField(default=list)
    # What the decision actually did, e.g. [{"type": "added_entries", "count": 6},
    # {"type": "created_tasks", "count": 3}]; shown in the reader's language.
    outcome = models.JSONField(default=list)
    language = models.CharField(max_length=4, default="en")
    model_version = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user_id} · {self.kind} · {self.status}"
