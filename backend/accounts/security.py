"""
Shared security helpers: the client's IP, rate limits and the security log.

Client IP
    Proxy headers (X-Real-IP, X-Forwarded-For) are only believed when the TCP
    peer is one of settings.TRUSTED_PROXIES. Anyone can send those headers, so
    trusting them blindly lets an attacker pick a fresh "IP" for every request
    and walk around every per-IP limit.

Rate limits
    ``hit(scope, key, limit, window)`` counts events in a fixed window and says
    whether the caller is still under the limit. The counters live in Redis or
    the cache, or — with RATE_LIMIT_STORE="db", as on Vercel where instances
    share nothing but the database — in the RateBucket table, incremented by a
    single atomic upsert so parallel requests cannot lose a count. A client
    that keeps going far past a limit is banned (accounts.bans).

Security log
    ``record(kind, ...)`` writes a SecurityEvent row and a log line. It never
    raises: a failure to log must not break sign-in.
"""
import ipaddress
import logging
import random
import time

from django.conf import settings
from django.core.cache import cache

log = logging.getLogger("accounts.security")


def _trusted_networks():
    nets = []
    for item in settings.TRUSTED_PROXIES:
        try:
            nets.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            log.warning("ignoring bad TRUSTED_PROXIES entry %r", item)
    return nets


_TRUSTED = None


def _is_trusted(addr):
    global _TRUSTED
    if _TRUSTED is None:
        _TRUSTED = _trusted_networks()
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return any(ip in net for net in _TRUSTED)


def _valid_ip(value):
    try:
        return str(ipaddress.ip_address(value.strip()))
    except (ValueError, AttributeError):
        return None


def client_ip(request):
    """The client's address, taking proxy headers only from trusted proxies."""
    peer = request.META.get("REMOTE_ADDR") or ""
    if peer and _is_trusted(peer):
        real = _valid_ip(request.META.get("HTTP_X_REAL_IP", ""))
        if real:
            return real
        # X-Forwarded-For: walk from the right, skipping our own proxies; the
        # first untrusted hop is the client. Left-most entries are client-made.
        chain = [part.strip() for part in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if part.strip()]
        for hop in reversed(chain):
            ip = _valid_ip(hop)
            if ip and not _is_trusted(ip):
                return ip
    return _valid_ip(peer) or peer or None


# ---------------------------------------------------------------------------
# Rate limits
# ---------------------------------------------------------------------------
def _bucket_table():
    from .models import RateBucket  # local: models import this module indirectly

    return RateBucket._meta.db_table


def _db_hit(name, window_seconds):
    """One atomic increment in RateBucket; returns the count in the current window."""
    from django.db import connection

    now = int(time.time())
    table = connection.ops.quote_name(_bucket_table())
    with connection.cursor() as cur:
        cur.execute(
            f"INSERT INTO {table} (name, hits, resets_at) VALUES (%s, 1, %s) "
            f"ON CONFLICT (name) DO UPDATE SET "
            f"hits = CASE WHEN {table}.resets_at > %s THEN {table}.hits + 1 ELSE 1 END, "
            f"resets_at = CASE WHEN {table}.resets_at > %s THEN {table}.resets_at ELSE excluded.resets_at END "
            f"RETURNING hits",
            [name, now + window_seconds, now, now],
        )
        count = cur.fetchone()[0]
        if random.random() < 0.01:  # now and then, drop windows long over
            cur.execute(f"DELETE FROM {table} WHERE resets_at < %s", [now - 3600])
    return count


def hit(scope, key, limit, window_seconds):
    """
    Count one event for (scope, key). Returns True while the caller is within
    ``limit`` events per ``window_seconds``, False once over it.
    """
    if settings.RATE_LIMIT_STORE == "db":
        count = _db_hit(f"{scope}:{key}"[:200], window_seconds)
    elif cache.add(f"rl:{scope}:{key}", 1, timeout=window_seconds):
        count = 1
    else:
        try:
            count = cache.incr(f"rl:{scope}:{key}")
        except ValueError:  # expired between add() and incr()
            cache.set(f"rl:{scope}:{key}", 1, timeout=window_seconds)
            count = 1
    if count > limit:
        from . import bans  # a client that keeps going far past the limit is banned

        bans.over_limit(scope, key, count, limit)
    return count <= limit


def over(scope, key, limit):
    """True once (scope, key) has used up ``limit`` events in its current window."""
    if settings.RATE_LIMIT_STORE == "db":
        from .models import RateBucket

        row = RateBucket.objects.filter(name=f"{scope}:{key}"[:200], resets_at__gt=int(time.time())).first()
        return bool(row) and row.hits >= limit
    return (cache.get(f"rl:{scope}:{key}") or 0) >= limit


def reset(scope, key):
    if settings.RATE_LIMIT_STORE == "db":
        from .models import RateBucket

        RateBucket.objects.filter(name=f"{scope}:{key}"[:200]).delete()
        return
    cache.delete(f"rl:{scope}:{key}")


# ---------------------------------------------------------------------------
# Security log
# ---------------------------------------------------------------------------
def mask(email):
    """a***@gmail.com, for logs: enough to tell addresses apart, not to read them off."""
    if not email or "@" not in email:
        return email or ""
    name, _, domain = email.partition("@")
    return f"{name[:1]}{'*' * max(2, min(len(name) - 1, 6))}@{domain}"


def record(kind, request=None, *, user=None, email="", ip=None, **details):
    from .models import SecurityEvent  # local: models import this module's helpers indirectly

    if ip is None and request is not None:
        ip = client_ip(request)
    if user is not None and not email:
        email = getattr(user, "email", "") or ""
    # The log (Vercel's, kept elsewhere) gets a masked address; the full one stays in the database.
    log.info("security_event kind=%s user=%s email=%s ip=%s %s", kind, getattr(user, "pk", None), mask(email), ip, details or "")
    try:
        SecurityEvent.objects.create(kind=kind, user=user, email=email[:254], ip_address=ip, details=details)
    except Exception:  # never let bookkeeping break the request
        log.exception("could not store security event %s", kind)
