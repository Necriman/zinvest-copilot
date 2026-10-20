"""
Django's built-in admin: the same sign-in limits as the app's login endpoint,
a security log entry on failures, and superusers only.
"""
from django.contrib import admin

from accounts import security, throttle
from accounts.models import SecurityEvent

admin.site.site_header = "Zinvest · server admin"
admin.site.site_title = "Zinvest server admin"
# Only superusers get in; the team uses the admin panel inside the app.
admin.site.has_permission = lambda request: bool(request.user.is_active and request.user.is_superuser)


def throttled_admin_login(request, extra_context=None):
    ip = security.client_ip(request) or "unknown"
    email = (request.POST.get("username") or "").strip().lower() if request.method == "POST" else ""
    if request.method == "POST" and throttle.is_locked(ip, email):
        security.record(SecurityEvent.Kind.LOGIN_LOCKED, request, email=email, where="django-admin")
        from django.http import HttpResponse

        return HttpResponse("Too many failed attempts. Try again later.", status=429, content_type="text/plain")
    response = admin.site.login(request, extra_context)
    if request.method == "POST":
        signed_in = response.status_code in (301, 302) and request.user.is_authenticated
        if signed_in:
            throttle.clear(ip, email)
        else:
            throttle.record_failure(ip, email)
            security.record(SecurityEvent.Kind.LOGIN_FAILED, request, email=email, where="django-admin")
    return response
