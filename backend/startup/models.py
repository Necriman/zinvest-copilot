"""
"My Startup" simulation: a per-user startup profile plus the founder's workspace
blocks — cash-flow entries, employees, products, employee task assignments and a
startup-scoped to-do list.

Revenue / spending / net are DERIVED via aggregation (never stored). Amounts are
DecimalField and serialized as strings to avoid float drift in JSON.
"""
import uuid

import uuid6

from django.conf import settings
from django.db import models
from django.utils import timezone


def employee_photo_upload_to(instance, filename):
    """Per-employee folder, random basename so a replaced photo can't be cached."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "png").lower()[:8]
    return f"startup/employees/{instance.pk}/{uuid.uuid4().hex}.{ext}"


def product_image_upload_to(instance, filename):
    """Per-product folder, random basename so a replaced image can't be cached."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "png").lower()[:8]
    return f"startup/products/{instance.pk}/{uuid.uuid4().hex}.{ext}"


class StartupProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="startup")
    name = models.CharField(max_length=120, blank=True)
    industry = models.CharField(max_length=80, blank=True)
    # Raw answers to the five onboarding questions (structured client-side).
    onboarding = models.JSONField(null=True, blank=True)
    # AI output of POST /api/startup/onboarding: {analysis, enabled: [block keys]}.
    blocks = models.JSONField(null=True, blank=True)
    onboarding_completed = models.BooleanField(default=False)
    currency = models.CharField(max_length=8, default="USD")
    operating_mode = models.CharField(max_length=10, default="online")
    locations = models.JSONField(default=list, blank=True)
    demand = models.JSONField(default=dict, blank=True)
    public_visible = models.BooleanField(default=False)
    public_summary = models.TextField(blank=True)
    # The AI roadmap (startup.roadmap): where the startup stands and the steps
    # ahead, grouped in phases, with the founder's progress on each step.
    roadmap = models.JSONField(default=dict, blank=True)
    # Zinvest Copilot (copilot app): the owner's cash and legal form, and the
    # results the owner approved (analysis, runway, loan, plan).
    copilot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id} · {self.name or 'Untitled startup'}"


class CashFlowEntry(models.Model):
    class Type(models.TextChoices):
        REVENUE = "revenue", "Revenue"
        SPENDING = "spending", "Spending"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cashflow_entries")
    entry_type = models.CharField(max_length=10, choices=Type.choices)
    category = models.CharField(max_length=80)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    description = models.CharField(max_length=200, blank=True)
    cost_type = models.CharField(max_length=10, default="variable")
    occurred_on = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_on", "-created_at"]
        indexes = [
            models.Index(fields=["user", "occurred_on"]),
            models.Index(fields=["user", "entry_type"]),
        ]

    def __str__(self):
        return f"{self.user_id} · {self.entry_type} · {self.amount}"


class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="startup_employees")
    full_name = models.CharField(max_length=120)
    position = models.CharField(max_length=80, blank=True)  # job title shown on the card: "CTO", "Chef"
    role = models.TextField(blank=True)  # free-text "what they do" note
    team = models.CharField(max_length=80, blank=True)
    salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # FileField (not ImageField): the view sniffs the magic bytes itself, so we
    # avoid pulling in Pillow just to validate the upload.
    photo = models.FileField(upload_to=employee_photo_upload_to, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["user", "created_at"])]

    def __str__(self):
        return f"{self.user_id} · {self.full_name}"


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="startup_products")
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=12, default="product")
    price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    image = models.FileField(upload_to=product_image_upload_to, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["user", "created_at"])]

    def __str__(self):
        return f"{self.user_id} · {self.name}"


class Assignment(models.Model):
    """A task the founder hands to a specific employee (Task-Dashboard block)."""
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=200)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["done", "start_date", "created_at"]
        indexes = [models.Index(fields=["employee", "done"])]

    def __str__(self):
        return f"{self.employee_id} · {'x' if self.done else ' '} {self.title}"


class StartupTodo(models.Model):
    """Business to-dos, kept separate from the learner's daily study tasks."""
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="startup_todos")
    title = models.CharField(max_length=200)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["done", "created_at"]
        indexes = [models.Index(fields=["user", "done", "created_at"])]

    def __str__(self):
        return f"{self.user_id} · {'x' if self.done else ' '} {self.title}"


class FounderConnection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_connections")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_connections")
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["sender", "recipient"], name="unique_founder_request")]


class FounderMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    connection = models.ForeignKey(FounderConnection, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class BusinessPost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    text = models.TextField(blank=True)
    image = models.FileField(upload_to=product_image_upload_to, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Hidden by the team after a report: gone from the feed, still visible to its author.
    is_hidden = models.BooleanField(default=False)
    hidden_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
