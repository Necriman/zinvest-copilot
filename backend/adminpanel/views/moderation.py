"""Reports from learners and the founder network's posts."""
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.models import RefreshToken, User
from startup.models import BusinessPost

from ..audit import audit
from ..models import Report
from ..permissions import OWNER, staff_required
from .common import body, iso, method_not_allowed, paginate


def _user_brief(u):
    if u is None:
        return None
    return {"id": str(u.pk), "email": u.email, "name": u.full_name, "is_active": u.is_active}


def _report_dict(r):
    return {
        "id": str(r.id),
        "target_type": r.target_type,
        "target_id": r.target_id,
        "reason": r.reason,
        "reason_label": r.get_reason_display(),
        "comment": r.comment,
        "snapshot": r.snapshot,
        "status": r.status,
        "resolution": r.resolution,
        "reporter": _user_brief(r.reporter),
        "target_user": _user_brief(r.target_user),
        "resolved_by": r.resolved_by.email if r.resolved_by else None,
        "resolved_at": iso(r.resolved_at),
        "created_at": iso(r.created_at),
        "same_target": Report.objects.filter(target_type=r.target_type, target_id=r.target_id).count(),
    }


@staff_required("moderation.view")
def reports(request):
    if request.method != "GET":
        return method_not_allowed()
    qs = Report.objects.select_related("reporter", "target_user", "resolved_by").order_by("-created_at")
    status = request.GET.get("status", "open")
    if status in dict(Report.Status.choices):
        qs = qs.filter(status=status)
    return JsonResponse(paginate(request, qs, _report_dict))


def _hide_post(post, reason):
    post.is_hidden = True
    post.hidden_reason = reason[:300]
    post.save(update_fields=["is_hidden", "hidden_reason"])


@staff_required("moderation.manage", write=True)
def report_detail(request, report_id):
    """POST {status: resolved|dismissed, note, action: none|hide_post|disable_user}"""
    if request.method != "POST":
        return method_not_allowed()
    report = get_object_or_404(Report.objects.select_related("target_user"), pk=report_id)
    data, err = body(request)
    if err:
        return err
    status = data.get("status")
    if status not in (Report.Status.RESOLVED, Report.Status.DISMISSED):
        return JsonResponse({"detail": "Resolve or dismiss the report."}, status=400)
    note = str(data.get("note") or "").strip()[:500]
    action = data.get("action") or "none"
    if action == "hide_post":
        if report.target_type != Report.Target.POST:
            return JsonResponse({"detail": "Only posts can be hidden."}, status=400)
        post = BusinessPost.objects.filter(pk=report.target_id).first()
        if post:
            _hide_post(post, note or report.get_reason_display())
    elif action == "disable_user":
        target = report.target_user
        if target is None:
            return JsonResponse({"detail": "This report has no account attached."}, status=400)
        if target.pk == request.auth_user.pk or ((target.is_superuser or target.staff_role) and request.admin_role != OWNER):
            return JsonResponse({"detail": "Only an owner can disable a team account."}, status=403)
        target.is_active = False
        target.disabled_reason = (note or f"Report: {report.get_reason_display()}")[:300]
        target.tokens_valid_after = timezone.now()
        target.save(update_fields=["is_active", "disabled_reason", "tokens_valid_after"])
        RefreshToken.objects.filter(user=target, is_revoked=False).update(is_revoked=True)
    elif action != "none":
        return JsonResponse({"detail": "Unknown action."}, status=400)
    # Close every open report about the same thing in one go.
    closed = Report.objects.filter(target_type=report.target_type, target_id=report.target_id, status=Report.Status.OPEN).update(
        status=status, resolution=note, resolved_by=request.auth_user, resolved_at=timezone.now()
    )
    audit(request, f"report.{status}", target_type="report", target_id=report.pk,
          summary=f"{status.title()} {closed} report(s) on {report.target_type} {report.target_id} ({action})", taken=action, note=note)
    report.refresh_from_db()
    return JsonResponse(_report_dict(report))


def _post_dict(p):
    return {
        "id": str(p.id), "title": p.title, "text": p.text[:600], "image_url": p.image.url if p.image else None,
        "author": _user_brief(p.user), "company": getattr(getattr(p.user, "startup", None), "name", ""),
        "hidden": p.is_hidden, "hidden_reason": p.hidden_reason, "created_at": iso(p.created_at),
        "reports": Report.objects.filter(target_type=Report.Target.POST, target_id=str(p.id)).count(),
    }


@staff_required("moderation.view")
def posts(request):
    if request.method != "GET":
        return method_not_allowed()
    qs = BusinessPost.objects.select_related("user", "user__startup").order_by("-created_at")
    if request.GET.get("hidden") == "1":
        qs = qs.filter(is_hidden=True)
    q = request.GET.get("q", "").strip()[:120]
    if q:
        qs = qs.filter(models.Q(title__icontains=q) | models.Q(text__icontains=q) | models.Q(user__email__icontains=q))
    return JsonResponse(paginate(request, qs, _post_dict))


@staff_required("moderation.manage", write=True)
def post_detail(request, post_id):
    """POST {hidden: bool, reason}"""
    if request.method != "POST":
        return method_not_allowed()
    post = get_object_or_404(BusinessPost.objects.select_related("user"), pk=post_id)
    data, err = body(request)
    if err:
        return err
    hidden = bool(data.get("hidden"))
    reason = str(data.get("reason") or "").strip()[:300]
    if hidden and not reason:
        return JsonResponse({"detail": "Say why the post is hidden."}, status=400)
    if hidden:
        _hide_post(post, reason)
    else:
        post.is_hidden = False
        post.hidden_reason = ""
        post.save(update_fields=["is_hidden", "hidden_reason"])
    audit(request, "post.hidden" if hidden else "post.shown", target_type="post", target_id=post.pk,
          summary=f"{'Hid' if hidden else 'Restored'} the post “{post.title}” by {post.user.email}", reason=reason)
    return JsonResponse(_post_dict(post))
