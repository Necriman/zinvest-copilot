"""
Uploaded files kept in the database (settings.MEDIA_STORAGE = "db").

For hosts with no disk that outlives a request, like Vercel functions. Avatars,
employee and product photos and the bear's voice clips are small, and the
database is already backed up, so a table is the simplest place for them.
"""
from django.db import models


class StoredFile(models.Model):
    # The storage name, e.g. "avatars/<uuid>.webp" or "tts/<hash>.mp3".
    name = models.CharField(max_length=255, unique=True)
    content = models.BinaryField()
    size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
