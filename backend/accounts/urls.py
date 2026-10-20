from django.urls import path

from . import google, views

urlpatterns = [
    path("register", views.register, name="register"),
    path("login", views.login, name="login"),
    path("code/verify", views.code_verify, name="code-verify"),
    path("code/resend", views.code_resend, name="code-resend"),
    path("google/start", google.start, name="google-start"),
    path("google/callback", google.callback, name="google-callback"),
    path("refresh", views.refresh, name="refresh"),  # -> /api/auth/refresh (matches cookie path)
    path("logout", views.logout, name="logout"),
    path("forgot-password", views.forgot_password, name="forgot-password"),
    path("password-reset", views.password_reset, name="password-reset"),
    path("verify-email", views.verify_email, name="verify-email"),
    path("verify-email/resend", views.resend_verification, name="verify-email-resend"),
    path("me", views.me, name="me"),
    path("me/avatar", views.avatar, name="me-avatar"),
    path("me/password", views.change_password, name="me-password"),
    path("me/email", views.change_email, name="me-email"),
    path("me/delete", views.delete_account, name="me-delete"),
    path("me/export", views.export_data, name="me-export"),
    path("sessions", views.sessions, name="sessions"),
    path("sessions/revoke-others", views.revoke_other_sessions, name="sessions-revoke-others"),
    path("sessions/<uuid:family_id>", views.session_detail, name="session-detail"),
]
