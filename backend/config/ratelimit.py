"""
Request rate limits for the whole API.

Three layers keep a flood from taking the site down:

1. Vercel's edge: automatic DDoS mitigation, plus a firewall rule that caps
   requests to /api per IP before they ever reach a function (configured with
   `vercel firewall`, see deploy/vercel/README.md).
2. This middleware: every /api request is counted and a client over its limit
   gets 429 with Retry-After, before any view, database query or AI call runs.
3. The precise limits inside the views (sign-in, sign-up, codes, password
   reset, AI token quota), which stay as they are.

Here a client is the signed-in user when the request carries a valid access
token (checked by signature only, no database), else its IP. Counting by user
matters: mobile carriers put thousands of people behind one IP, so an IP-only
limit would lock out a school or a whole district.

Counters:
- every request first counts against a per-IP ceiling in this process's
  memory: free, and it bounds what one instance takes;
- then against its own kind (read, write, upload, AI) in the shared store
  (accounts.security.hit): Redis, or on Vercel the RateBucket table, where a
  single atomic upsert per request keeps the count exact across instances.

Limits are per minute and can be tuned with RATE_LIMIT_* settings. A client
that keeps going until twice its limit is banned (accounts.bans): an account
for good, an address for a while; a banned address gets 429 "ip_banned" here
on every guest request until its ban runs out.
"""
import logging
import threading
import time

from django.conf import settings
from django.http import JsonResponse

from accounts import bans, security
from accounts.jwt_utils import InvalidAccessToken, decode_access_token

log = logging.getLogger("ratelimit")

# Callers that prove themselves with a secret, and send bursts by design.
EXEMPT = ("/api/telegram/", "/api/cron/")
# Calls that run the AI or build big answers.
HEAVY = (
    "/api/ai/", "/api/startup/roadmap", "/api/startup/onboarding", "/api/startup/network/recommendations", "/api/auth/me/export",
    "/api/copilot/entries", "/api/copilot/analysis", "/api/copilot/runway", "/api/copilot/loan", "/api/copilot/plan",
    "/api/learning/study-plan/regenerate", "/api/learning/onboarding",
)
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# A person signed in before their network was banned keeps their session.
SESSION_PATHS = ("/api/auth/refresh", "/api/auth/logout")
WINDOW = 60


def limits():
    return {
        "read": settings.RATE_LIMIT_READ,
        "write": settings.RATE_LIMIT_WRITE,
        "upload": settings.RATE_LIMIT_UPLOAD,
        "heavy": settings.RATE_LIMIT_HEAVY,
        "ip": settings.RATE_LIMIT_IP,
        # Guests write by IP (sign-in, sign-up, session refresh), and a class
        # behind one address signs in at once; those views keep their own
        # stricter per-address limits.
        "guest_write": settings.RATE_LIMIT_GUEST_WRITE,
    }


class LocalCounter:
    """Fixed one-minute windows in this process's memory, thread-safe and bounded."""

    MAX_KEYS = 50000

    def __init__(self):
        self._lock = threading.Lock()
        self._counts = {}
        self._window = 0

    def hit(self, key, limit):
        window = int(time.time() // WINDOW)
        with self._lock:
            if window != self._window or len(self._counts) > self.MAX_KEYS:
                self._counts.clear()
                self._window = window
            count = self._counts.get(key, 0) + 1
            self._counts[key] = count
        return count <= limit, count

    def clear(self):
        with self._lock:
            self._counts.clear()


local = LocalCounter()


def _identity(request):
    """'u:<id>' for a valid access token, else 'ip:<address>'."""
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if header.startswith("Bearer "):
        try:
            return "u:" + decode_access_token(header[7:].strip())["sub"]
        except (InvalidAccessToken, KeyError):
            pass
    return f"ip:{security.client_ip(request) or 'unknown'}"


def _kind(request):
    path = request.path
    if request.method in WRITE_METHODS and request.content_type == "multipart/form-data":
        return "upload"
    if path.startswith(HEAVY) and request.method in WRITE_METHODS:
        return "heavy"
    if request.method in WRITE_METHODS:
        return "write"
    return "read"


def _too_many():
    seconds = WINDOW - int(time.time()) % WINDOW
    response = JsonResponse(
        {"detail": "Too many requests. Please slow down and try again in a minute.", "code": "rate_limited", "retry_after": seconds},
        status=429,
    )
    response["Retry-After"] = str(seconds)
    return response


def _keeps_session(request):
    """Refreshing or ending a session someone already has: allowed from a banned address."""
    return request.path in SESSION_PATHS and bool(request.COOKIES.get("refresh_token"))


def _banned(seconds):
    response = JsonResponse(
        {"detail": "Too many requests came from your network, so it is blocked for a while. Please try again later.",
         "code": "ip_banned", "retry_after": seconds},
        status=429,
    )
    response["Retry-After"] = str(seconds)
    return response


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_api = request.path.startswith("/api/")
        response = self._check(request, is_api) or self.get_response(request)
        if is_api and not response.has_header("Cache-Control"):
            response["Cache-Control"] = "no-store"  # answers are per person: no shared cache keeps them
        return response

    def _check(self, request, is_api):
        """None to let the request through, else the refusal."""
        if not settings.RATE_LIMITS_ENABLED or request.method == "OPTIONS":
            return None
        if request.path.startswith(settings.MEDIA_URL):
            # Uploaded pictures and voice clips: each one is a function call and a
            # database read, so they are counted too (per address: <img> sends no
            # token). Generous, and never a reason to ban: a class loads a feed at once.
            ip = security.client_ip(request) or "unknown"
            if not security.hit("media", ip, settings.RATE_LIMIT_MEDIA, WINDOW):
                return self._block("media", f"ip:{ip}", settings.RATE_LIMIT_MEDIA)
            return None
        if not is_api or request.path.startswith(EXEMPT):
            return None
        caps = limits()
        ip = security.client_ip(request) or "unknown"
        who = _identity(request)
        if who.startswith("ip:") and not _keeps_session(request):
            left = bans.ip_banned_for(ip)
            if left:
                return _banned(left)
        ok, count = local.hit(f"ip:{ip}", caps["ip"])
        if not ok:
            bans.over_limit("api-ip", f"ip:{ip}", count, caps["ip"])
            return self._block("ip", f"ip:{ip}", caps["ip"])
        kind = _kind(request)
        cap = caps["guest_write"] if kind == "write" and who.startswith("ip:") else caps[kind]
        if not security.hit(f"api-{kind}", who, cap, WINDOW):
            return self._block(kind, who, cap)
        return None

    @staticmethod
    def _block(kind, who, limit):
        # Log the first refusal per client and window only, so a flood does not flood the logs.
        if local.hit(f"logged:{kind}:{who}", 1)[0]:
            log.warning("rate_limited kind=%s who=%s limit=%s/min", kind, who, limit)
        return _too_many()
