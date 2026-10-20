from django.urls import path

from . import views
from .challenges import challenges

urlpatterns = [
    path("challenges", challenges, name="learning-challenges"),
    path("daily", views.daily, name="learning-daily"),
    path("daily/answer", views.daily_answer, name="learning-daily-answer"),
    path("practice/next", views.practice_next, name="learning-practice-next"),
    path("practice/answer", views.practice_answer, name="learning-practice-answer"),
    path("predict", views.predict, name="learning-predict"),
    path("predict/answer", views.predict_answer, name="learning-predict-answer"),
    path("stats", views.stats, name="learning-stats"),
    path("league", views.league, name="learning-league"),
    path("stats/goal", views.stats_goal, name="learning-stats-goal"),
    path("tasks", views.tasks, name="learning-tasks"),
    path("tasks/<uuid:task_id>", views.task_detail, name="learning-task-detail"),
    path("units", views.units, name="learning-units"),
    path("study-plan", views.study_plan, name="learning-study-plan"),
    path("next-step", views.next_step, name="learning-next-step"),
    path("today", views.today_plan, name="learning-today"),
    path("study-plan/regenerate", views.regenerate_study_plan, name="learning-study-plan-regenerate"),
    path("onboarding", views.onboarding, name="learning-onboarding"),
    path("lessons", views.lessons_catalog, name="learning-lessons-catalog"),
    path("units/<uuid:unit_id>/study-plan", views.unit_study_plan, name="learning-unit-study-plan"),
    path("units/<uuid:unit_id>/test/start", views.test_start, name="learning-test-start"),
    path("units/<uuid:unit_id>/test/submit", views.test_submit, name="learning-test-submit"),
    path("lessons/<uuid:lesson_id>", views.lesson_detail, name="learning-lesson-detail"),
    path("lessons/<uuid:lesson_id>/practice", views.lesson_practice, name="learning-lesson-practice"),
    path("lessons/<uuid:lesson_id>/save", views.lesson_save, name="learning-lesson-save"),
    path("lessons/<uuid:lesson_id>/complete", views.lesson_complete, name="learning-lesson-complete"),
]
