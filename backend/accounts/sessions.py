"""
Signing a person out everywhere, in one place.

A session is more than refresh tokens: the access tokens already handed out,
a linked Telegram chat (which reads the person's money and spends their AI)
and admin step-ups all keep working unless they go too. Every path that ends
other sessions (password change or reset, "sign out everywhere", an account
switched off or banned, an account taken back through Google) calls this.
"""
from django.utils import timezone


def sign_out(user, keep_family=None):
    """End every session but ``keep_family``'s. Returns how many refresh tokens were revoked."""
    from adminpanel.models import SudoGrant
    from telegrambot.models import TelegramLink, TelegramLinkCode

    from .models import RefreshToken

    now = timezone.now()
    stale = RefreshToken.objects.filter(user=user, is_revoked=False)
    grants = SudoGrant.objects.filter(user=user)
    if keep_family:
        stale = stale.exclude(family_id=keep_family)
        grants = grants.exclude(family_id=str(keep_family))
    revoked = stale.update(is_revoked=True)
    grants.delete()
    TelegramLink.objects.filter(user=user).delete()
    TelegramLinkCode.objects.filter(user=user, used_at=None).update(used_at=now)
    user.tokens_valid_after = now
    user.save(update_fields=["tokens_valid_after"])
    return revoked
