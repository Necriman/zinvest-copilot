"""Writing to the admin audit log."""
import logging

from accounts import security

from .models import AuditLog

log = logging.getLogger("adminpanel")


def audit(request, action, *, target_type="", target_id="", summary="", **details):
    actor = getattr(request, "auth_user", None)
    try:
        AuditLog.objects.create(
            actor=actor,
            actor_email=getattr(actor, "email", "") or "",
            action=action,
            target_type=target_type,
            target_id=str(target_id or ""),
            summary=summary[:300],
            details=details,
            ip_address=security.client_ip(request),
        )
    except Exception:
        log.exception("could not write audit log for %s", action)
    log.info("admin_action actor=%s action=%s target=%s:%s", getattr(actor, "pk", None), action, target_type, target_id)
