"""
Free-standing user notes.

A note is the same kind of artefact as a lesson document — rich HTML produced by
the Tiptap document editor — so the two stay interchangeable: ``Note.content``
mirrors ``learning.LessonProgress.edited_content``. Conventions match the other
apps: UUIDv7 PKs, FK to ``settings.AUTH_USER_MODEL``, ``Meta.indexes`` for hot reads.
"""
import html as html_module
import re

import uuid6

from config import languages

from django.conf import settings
from django.db import models
from django.utils.html import strip_tags

EXCERPT_LENGTH = 280
TITLE_FALLBACK_LENGTH = 60

# Block-level tags become a space so words either side don't run together once
# the tags are stripped ("<p>a</p><p>b</p>" → "a b", not "ab"). Non-capturing so
# re.split() doesn't hand the tag names back as segments.
_BLOCK_BOUNDARY = re.compile(r"(?i)</?(?:br|p|h[1-6]|li|tr|div|blockquote|pre)[^>]*>")


def html_to_text(value):
    """Collapse editor HTML into a single-line plain-text string."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", html_module.unescape(strip_tags(_BLOCK_BOUNDARY.sub(" ", value)))).strip()


def first_block_text(value):
    """Plain text of the first non-empty block — an untitled note's implied title."""
    for chunk in _BLOCK_BOUNDARY.split(value or ""):
        text = html_to_text(chunk)
        if text:
            return text
    return ""


# What a note without a title is called, in the reader's language.
UNTITLED = {"en": "Untitled note", "ru": "Без названия", "uz": "Nomsiz eslatma"}


class Note(models.Model):
    """One user-authored document. Ordered pinned-first, then most recently touched."""

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notes")
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField(blank=True, default="")
    # Denormalised plain-text preview, refreshed whenever content changes, so the
    # grid and the rail can render previews without shipping the full HTML body.
    excerpt = models.CharField(max_length=EXCERPT_LENGTH, blank=True)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
            models.Index(fields=["user", "-is_pinned", "-updated_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} · {self.display_title}"

    @property
    def display_title(self):
        return self.title.strip() or languages.pick(UNTITLED)

    def apply_content(self, value):
        """Set the body and keep the derived excerpt (and any implied title) in sync."""
        self.content = value or ""
        text = html_to_text(self.content)
        self.excerpt = text[:EXCERPT_LENGTH]
        # An untitled note borrows its first line, the way a doc editor would.
        if not self.title.strip():
            self.title = first_block_text(self.content)[:TITLE_FALLBACK_LENGTH].strip()
