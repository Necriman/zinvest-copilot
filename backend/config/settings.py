"""
Django settings for the secure hybrid-JWT auth boilerplate.

Everything security-relevant is driven by environment variables (see .env.example).
Reads a .env file in development via python-dotenv if present.
"""
import os
import sys
import warnings
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Load .env (development convenience). In production, real env vars win.
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    # Look for a .env at the repo root (../.env) and in backend/ (./.env).
    load_dotenv(BASE_DIR.parent / ".env")
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


def env_bool(name, default=False):
    return os.environ.get(name, "1" if default else "0").lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = env_bool("DEBUG", default=False)  # on only where .env says DEBUG=1 (local)

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        # Deterministic, clearly-insecure key so `runserver` works out of the box.
        SECRET_KEY = "django-insecure-dev-only-change-me-in-production-0123456789"
        warnings.warn("SECRET_KEY not set; using an insecure development key.", stacklevel=1)
    else:
        raise RuntimeError("SECRET_KEY environment variable is required when DEBUG=False.")

# Dedicated JWT signing key — NOT reused from SECRET_KEY (security review #7).
# Falls back to SECRET_KEY only in DEBUG, with a warning.
JWT_SIGNING_KEY = os.environ.get("JWT_SIGNING_KEY")
if not JWT_SIGNING_KEY:
    if DEBUG:
        JWT_SIGNING_KEY = SECRET_KEY
        warnings.warn(
            "JWT_SIGNING_KEY not set; falling back to SECRET_KEY (dev only). "
            "Set a dedicated JWT_SIGNING_KEY in production.",
            stacklevel=1,
        )
    else:
        raise RuntimeError("JWT_SIGNING_KEY environment variable is required when DEBUG=False.")

# Production keys must be real secrets: long, and different from each other.
# (.env.example used to ship "123"; a key like that makes every token forgeable.)
if not DEBUG:
    for _name, _value in (("SECRET_KEY", SECRET_KEY), ("JWT_SIGNING_KEY", JWT_SIGNING_KEY)):
        if len(_value) < 32 or _value.lower().startswith(("change-me", "django-insecure")):
            raise RuntimeError(f"{_name} is too weak: use at least 32 random characters (see .env.example).")
    if SECRET_KEY == JWT_SIGNING_KEY:
        raise RuntimeError("JWT_SIGNING_KEY must differ from SECRET_KEY.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

# Proxies whose X-Real-IP / X-Forwarded-For headers are believed (IPs or CIDR
# ranges). Everyone else is identified by the TCP peer address, so a client
# cannot spoof its IP to dodge sign-in limits. Defaults: localhost and private
# networks, where Nginx and the Docker network live.
TRUSTED_PROXIES = env_list("TRUSTED_PROXIES", "127.0.0.1/32,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16")

# Origins allowed to send unsafe (POST) requests. Required for the Django admin
# and any cross-subdomain calls once the app is served under custom hostnames
# behind Nginx (e.g. http://zinvest.loc, http://api.zinvest.loc). Override in
# prod with the real https origins.
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "https://zinvest.loc,https://api.zinvest.loc,https://dashboard.zinvest.loc,"
    "http://zinvest.loc:5173,http://api.zinvest.loc:5173,http://dashboard.zinvest.loc:5173",
)

AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# Auth / token tuning (read by accounts.jwt_utils and accounts.views)
# ---------------------------------------------------------------------------
ACCESS_TOKEN_TTL = timedelta(minutes=int(os.environ.get("ACCESS_TOKEN_TTL_MIN", "15")))
REFRESH_TOKEN_TTL = timedelta(days=int(os.environ.get("REFRESH_TOKEN_TTL_DAYS", "7")))
# Small window during which re-presenting the just-rotated refresh token is
# treated as a benign concurrent/retried refresh instead of token theft.
REFRESH_REUSE_GRACE = timedelta(seconds=int(os.environ.get("REFRESH_REUSE_GRACE_SEC", "15")))
# Logout may accept a just-expired access token, but only within a bounded
# window (security review #6) — never unlimited.
LOGOUT_EXP_LEEWAY = timedelta(minutes=int(os.environ.get("LOGOUT_EXP_LEEWAY_MIN", "5")))
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

# The refresh cookie is Secure (HTTPS-only) by default in production. Override to
# False ONLY for a local HTTP demo (e.g. the docker-compose path) — never in prod.
REFRESH_COOKIE_SECURE = env_bool("REFRESH_COOKIE_SECURE", default=not DEBUG)

# Login throttle / lockout (security review #3)
LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_ATTEMPT_WINDOW = timedelta(minutes=int(os.environ.get("LOGIN_ATTEMPT_WINDOW_MIN", "15")))
IP_MAX_ATTEMPTS = int(os.environ.get("IP_MAX_ATTEMPTS", "30"))
# Failed sign-ins to one account from anywhere before it pauses for the window.
EMAIL_MAX_ATTEMPTS = int(os.environ.get("EMAIL_MAX_ATTEMPTS", "20"))
# New accounts per IP per hour, and wrong "current password" answers per user
# per 15 minutes (password / email change, account deletion, admin step-up).
REGISTER_MAX_PER_IP_HOUR = int(os.environ.get("REGISTER_MAX_PER_IP_HOUR", "10"))
PASSWORD_CHECK_MAX = int(os.environ.get("PASSWORD_CHECK_MAX", "10"))

# ---------------------------------------------------------------------------
# Admin panel (adminpanel app, /api/admin/*) and Django's own admin
# ---------------------------------------------------------------------------
# Dangerous admin actions need a fresh confirmation (password + 2FA code),
# valid for this many minutes on the device that made it.
ADMIN_SUDO_MINUTES = int(os.environ.get("ADMIN_SUDO_MINUTES", "30"))
# Staff who can change anything must turn on two-factor sign-in.
ADMIN_REQUIRE_2FA = env_bool("ADMIN_REQUIRE_2FA", default=not DEBUG)
# Key for encrypting two-factor secrets at rest (defaults to one derived from SECRET_KEY).
TOTP_ENCRYPTION_KEY = os.environ.get("TOTP_ENCRYPTION_KEY", "")
# Django's built-in admin: move it off the well-known /admin/ path in production
# (it is for superusers only; the team uses the admin panel in the app).
DJANGO_ADMIN_PATH = os.environ.get("DJANGO_ADMIN_PATH", "admin/").strip("/") + "/"
# …and off entirely in production unless asked for: its sign-in is a password
# only, with none of the panel's two-factor step.
DJANGO_ADMIN_ENABLED = env_bool("DJANGO_ADMIN_ENABLED", default=DEBUG)
# Where learners open a password reset link that staff created.
APP_ORIGIN = os.environ.get("APP_ORIGIN", "http://127.0.0.1:5173").rstrip("/")

# If True, register returns 409 for an existing email (better UX, but enables
# user enumeration). Default False = enumeration-resistant uniform response.
AUTH_REVEAL_EMAIL_EXISTS = env_bool("AUTH_REVEAL_EMAIL_EXISTS", default=False)

# Sign-in and sign-up finish with a six-digit code mailed to the address
# (accounts.codes). Off only for tests that exercise the password step alone.
LOGIN_EMAIL_CODE = env_bool("LOGIN_EMAIL_CODE", default=True)
LOGIN_CODE_TTL_MINUTES = int(os.environ.get("LOGIN_CODE_TTL_MINUTES", "10"))
LOGIN_CODE_MAX_PER_EMAIL_HOUR = int(os.environ.get("LOGIN_CODE_MAX_PER_EMAIL_HOUR", "8"))

# API rate limits per minute (config/ratelimit.py): per signed-in user, or per
# IP for guests; RATE_LIMIT_IP caps everything from one IP on one instance.
# Off while the test suite runs (its tests turn them on where they test them).
# Where accounts.security.hit keeps its counters: "db" (RateBucket, atomic) on
# Vercel, where the cache is a database table and its incr is not atomic.
RATE_LIMIT_STORE = os.environ.get("RATE_LIMIT_STORE") or ("db" if os.environ.get("CACHE_BACKEND") == "db" and not os.environ.get("REDIS_URL") else "cache")
RATE_LIMITS_ENABLED = env_bool("RATE_LIMITS_ENABLED", default="test" not in sys.argv[1:2])
RATE_LIMIT_READ = int(os.environ.get("RATE_LIMIT_READ", "300"))
RATE_LIMIT_WRITE = int(os.environ.get("RATE_LIMIT_WRITE", "60"))
RATE_LIMIT_UPLOAD = int(os.environ.get("RATE_LIMIT_UPLOAD", "20"))
RATE_LIMIT_HEAVY = int(os.environ.get("RATE_LIMIT_HEAVY", "20"))
RATE_LIMIT_IP = int(os.environ.get("RATE_LIMIT_IP", "1200"))
RATE_LIMIT_GUEST_WRITE = int(os.environ.get("RATE_LIMIT_GUEST_WRITE", "300"))
RATE_LIMIT_MEDIA = int(os.environ.get("RATE_LIMIT_MEDIA", "900"))  # /media/ files per address
CODE_VERIFY_MAX_PER_IP = int(os.environ.get("CODE_VERIFY_MAX_PER_IP", "40"))
CODE_RESEND_MAX_PER_IP_HOUR = int(os.environ.get("CODE_RESEND_MAX_PER_IP_HOUR", "20"))
# accounts.bans: a client that keeps going until AUTO_BAN_FACTOR times a limit
# in one window is banned (an account forever, an address for 1 h / 24 h / 30 d).
AUTO_BAN_ENABLED = env_bool("AUTO_BAN_ENABLED", default="test" not in sys.argv[1:2])
AUTO_BAN_FACTOR = max(2, int(os.environ.get("AUTO_BAN_FACTOR", "2")))
AUTO_BAN_SAFE_IPS = env_list("AUTO_BAN_SAFE_IPS", "")

# Sign in with Google (accounts.google). Leave the ID empty to hide the button.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
# Pages allowed to start a Google sign-in; each needs its
# <origin>/api/auth/google/callback registered in the Google Cloud console.
GOOGLE_ALLOWED_ORIGINS = [
    o.rstrip("/")
    for o in env_list(
        "GOOGLE_ALLOWED_ORIGINS",
        f"{APP_ORIGIN},https://zinvest-kappa.vercel.app,http://localhost:5173,http://localhost:5181",
    )
]

# ---------------------------------------------------------------------------
# AI engine (ai_engine app) — Gemini via the unified google-genai SDK
# ---------------------------------------------------------------------------
# Empty key => the AI engine runs in graceful "[STUB]" mode (no external calls).
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# FLASH = fast parsing, PRO = deep reasoning, FLASH_LITE = async background work.
# Google retires model ids on its own schedule (gemini-2.5-pro and
# gemini-2.5-flash-lite stopped serving new keys in 2026 and answered 404), so
# these are env-overridable and ai_engine falls back to GEMINI_MODEL_FALLBACK
# the moment a configured id reports that it is gone.
GEMINI_MODEL_FLASH = os.environ.get("GEMINI_MODEL_FLASH", "gemini-2.5-flash")
# Measured on the live key: 3.1-flash-lite returns a complete advisor answer in
# ~4s, while 3.5-flash spends 12-29s thinking and then truncates — long enough
# to trip AI_REQUEST_TIMEOUT_SEC. Speed wins until a billed key unlocks the pro tier.
GEMINI_MODEL_PRO = os.environ.get("GEMINI_MODEL_PRO", "gemini-3.1-flash-lite")
GEMINI_MODEL_FLASH_LITE = os.environ.get("GEMINI_MODEL_FLASH_LITE", "gemini-3.1-flash-lite")
GEMINI_MODEL_FALLBACK = os.environ.get("GEMINI_MODEL_FALLBACK", "gemini-2.5-flash")
AI_REQUEST_TIMEOUT_SEC = int(os.environ.get("AI_REQUEST_TIMEOUT_SEC", "30"))

# The bear's server voice (POST /api/ai/tts): Gemini text-to-speech. Needs the
# same GEMINI_API_KEY. Clips are stored under MEDIA_ROOT/tts and reused, so only
# the first listener of a text triggers a generation; the daily limit caps new
# clips per learner. Voices: https://ai.google.dev/gemini-api/docs/speech-generation
GEMINI_TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_TTS_VOICE = os.environ.get("GEMINI_TTS_VOICE", "Puck")
TTS_DAILY_LIMIT = int(os.environ.get("TTS_DAILY_LIMIT", "60"))
TTS_MAX_CHARS = int(os.environ.get("TTS_MAX_CHARS", "1200"))

# Quota defaults used when a UserAIQuota row is first auto-created.
AI_DEFAULT_TIER = os.environ.get("AI_DEFAULT_TIER", "free")
AI_DEFAULT_MONTHLY_TOKEN_LIMIT = int(os.environ.get("AI_DEFAULT_MONTHLY_TOKEN_LIMIT", "30000"))
# Learning earns AI tokens for the current month (ai_engine.quota.add_bonus).
AI_BONUS_PER_LESSON = int(os.environ.get("AI_BONUS_PER_LESSON", "2000"))  # each lesson finished for the first time
AI_BONUS_PER_STREAK_DAY = int(os.environ.get("AI_BONUS_PER_STREAK_DAY", "1000"))  # each new day of study

# ---------------------------------------------------------------------------
# Telegram bot (telegrambot/): the pocket Zinvest — receipts, voice notes,
# questions and the bear's nudges. Empty token = the bot is simply off, the
# rest of the app does not notice.
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "ZinvestAI_bot")
# Telegram sends this back in a header on every webhook call; a request without
# it is not from Telegram. Generated per deployment, like any other secret.
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
# Photos and voice notes the bot will accept, in megabytes.
TELEGRAM_MAX_FILE_MB = int(os.environ.get("TELEGRAM_MAX_FILE_MB", "8"))

# ---------------------------------------------------------------------------
# Outgoing email (accounts/mail.py): address confirmations and password links.
# No EMAIL_HOST -> Django prints letters to the console, which is what local
# development wants. Nothing in the app fails when mail does.
# ---------------------------------------------------------------------------
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST else "django.core.mail.backends.console.EmailBackend",
)
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") not in ("0", "false", "False")
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "0") in ("1", "true", "True")
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))  # never hang a request on a slow relay
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Zinvest <no-reply@zinvest.local>")

# Self-service links (accounts/views.py).
EMAIL_VERIFY_TTL_HOURS = int(os.environ.get("EMAIL_VERIFY_TTL_HOURS", "48"))
PASSWORD_RESET_TTL_HOURS = int(os.environ.get("PASSWORD_RESET_TTL_HOURS", "1"))
FORGOT_MAX_PER_IP_HOUR = int(os.environ.get("FORGOT_MAX_PER_IP_HOUR", "10"))
FORGOT_MAX_PER_EMAIL_HOUR = int(os.environ.get("FORGOT_MAX_PER_EMAIL_HOUR", "3"))

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "ai_engine",
    "learning",
    "notes",
    "startup",
    "adminpanel",
    "telegrambot",
    "files",
    "copilot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # The interface language (Accept-Language / ?lang=) for content and the AI.
    "config.languages.LanguageMiddleware",
    # …and the `detail` of every JSON answer, in that language.
    "config.messages.TranslateMessagesMiddleware",
    # Requests per minute for the whole API, before any view runs (config/ratelimit.py).
    "config.ratelimit.RateLimitMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database — SQLite by default, Postgres when DATABASE_URL or DB_HOST is set.
# ---------------------------------------------------------------------------
if os.environ.get("DATABASE_URL"):
    # One URL, as hosted Postgres (Supabase) hands it out. Meant for a
    # connection pooler in front of the database and short-lived app instances
    # (Vercel functions): no persistent connections by default, TLS required,
    # and no server-side cursors, which a transaction-mode pooler cannot keep
    # open between statements.
    from urllib.parse import unquote, urlsplit

    _db = urlsplit(os.environ["DATABASE_URL"])
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(_db.path.lstrip("/")) or "postgres",
            "USER": unquote(_db.username or ""),
            "PASSWORD": unquote(_db.password or ""),
            "HOST": _db.hostname or "",
            "PORT": str(_db.port or 5432),
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "0")),
            "CONN_HEALTH_CHECKS": True,
            "DISABLE_SERVER_SIDE_CURSORS": True,
            "OPTIONS": {"sslmode": os.environ.get("DB_SSLMODE", "require")},
        }
    }
elif os.environ.get("DB_HOST") or os.environ.get("DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "authdb"),
            "USER": os.environ.get("DB_USER", "postgres"),
            # No weak default — supply DB_PASSWORD via the environment / .env.
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("SQLITE_PATH", BASE_DIR / "db.sqlite3"),
        }
    }

# ---------------------------------------------------------------------------
# Cache — used by the login throttle. LocMemCache is per-process; use Redis or
# the database cache in production so counters are shared across Gunicorn workers.
# ---------------------------------------------------------------------------
REDIS_URL = os.environ.get("REDIS_URL")
if REDIS_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}}
elif os.environ.get("CACHE_BACKEND") == "db":
    # Serverless: every instance has its own memory, so the counters live in a
    # table instead (`manage.py createcachetable`).
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "django_cache"}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "auth-locmem"}}

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# I18N / static
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# User uploads (avatars). Nginx serves /media/ directly in the deploy configs;
# Django only serves it when DEBUG is on (see config/urls.py).
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# MEDIA_STORAGE=db keeps uploads and the bear's voice clips in the database
# (files.StoredFile) and serves them from /media/ through Django: for hosts
# without a persistent disk, like Vercel functions.
MEDIA_STORAGE = os.environ.get("MEDIA_STORAGE", "disk")
if MEDIA_STORAGE == "db":
    STORAGES = {
        "default": {"BACKEND": "files.storage.DatabaseStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

# Scheduled jobs over HTTP (config/cron.py) for hosts without cron: the caller
# sends "Authorization: Bearer <CRON_SECRET>". Unset, the endpoint is off.
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# Avatars are the only upload; keep the accepted body small so an oversized
# file is rejected by the server before it is ever buffered to disk.
AVATAR_MAX_BYTES = 2 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Cookie / transport security
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

if not DEBUG:
    # TLS is terminated by Nginx; trust its X-Forwarded-Proto.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"
    USE_X_FORWARDED_HOST = True
    # HSTS + HTTP->HTTPS redirect are emitted by Nginx (single source of truth).
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0

# ---------------------------------------------------------------------------
# Logging — surface token-reuse / lockout warnings clearly.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "loggers": {
        "accounts.security": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
