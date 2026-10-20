"""
AI token-quota gate + post-call accounting.

``@check_ai_quota`` must sit BELOW ``@require_auth`` (so ``request.auth_user`` is
set). It rejects a request with 429 when the cycle allowance is spent, but it
deliberately does NOT hold the quota row lock across the (multi-second) Gemini
network call — that would serialize a user's AI calls and pin a DB connection.

The lock is therefore taken twice, briefly: once here for the pre-flight gate,
and again in ``consume_and_log`` after the call to record actual usage. This
makes the cap a *soft* one — two requests near the limit can both pass the gate
and overshoot by at most one in-flight request. That is an accepted trade-off,
consistent with the refresh view's locking discipline in accounts/views.py.
"""
from functools import wraps

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from .models import AIUsageLog, UserAIQuota


def check_ai_quota(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = getattr(request, "auth_user", None)
        if user is None:
            # Decorator misordering: @check_ai_quota was placed above @require_auth.
            return JsonResponse({"detail": "Server auth misconfiguration."}, status=500)

        from adminpanel.models import PlatformSettings  # local: adminpanel imports ai_engine

        if not PlatformSettings.current().ai_enabled:
            return JsonResponse({"detail": "AI features are paused by the Zinvest team. Please try again later.", "code": "ai_paused"}, status=503)

        UserAIQuota.get_or_create_for(user)  # ensure the row exists (unlocked)

        with transaction.atomic():
            quota = UserAIQuota.objects.select_for_update().get(user=user)
            if quota.maybe_rollover(timezone.localdate()):
                quota.save(update_fields=["tokens_used_this_cycle", "reset_date", "updated_at"])
            if not quota.has_allowance():
                return JsonResponse(
                    {
                        "detail": "AI token quota exhausted for this cycle.",
                        "reset_date": quota.reset_date.isoformat(),
                    },
                    status=429,
                )
        # Row lock released here — never held across the model call below.
        request.ai_quota = quota
        return view_func(request, *args, **kwargs)

    return wrapper


def consume_and_log(user, feature, result):
    """
    Record token usage and advance the cycle counter atomically, AFTER the model
    call (token counts are only known post-call). Re-locks the quota row.
    """
    total = (result.input_tokens or 0) + (result.output_tokens or 0)
    UserAIQuota.get_or_create_for(user)
    with transaction.atomic():
        quota = UserAIQuota.objects.select_for_update().get(user=user)
        quota.maybe_rollover(timezone.localdate())  # cycle may have turned over mid-call
        quota.consume(total)
        quota.save(update_fields=["tokens_used_this_cycle", "bonus_tokens", "reset_date", "updated_at"])
        AIUsageLog.objects.create(
            user=user,
            feature=feature,
            model_version=result.model_version,
            input_tokens=result.input_tokens or 0,
            output_tokens=result.output_tokens or 0,
        )
    return quota


def add_bonus(user, tokens):
    """
    Extra AI tokens earned by learning (settings.AI_BONUS_PER_LESSON, _PER_STREAK_DAY).
    They count for the current cycle only and lapse with it, like the allowance.
    """
    tokens = int(tokens or 0)
    if tokens <= 0:
        return None
    UserAIQuota.get_or_create_for(user)
    with transaction.atomic():
        quota = UserAIQuota.objects.select_for_update().get(user=user)
        quota.maybe_rollover(timezone.localdate())  # a bonus earned in a new month counts for that month
        quota.bonus_tokens += tokens
        quota.save(update_fields=["bonus_tokens", "tokens_used_this_cycle", "reset_date", "updated_at"])
    return quota


def quota_dict(quota):
    return {
        "tier": quota.tier,
        "used": quota.tokens_used_this_cycle,
        "limit": quota.total_limit(),  # what the percentages are of: allowance + earned bonus
        "base_limit": quota.monthly_token_limit,
        "bonus": quota.bonus_tokens,
        "remaining": quota.remaining(),
        "reset_date": quota.reset_date.isoformat(),
    }
