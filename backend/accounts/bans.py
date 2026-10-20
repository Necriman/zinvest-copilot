"""
Automatic bans for clients that abuse a rate limit.

A limit first answers a polite "429, slow down". A person stops there; a
script does not. When the same client keeps going until it has sent
AUTO_BAN_FACTOR times the limit within one window, it is banned on the spot:

- a signed-in account: forever. The account is switched off, every session
  revoked, and staff see why under Admin → Security → Bans;
- an address (guests: sign-up, codes, password reset, the API without a
  token): for 1 hour, then 24 hours, then 30 days on later strikes within
  90 days. Never forever: a mobile carrier puts thousands of people behind
  one address. An address ban only stops guests; people signed in from the
  same network keep working.

Only the client that sends the requests is banned. Limits counted per target
(an email someone asks a reset link for, a Telegram chat) never ban: anyone
could otherwise get someone else's account banned by attacking it.

Staff accounts and loopback addresses are never banned automatically; the
event is logged instead.
"""
import ipaddress
import logging
import threading
import time
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

log = logging.getLogger("accounts.security")

# Which limits ban, and who their key names: the signed-in "user", the
# client's "ip", or "who" — the API counters' "u:<id>" / "ip:<address>".
ACTORS = {
    "api-ip": "who", "api-read": "who", "api-write": "who", "api-upload": "who", "api-heavy": "who",
    "register": "ip", "login-locked": "ip", "code-verify": "ip", "code-resend": "ip", "pwreset": "ip", "verify": "ip", "forgot-ip": "ip",
    "export": "user", "report": "user", "tg-code": "user",
    "connect-min": "user", "message-min": "user", "post-min": "user",
}
IP_STEPS = (timedelta(hours=1), timedelta(hours=24), timedelta(days=30))
STRIKE_MEMORY = timedelta(days=90)


def threshold(limit):
    return max(limit * settings.AUTO_BAN_FACTOR, limit + 1)


def over_limit(scope, key, count, limit):
    """Called by security.hit for every refused event; bans exactly once per window."""
    if not settings.AUTO_BAN_ENABLED or count != threshold(limit) or scope not in ACTORS:
        return None
    try:
        return trip(scope, str(key), count, limit)
    except Exception:  # a failed ban must never turn into a failed request
        log.exception("auto-ban failed scope=%s key=%s", scope, key)
        return None


def trip(scope, key, hits, limit):
    actor = ACTORS[scope]
    if actor == "who":
        prefix, _, key = key.partition(":")
        actor = "user" if prefix == "u" else "ip"
    if actor == "user":
        return ban_user(key, scope, hits, limit)
    return ban_ip(key, scope, hits, limit)


def ban_user(user_id, reason, hits, limit):
    from . import security, sessions
    from .models import Ban, SecurityEvent, User

    try:
        user = User.objects.filter(pk=user_id).first()
    except Exception:  # not a valid id
        return None
    if user is None or not user.is_active:
        return None
    if user.is_superuser or user.is_staff or user.staff_role:
        security.record(SecurityEvent.Kind.AUTO_BAN, user=user, target="account", reason=reason, hits=hits, limit=limit,
                        banned=False, note="staff are never banned automatically")
        return None
    with transaction.atomic():
        ban = Ban.objects.create(kind=Ban.Kind.USER, value=str(user.pk), user=user, reason=reason, hits=hits, limit=limit)
        user.is_active = False
        user.disabled_reason = f"Banned automatically: {hits} requests past the '{reason}' limit of {limit} in one window."
        user.save(update_fields=["is_active", "disabled_reason"])
        sessions.sign_out(user)  # sessions, access tokens, the Telegram chat
    security.record(SecurityEvent.Kind.AUTO_BAN, user=user, target="account", reason=reason, hits=hits, limit=limit, until="forever")
    return ban


def ban_ip(address, reason, hits, limit):
    from . import security
    from .models import Ban, SecurityEvent

    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return None
    address = str(ip)
    if ip.is_loopback or address in settings.AUTO_BAN_SAFE_IPS:
        security.record(SecurityEvent.Kind.AUTO_BAN, ip=address, target="ip", reason=reason, hits=hits, limit=limit,
                        banned=False, note="this address is never banned automatically")
        return None
    now = timezone.now()
    with transaction.atomic():
        current = Ban.objects.select_for_update().filter(kind=Ban.Kind.IP, value=address, lifted_at=None).filter(
            Q(expires_at=None) | Q(expires_at__gt=now)).first()
        if current:
            return current
        # Strikes are the earlier bans that ran out; a ban staff lifted was a mistake and does not count.
        strike = Ban.objects.filter(kind=Ban.Kind.IP, value=address, lifted_at=None, created_at__gte=now - STRIKE_MEMORY).count() + 1
        until = now + IP_STEPS[min(strike, len(IP_STEPS)) - 1]
        ban = Ban.objects.create(kind=Ban.Kind.IP, value=address, reason=reason, hits=hits, limit=limit, strike=strike, expires_at=until)
    _cache.add(address, until.timestamp())
    security.record(SecurityEvent.Kind.AUTO_BAN, ip=address, target="ip", reason=reason, hits=hits, limit=limit,
                    strike=strike, until=until.isoformat(timespec="minutes"))
    return ban


def lift(ban, by):
    """Undo a ban (staff). An account ban also switches the account back on."""
    from . import security
    from .models import SecurityEvent, User

    with transaction.atomic():
        ban.lifted_at = timezone.now()
        ban.lifted_by = by[:254]
        ban.save(update_fields=["lifted_at", "lifted_by"])
        if ban.kind == ban.Kind.USER and ban.user_id:
            User.objects.filter(pk=ban.user_id, is_active=False).update(is_active=True, disabled_reason="")
    if ban.kind == ban.Kind.IP:
        _cache.remove(ban.value)
    security.record(SecurityEvent.Kind.BAN_LIFTED, user=ban.user, ip=ban.value if ban.kind == ban.Kind.IP else None,
                    target=ban.kind, reason=ban.reason, by=by)


def lift_for_user(user, by):
    """Staff switched an account back on by hand: close its open bans too."""
    from .models import Ban

    Ban.objects.filter(kind=Ban.Kind.USER, user=user, lifted_at=None).update(lifted_at=timezone.now(), lifted_by=by[:254])


# ---------------------------------------------------------------------------
# Banned addresses, checked on every API request
# ---------------------------------------------------------------------------
class _IpCache:
    """Active address bans, reloaded from the database every TTL seconds per instance."""

    TTL = 30

    def __init__(self):
        self._lock = threading.Lock()
        self._until = {}
        self._loaded = 0.0

    def _reload(self, now):
        from .models import Ban

        rows = Ban.objects.filter(kind=Ban.Kind.IP, lifted_at=None).filter(
            Q(expires_at=None) | Q(expires_at__gt=timezone.now())).values_list("value", "expires_at")
        self._until = {value: (until.timestamp() if until else float("inf")) for value, until in rows}
        self._loaded = now

    def until(self, address):
        now = time.time()
        with self._lock:
            if now - self._loaded > self.TTL:
                self._reload(now)
            until = self._until.get(address)
        return until if until and until > now else None

    def add(self, address, until):
        with self._lock:
            self._until[address] = until

    def remove(self, address):
        with self._lock:
            self._until.pop(address, None)

    def clear(self):
        with self._lock:
            self._until = {}
            self._loaded = 0.0


_cache = _IpCache()


def ip_banned_for(address):
    """Seconds left on this address's ban, or None."""
    if not address:
        return None
    try:
        until = _cache.until(address)
    except Exception:  # the ban list must never take the API down
        log.exception("could not read address bans")
        return None
    if until is None:
        return None
    return max(1, int(min(until, time.time() + 365 * 24 * 3600) - time.time()))


def forget():
    """Tests: drop this process's copy of the ban list."""
    _cache.clear()
