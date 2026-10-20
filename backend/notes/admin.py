from django.contrib import admin

from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("user", "display_title", "is_pinned", "updated_at")
    list_filter = ("is_pinned",)
    search_fields = ("user__email", "title", "excerpt")
    readonly_fields = ("excerpt", "created_at", "updated_at")
