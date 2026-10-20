from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from django.utils.encoding import filepath_to_uri

from .models import StoredFile

# What a stored file is served as, chosen by the server from the extension it
# gave the file. Never the Content-Type the uploader's browser sent: a "photo"
# declared as text/html would otherwise run as a page on our own origin.
SAFE_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp",
    "mp3": "audio/mpeg", "wav": "audio/wav",
}


def type_for(name):
    return SAFE_TYPES.get(name.rsplit(".", 1)[-1].lower(), "application/octet-stream")


@deconstructible
class DatabaseStorage(Storage):
    """Django storage over files.StoredFile; served by files.views.serve."""

    def _open(self, name, mode="rb"):
        row = StoredFile.objects.filter(name=name).only("content").first()
        if row is None:
            raise FileNotFoundError(name)
        return ContentFile(bytes(row.content), name=name)

    def _save(self, name, content):
        if hasattr(content, "seek"):
            content.seek(0)
        data = b"".join(content.chunks()) if hasattr(content, "chunks") else content.read()
        content_type = type_for(name)
        StoredFile.objects.update_or_create(
            name=name, defaults={"content": data, "size": len(data), "content_type": content_type}
        )
        return name

    def exists(self, name):
        return StoredFile.objects.filter(name=name).exists()

    def delete(self, name):
        StoredFile.objects.filter(name=name).delete()

    def size(self, name):
        row = StoredFile.objects.filter(name=name).only("size").first()
        if row is None:
            raise FileNotFoundError(name)
        return row.size

    def url(self, name):
        return settings.MEDIA_URL + filepath_to_uri(name)

    def get_created_time(self, name):
        row = StoredFile.objects.filter(name=name).only("created_at").first()
        if row is None:
            raise FileNotFoundError(name)
        return row.created_at

    get_modified_time = get_created_time
