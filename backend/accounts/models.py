import uuid

import uuid6

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


def avatar_upload_to(instance, filename):
    """Per-user folder, random basename so a replaced avatar can't be cached."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "png").lower()[:8]
    return f"avatars/{instance.pk}/{uuid.uuid4().hex}.{ext}"


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user with email as the unique identifier (no username column)."""

    class StaffRole(models.TextChoices):
        # What a team member may do in the admin panel (adminpanel.permissions).
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        SUPPORT = "support", "Support"
        CONTENT = "content", "Content editor"
        ANALYST = "analyst", "Analyst"

    class Theme(models.TextChoices):
        SYSTEM = "system", "Follow the system"
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"

    # UUIDv7 is time-ordered: much better B-tree index locality than random v4,
    # while still being non-sequential/non-enumerable.
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    # FileField rather than ImageField: ImageField needs Pillow purely to verify
    # the upload, and the view already sniffs the magic bytes itself.
    avatar = models.FileField(upload_to=avatar_upload_to, blank=True, null=True)

    # Appearance preferences live on the account so they follow the user between
    # devices; the client still caches them locally to avoid a flash on boot.
    theme = models.CharField(max_length=8, choices=Theme.choices, default=Theme.SYSTEM)
    brand_color = models.CharField(max_length=9, blank=True)  # "#RRGGBB"

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    # Sign-up consent: when the Terms and Privacy Policy were accepted, and that
    # the person said they are 16+ or have a parent's or guardian's permission.
    # Only the yes is kept, never a birth date.
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    age_confirmed = models.BooleanField(default=False)

    # Admin panel access. Empty = a regular learner. Superusers count as owners.
    staff_role = models.CharField(max_length=16, choices=StaffRole.choices, blank=True, default="")
    # Time-based one-time passwords for staff (RFC 6238). The secret is stored
    # encrypted (accounts.totp); it is only usable once confirmed with a code.
    totp_secret = models.CharField(max_length=256, blank=True, default="")
    totp_enabled = models.BooleanField(default=False)
    # Access tokens issued before this moment are refused, so "sign out
    # everywhere" and a ban take effect at once, not when tokens expire.
    tokens_valid_after = models.DateTimeField(null=True, blank=True)
    # Why an account was disabled, shown to staff (never to the user).
    disabled_reason = models.CharField(max_length=300, blank=True, default="")
    # When the address was confirmed by opening the link we mailed. Unconfirmed
    # accounts still work — they only see a reminder — but a password can never
    # be recovered without a working address, which is why we ask early.
    email_verified_at = models.DateTimeField(null=True, blank=True)
    # The Google account linked to this one ("sub" in Google's ID token: stable
    # for life, unlike the address). Set on the first Google sign-in, whether it
    # created the account or joined an existing one with the same email.
    google_sub = models.CharField(max_length=64, blank=True, default="")

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []  # email + password are already implied by createsuperuser

    class Meta:
        constraints = [
            # One Zinvest account per Google account.
            models.UniqueConstraint(
                fields=["google_sub"],
                condition=~models.Q(google_sub=""),
                name="unique_google_sub",
            )
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def admin_role(self):
        """The effective admin panel role ('' for learners)."""
        if not self.is_active:
            return ""
        if self.is_superuser:
            return self.StaffRole.OWNER
        return self.staff_role or ""


class RefreshToken(models.Model):
    """
    One row per issued refresh token. Rotation keeps the same ``family_id``;
    each row points at the token that replaced it (``replaced_by``) so a
    re-presented, just-rotated token can be distinguished from real reuse.
    """

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_tokens")

    # SHA-256 hex digest (64 chars). We store the HASH, never the raw token.
    token_hash = models.CharField(max_length=64, unique=True)

    # One device session == one family. Rotation preserves family_id. UUIDv7 so
    # families are time-ordered (index locality); it is not a secret.
    family_id = models.UUIDField(default=uuid6.uuid7)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_name = models.CharField(max_length=255, blank=True)      # parsed from User-Agent
    unique_device_id = models.CharField(max_length=255, blank=True)  # client-supplied, non-secret

    # Rotation bookkeeping (grace-window theft detection).
    is_revoked = models.BooleanField(default=False)
    replaced_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replaces"
    )
    rotated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["family_id"]),
            models.Index(fields=["family_id", "is_revoked"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} · fam={self.family_id} · revoked={self.is_revoked}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_active(self):
        return not self.is_revoked and not self.is_expired

    def revoke(self):
        if not self.is_revoked:
            self.is_revoked = True
            self.save(update_fields=["is_revoked"])

    @classmethod
    def revoke_family(cls, family_id):
        """Revoke every live token in a family in a single atomic UPDATE."""
        return cls.objects.filter(family_id=family_id, is_revoked=False).update(is_revoked=True)


class SecurityEvent(models.Model):
    """
    Append-only record of security-relevant events (failed and blocked logins,
    refresh-token reuse, password and email changes, admin step-ups...). Kept
    in the database so staff can review them in the admin panel.
    """

    class Kind(models.TextChoices):
        LOGIN_FAILED = "login_failed", "Failed sign-in"
        LOGIN_LOCKED = "login_locked", "Sign-in blocked (too many attempts)"
        LOGIN_DISABLED = "login_disabled", "Sign-in to a disabled account"
        TOKEN_REUSE = "token_reuse", "Refresh token reuse (possible theft)"
        PASSWORD_CHANGED = "password_changed", "Password changed"
        PASSWORD_CHECK_FAILED = "password_check_failed", "Wrong current password"
        PASSWORD_RESET_CREATED = "password_reset_created", "Password reset link created"
        PASSWORD_RESET_USED = "password_reset_used", "Password reset link used"
        EMAIL_VERIFIED = "email_verified", "Email confirmed"
        EMAIL_CHANGED = "email_changed", "Email changed"
        ACCOUNT_DELETED = "account_deleted", "Account deleted"
        DATA_EXPORTED = "data_exported", "Data downloaded"
        SESSIONS_REVOKED = "sessions_revoked", "Sessions revoked"
        REGISTER_THROTTLED = "register_throttled", "Sign-up throttled"
        ADMIN_SUDO = "admin_sudo", "Admin step-up confirmed"
        ADMIN_SUDO_FAILED = "admin_sudo_failed", "Admin step-up failed"
        ADMIN_DENIED = "admin_denied", "Admin access denied"
        TOTP_ENABLED = "totp_enabled", "Two-factor enabled"
        TOTP_DISABLED = "totp_disabled", "Two-factor disabled"
        CODE_FAILED = "code_failed", "Wrong emailed code"
        GOOGLE_SIGNIN = "google_signin", "Signed in with Google"
        AUTO_BAN = "auto_ban", "Banned automatically (limit abused)"
        BAN_LIFTED = "ban_lifted", "Ban lifted"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    kind = models.CharField(max_length=32, choices=Kind.choices)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="security_events")
    email = models.CharField(max_length=254, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["kind", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.kind} · {self.email or self.user_id} · {self.created_at:%Y-%m-%d %H:%M}"


class PasswordResetToken(models.Model):
    """A single-use link staff create for a learner who lost their password."""

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_resets")
    token_hash = models.CharField(max_length=64, unique=True)  # SHA-256 of the raw token
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_usable(self):
        return self.used_at is None and timezone.now() < self.expires_at


class EmailVerification(models.Model):
    """
    A single-use link that confirms an address belongs to whoever opened it.

    The address is stored alongside the user: changing the email later leaves
    older links pointing at an address the account no longer has, and they are
    refused rather than silently confirming the new one.
    """

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_verifications")
    email = models.EmailField()
    token_hash = models.CharField(max_length=64, unique=True)  # SHA-256 of the raw token
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "-created_at"])]

    @property
    def is_usable(self):
        return self.used_at is None and timezone.now() < self.expires_at

    def __str__(self):
        return f"verify {self.email} · {self.created_at:%Y-%m-%d %H:%M}"


class LoginCode(models.Model):
    """
    A six-digit code mailed to finish a sign-in or a sign-up (accounts.codes).

    A password alone no longer opens a session: the code from the letter does.
    For a sign-up nothing is created until the code is right; the details wait
    in ``payload`` with the password already hashed. The code itself is kept
    only as an HMAC, and a row dies after a few wrong tries.
    """

    class Purpose(models.TextChoices):
        LOGIN = "login", "Sign-in"
        REGISTER = "register", "Sign-up"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    purpose = models.CharField(max_length=16, choices=Purpose.choices)
    email = models.EmailField()
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="login_codes")
    code_hash = models.CharField(max_length=64)
    # Sign-up details until the code is confirmed (the password as a hash), or
    # {"decoy": true} for an address that already has an account.
    payload = models.JSONField(default=dict, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    sends = models.PositiveSmallIntegerField(default=1)
    sent_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["email", "-created_at"])]

    @property
    def is_usable(self):
        return self.used_at is None and timezone.now() < self.expires_at

    def __str__(self):
        return f"{self.purpose} code {self.email} · {self.created_at:%Y-%m-%d %H:%M}"


class RateBucket(models.Model):
    """
    One rate-limit counter for accounts.security.hit when the counters live in
    the database (Vercel: no shared memory between instances). `hits` grows by
    one atomic upsert per event, so concurrent requests cannot lose a count;
    the window restarts once `resets_at` (epoch seconds) has passed.
    """
    name = models.CharField(max_length=200, primary_key=True)
    hits = models.PositiveIntegerField(default=0)
    resets_at = models.BigIntegerField(db_index=True)

    def __str__(self):
        return f"{self.name} · {self.hits}"


class Ban(models.Model):
    """
    A block set by accounts.bans when a client kept hammering a rate limit.
    An account ban is permanent (and also switches the account off); an
    address ban lasts longer with every strike. Staff lift either from the
    admin panel, which keeps the row for the record.
    """

    class Kind(models.TextChoices):
        USER = "user", "Account"
        IP = "ip", "IP address"

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    kind = models.CharField(max_length=8, choices=Kind.choices)
    value = models.CharField(max_length=64)  # the account id or the address
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="bans")
    reason = models.CharField(max_length=64)  # the limit that was abused, e.g. "api-write"
    hits = models.PositiveIntegerField(default=0)  # requests counted in that window
    limit = models.PositiveIntegerField(default=0)
    strike = models.PositiveSmallIntegerField(default=1)
    expires_at = models.DateTimeField(null=True, blank=True)  # None: forever
    created_at = models.DateTimeField(auto_now_add=True)
    lifted_at = models.DateTimeField(null=True, blank=True)
    lifted_by = models.CharField(max_length=254, blank=True)

    class Meta:
        indexes = [models.Index(fields=["kind", "value"]), models.Index(fields=["-created_at"])]

    @property
    def is_active(self):
        return self.lifted_at is None and (self.expires_at is None or self.expires_at > timezone.now())

    def __str__(self):
        return f"{self.kind} ban {self.value} · {self.reason}"
