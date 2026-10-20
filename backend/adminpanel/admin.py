from django.contrib import admin

from .models import Announcement, AuditLog, PlatformSettings, Report


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor_email", "action", "summary", "ip_address")
    search_fields = ("actor_email", "action", "summary", "target_id")
    list_filter = ("action",)

    # Append-only, also here.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("created_at", "target_type", "reason", "status", "reporter", "target_user")
    list_filter = ("status", "reason", "target_type")


admin.site.register(Announcement)
admin.site.register(PlatformSettings)
