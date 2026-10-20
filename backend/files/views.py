from django.http import Http404, HttpResponse
from django.views.decorators.http import require_safe

from .models import StoredFile
from .storage import type_for


@require_safe
def serve(request, name):
    """GET /media/<name> for files kept in the database."""
    row = StoredFile.objects.filter(name=name).only("content").first()
    if row is None:
        raise Http404
    # The type comes from the name the server chose, never from the upload.
    content_type = type_for(name)
    response = HttpResponse(bytes(row.content), content_type=content_type)
    # Names are unique per upload (avatars get a new name each time, voice
    # clips are named by their text), so the CDN may keep them for a day.
    response["Cache-Control"] = "public, max-age=86400"
    response["X-Content-Type-Options"] = "nosniff"
    # Even if something slipped through, nothing served from here may run
    # script, load anything or be read by another site.
    response["Content-Security-Policy"] = "default-src 'none'; img-src 'self'; media-src 'self'; style-src 'unsafe-inline'; sandbox"
    response["Cross-Origin-Resource-Policy"] = "same-origin"
    if content_type == "application/octet-stream":
        response["Content-Disposition"] = "attachment"
    return response
