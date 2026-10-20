from django.contrib import admin

from .models import Assignment, CashFlowEntry, Employee, Product, StartupProfile, StartupTodo


@admin.register(StartupProfile)
class StartupProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "industry", "currency", "onboarding_completed", "updated_at")
    list_filter = ("onboarding_completed",)
    search_fields = ("user__email", "name")


@admin.register(CashFlowEntry)
class CashFlowEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "entry_type", "category", "amount", "occurred_on")
    list_filter = ("entry_type",)
    search_fields = ("user__email", "category")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "salary", "created_at")
    search_fields = ("user__email", "full_name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "price", "created_at")
    search_fields = ("user__email", "name")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("employee", "title", "start_date", "end_date", "done")
    list_filter = ("done",)
    search_fields = ("employee__full_name", "title")


@admin.register(StartupTodo)
class StartupTodoAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "done", "created_at")
    list_filter = ("done",)
    search_fields = ("user__email", "title")
