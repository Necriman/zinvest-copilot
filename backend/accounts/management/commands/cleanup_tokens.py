"""
Purge dead refresh-token rows so the table does not grow unbounded.

Revoked rows are kept for a short grace window first, so the theft trap can
still fire on a replayed just-rotated token. Run from cron / a systemd timer.

It also keeps personal data no longer than it is useful: emailed codes after a
day (an abandoned sign-up's code holds its name and password hash), finished
reset and confirmation links after a week, the security log after 180 days and
bans that ended after a year.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Ban, EmailVerification, LoginCode, PasswordResetToken, RateBucket, RefreshToken, SecurityEvent


class Command(BaseCommand):
    help = "Delete expired tokens and revoked tokens older than a grace window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--revoked-grace-days",
            type=int,
            default=7,
            help="Keep revoked rows this many days before deleting (default: 7).",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        grace = now - timedelta(days=options["revoked_grace_days"])

        expired, _ = RefreshToken.objects.filter(expires_at__lt=now).delete()
        old_revoked, _ = RefreshToken.objects.filter(
            is_revoked=True, created_at__lt=grace
        ).delete()

        # Rate-limit windows that ended over an hour ago.
        stale, _ = RateBucket.objects.filter(resets_at__lt=int(now.timestamp()) - 3600).delete()

        codes, _ = LoginCode.objects.filter(created_at__lt=now - timedelta(days=1)).delete()
        week = now - timedelta(days=7)
        links = 0
        for model in (PasswordResetToken, EmailVerification):
            links += model.objects.filter(created_at__lt=week, expires_at__lt=now).delete()[0]
            links += model.objects.filter(used_at__lt=week).delete()[0]
        events, _ = SecurityEvent.objects.filter(created_at__lt=now - timedelta(days=180)).delete()
        year = now - timedelta(days=365)
        bans, _ = Ban.objects.filter(created_at__lt=year).exclude(expires_at=None, lifted_at=None).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {expired} expired and {old_revoked} old-revoked tokens, {stale} old rate-limit windows, "
                f"{codes} emailed codes, {links} old links, {events} old security events, {bans} old bans."
            )
        )
