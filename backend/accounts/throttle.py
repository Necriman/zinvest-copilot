"""
Brute-force throttling for the login endpoint (security review #3).

Three independent counters are enforced:
  * per (ip, email)  -> stops password-guessing a single account
  * per ip           -> stops spraying many accounts from one host
  * per email        -> stops guessing one account from many hosts (a botnet or
                        spoofed addresses). Higher limit, so a stranger cannot
                        lock someone out with a handful of attempts.

A successful sign-in only clears its own (ip, email) counter. Clearing the IP
counter as well would let an attacker reset it by signing into their own
account between guesses at someone else's.

The counters live wherever accounts.security keeps its rate limits: Redis, or
on Vercel the RateBucket table, where every count is one atomic upsert, so
parallel guesses cannot lose counts and slip past the lockout together.
"""
import logging

from django.conf import settings

from . import security

log = logging.getLogger("accounts.security")


def _window():
    return int(settings.LOGIN_ATTEMPT_WINDOW.total_seconds())


def is_locked(ip, email):
    """Return True if the account, the IP or the address has used up its attempts."""
    email = email.lower()
    return (
        security.over("login-fail", f"{ip}:{email}", settings.LOGIN_MAX_ATTEMPTS)
        or security.over("login-ip", ip, settings.IP_MAX_ATTEMPTS)
        or security.over("login-email", email, settings.EMAIL_MAX_ATTEMPTS)
    )


def record_failure(ip, email):
    """Count one failed attempt on all three counters. Returns True once this locks the account."""
    email = email.lower()
    window = _window()
    account_ok = security.hit("login-fail", f"{ip}:{email}", settings.LOGIN_MAX_ATTEMPTS - 1, window)
    security.hit("login-ip", ip, settings.IP_MAX_ATTEMPTS, window)
    email_ok = security.hit("login-email", email, settings.EMAIL_MAX_ATTEMPTS - 1, window)
    if not account_ok:
        log.warning("login_lockout ip=%s email=%s", ip, security.mask(email))
    return not account_ok or not email_ok


def clear(ip, email):
    """Reset this device's counter for the account after a successful login."""
    security.reset("login-fail", f"{ip}:{email.lower()}")
