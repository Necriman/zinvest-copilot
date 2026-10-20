from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from adminpanel import public
from adminpanel.django_admin import throttled_admin_login
from config import cron
from files import views as files_views

urlpatterns = [
    path("api/auth/", include("accounts.urls")),
    path("api/ai/", include("ai_engine.urls")),
    path("api/learning/", include("learning.urls")),
    path("api/startup/", include("startup.urls")),
    path("api/copilot/", include("copilot.urls")),
    path("api/admin/", include("adminpanel.urls")),
    path("api/telegram/", include("telegrambot.urls")),
    path("api/announcements", public.announcements, name="announcements"),
    path("api/reports", public.report, name="reports"),
    path("api/cron/<str:job>", cron.run, name="cron"),
    path("api/", include("notes.urls")),
]

if settings.DJANGO_ADMIN_ENABLED:
    # Django's own admin (superusers only), off in production by default. Its
    # path comes from DJANGO_ADMIN_PATH so it can move off the well-known
    # /admin/; sign-in is throttled like the app's.
    urlpatterns = [
        path(f"{settings.DJANGO_ADMIN_PATH}login/", throttled_admin_login),
        path(settings.DJANGO_ADMIN_PATH, admin.site.urls),
    ] + urlpatterns

if settings.MEDIA_STORAGE == "db":
    # Uploads kept in the database (no disk on the host): Django serves them.
    urlpatterns += [path(f"{settings.MEDIA_URL.strip('/')}/<path:name>", files_views.serve, name="media")]
elif settings.DEBUG:
    # Dev only — in production Nginx serves /media/ straight off disk.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
