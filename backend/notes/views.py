"""
Notes endpoints (native JsonResponse — no DRF). All @require_auth, owner-scoped.

  GET    /api/notes            list (metadata + excerpt, no body)
  POST   /api/notes            create
  GET    /api/notes/<uuid>     full note (with content)
  PATCH  /api/notes/<uuid>     rename / save content / pin
  DELETE /api/notes/<uuid>     remove

Every lookup filters on ``user=request.auth_user`` so one account can never read
or mutate another's note — a 404 is returned rather than a 403 so the endpoint
doesn't confirm that someone else's id exists.
"""
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from accounts.auth import require_auth

from .models import Note

TITLE_MAX = 200


def _json_body(request):
    try:
        return json.loads(request.body or b"{}"), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"detail": "Malformed JSON body."}, status=400)


def _summary(note):
    """List/preview shape — deliberately without the (potentially large) body."""
    return {
        "id": str(note.id),
        "title": note.display_title,
        # The title above is a stand-in when the note has none; the editor
        # shows an empty field instead of offering the stand-in as text.
        "untitled": not note.title.strip(),
        "excerpt": note.excerpt,
        "is_pinned": note.is_pinned,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }


def _detail(note):
    return {**_summary(note), "content": note.content}


@csrf_exempt
@require_auth
def notes(request):
    user = request.auth_user

    if request.method == "GET":
        return JsonResponse({"notes": [_summary(n) for n in Note.objects.filter(user=user)]})
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    data, jerr = _json_body(request)
    if jerr:
        return jerr

    note = Note(user=user, title=str(data.get("title") or "")[:TITLE_MAX])
    note.apply_content(data.get("content") or "")
    note.save()
    return JsonResponse(_detail(note), status=201)


@csrf_exempt
@require_auth
def note_detail(request, note_id):
    note = get_object_or_404(Note, pk=note_id, user=request.auth_user)

    if request.method == "GET":
        return JsonResponse(_detail(note))
    if request.method == "DELETE":
        note.delete()
        return JsonResponse({"status": "deleted"})
    if request.method != "PATCH":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    data, jerr = _json_body(request)
    if jerr:
        return jerr

    if "title" in data:
        note.title = str(data.get("title") or "")[:TITLE_MAX]
    if "content" in data:
        content = data.get("content")
        if not isinstance(content, str):
            return JsonResponse({"detail": "content must be a string."}, status=400)
        note.apply_content(content)
    if "is_pinned" in data:
        note.is_pinned = bool(data.get("is_pinned"))

    # Save unconditionally: auto_now on updated_at is what drives list ordering.
    note.save()
    return JsonResponse(_detail(note))
