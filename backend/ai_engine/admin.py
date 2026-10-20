from django.contrib import admin

from .models import AIUsageLog, UserAIQuota


@admin.register(UserAIQuota)
class UserAIQuotaAdmin(admin.ModelAdmin):
    list_display = ("user", "tier", "tokens_used_this_cycle", "monthly_token_limit", "reset_date")
    list_filter = ("tier",)
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = ("user", "feature", "model_version", "input_tokens", "output_tokens", "created_at")
    list_filter = ("feature", "model_version")
    search_fields = ("user__email",)
    readonly_fields = ("created_at",)
