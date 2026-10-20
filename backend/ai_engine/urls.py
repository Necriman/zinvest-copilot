from django.urls import path

from . import views

urlpatterns = [
    path("advisor", views.advisor, name="ai-advisor"),
    path("context", views.ai_context, name="ai-context"),
    path("onboarding/parse", views.onboarding_parse, name="ai-onboarding-parse"),
    path("quota", views.quota_status, name="ai-quota"),
    path("tts", views.tts, name="ai-tts"),
]
