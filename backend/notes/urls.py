from django.urls import path

from . import views

# Mounted under "api/" (not "api/notes/") so the collection itself stays
# slash-free — /api/notes — matching the convention in the other apps.
urlpatterns = [
    path("notes", views.notes, name="notes-list"),
    path("notes/<uuid:note_id>", views.note_detail, name="notes-detail"),
]
