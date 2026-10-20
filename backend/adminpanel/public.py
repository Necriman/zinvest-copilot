"""
The parts of the admin panel learners touch:

  GET  /api/announcements   live banners for this learner + the maintenance note
  POST /api/reports         flag a post, a founder or a message
"""
from datetime import timedelta

from django.db import IntegrityError, models, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts import security
from accounts.auth import require_auth
from startup.models import BusinessPost, FounderMessage, StartupProfile

from .models import Announcement, PlatformSettings, Report
from .views.common import body, iso, method_not_allowed


@csrf_exempt
@require_auth
def announcements(request):
    if request.method != "GET":
        return method_not_allowed()
    user = request.auth_user
    now = timezone.now()
    live = Announcement.objects.filter(is_active=True, starts_at__lte=now).filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=now))
    is_new = user.date_joined >= now - timedelta(days=14)
    is_founder = StartupProfile.objects.filter(user=user, onboarding_completed=True).exists()
    items = [
        {"id": str(a.id), "title": a.title, "body": a.body, "link_url": a.link_url, "link_label": a.link_label, "level": a.level, "starts_at": iso(a.starts_at)}
        for a in live.order_by("-starts_at")[:5]
        if a.audience == Announcement.Audience.ALL
        or (a.audience == Announcement.Audience.NEW and is_new)
        or (a.audience == Announcement.Audience.FOUNDERS and is_founder)
    ]
    return JsonResponse({"maintenance_message": PlatformSettings.current().maintenance_message, "announcements": items})


def _target(user, target_type, target_id):
    """(target_user, snapshot) if the reporter can actually see the target, else None."""
    if target_type == Report.Target.POST:
        post = BusinessPost.objects.filter(pk=target_id, user__is_active=True).select_related("user").first()
        if post is None or post.user_id == user.pk or (post.is_hidden and post.user_id != user.pk):
            return None
        return post.user, {"title": post.title, "text": post.text[:1000]}
    if target_type == Report.Target.USER:
        profile = StartupProfile.objects.filter(user_id=target_id, public_visible=True, user__is_active=True).select_related("user").first()
        if profile is None or profile.user_id == user.pk:
            return None
        return profile.user, {"company": profile.name, "summary": profile.public_summary[:1000], "name": profile.user.full_name}
    if target_type == Report.Target.MESSAGE:
        message = (
            FounderMessage.objects.filter(pk=target_id)
            .filter(models.Q(connection__sender=user) | models.Q(connection__recipient=user))
            .exclude(sender=user).select_related("sender").first()
        )
        if message is None:
            return None
        return message.sender, {"text": message.text[:1000], "sent_at": iso(message.created_at)}
    return None


@csrf_exempt
@require_auth
def report(request):
    """POST {target_type: post|user|message, target_id, reason, comment}"""
    if request.method != "POST":
        return method_not_allowed()
    user = request.auth_user
    data, err = body(request)
    if err:
        return err
    target_type = data.get("target_type")
    target_id = str(data.get("target_id") or "")[:64]
    reason = data.get("reason")
    if target_type not in dict(Report.Target.choices) or not target_id:
        return JsonResponse({"detail": "Unknown report target."}, status=400)
    if reason not in dict(Report.Reason.choices):
        return JsonResponse({"detail": "Choose a reason."}, status=400)
    try:
        found = _target(user, target_type, target_id)
    except Exception:  # malformed ids
        found = None
    if found is None:
        return JsonResponse({"detail": "Nothing to report here."}, status=404)
    if not security.hit("report", user.pk, 20, 24 * 3600):
        return JsonResponse({"detail": "You have sent a lot of reports today. The team will get to them."}, status=429)
    target_user, snapshot = found
    try:
        with transaction.atomic():  # a savepoint, so a duplicate does not poison an outer transaction
            Report.objects.create(
                reporter=user, target_type=target_type, target_id=target_id, target_user=target_user,
                reason=reason, comment=str(data.get("comment") or "").strip()[:1000], snapshot=snapshot,
            )
    except IntegrityError:
        pass  # already reported and still open: same answer, nothing to add
    return JsonResponse({"ok": True, "detail": "Thanks. The team will take a look."}, status=201)
