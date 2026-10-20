from django.urls import path

from . import views

urlpatterns = [
    path("state", views.state, name="copilot-state"),
    path("settings", views.settings_view, name="copilot-settings"),
    path("entries", views.entries, name="copilot-entries"),
    path("analysis", views.analysis, name="copilot-analysis"),
    path("runway", views.runway, name="copilot-runway"),
    path("loan", views.loan, name="copilot-loan"),
    path("plan", views.plan, name="copilot-plan"),
    path("actions/<uuid:action_id>/decide", views.decide, name="copilot-decide"),
    path("history", views.history, name="copilot-history"),
]
