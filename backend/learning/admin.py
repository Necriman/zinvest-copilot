from django.contrib import admin

from .models import (
    DailyActivity,
    Lesson,
    LessonProgress,
    Task,
    Unit,
    UnitProgress,
    UnitTestResult,
    UserStats,
)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ("order", "title", "slug", "coin_reward", "estimated_minutes")
    ordering = ("order",)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "order", "accent_color")
    ordering = ("order",)
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("unit", "order", "title", "coin_reward")
    list_filter = ("unit",)
    ordering = ("unit", "order")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "status", "completed_at")
    list_filter = ("status",)
    search_fields = ("user__email",)


@admin.register(UnitProgress)
class UnitProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "unit", "status", "best_test_score", "test_passed")
    list_filter = ("status", "test_passed")
    search_fields = ("user__email",)


@admin.register(UnitTestResult)
class UnitTestResultAdmin(admin.ModelAdmin):
    list_display = ("user", "unit", "score", "passed", "created_at")
    list_filter = ("passed",)
    search_fields = ("user__email",)


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    list_display = ("user", "coins", "day_streak", "longest_streak", "weekly_rank", "target_score")
    search_fields = ("user__email",)


@admin.register(DailyActivity)
class DailyActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "date")
    search_fields = ("user__email",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "done", "order", "completed_at")
    list_filter = ("done",)
    search_fields = ("user__email", "title")
