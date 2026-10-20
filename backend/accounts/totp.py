"""
Time-based one-time passwords (RFC 6238, the codes in Google Authenticator,
1Password, Authy...), used as the second factor for staff.

Secrets are encrypted at rest with Fernet, keyed by settings.TOTP_ENCRYPTION_KEY
(derived from SECRET_KEY when that is not set), so a database dump alone does
not hand out working second factors.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.cache import cache

DIGITS = 6
PERIOD = 30
ISSUER = "Zinvest"


def _fernet():
    material = settings.TOTP_ENCRYPTION_KEY or settings.SECRET_KEY
    key = base64.urlsafe_b64encode(hashlib.sha256(("totp:" + material).encode()).digest())
    return Fernet(key)


def new_secret():
    """A fresh base32 secret (160 bits, the RFC 4226 recommendation)."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def encrypt(secret):
    return _fernet().encrypt(secret.encode()).decode()


def decrypt(stored):
    if not stored:
        return ""
    try:
        return _fernet().decrypt(stored.encode()).decode()
    except InvalidToken:
        return ""


def provisioning_uri(secret, account):
    label = quote(f"{ISSUER}:{account}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(ISSUER)}&digits={DIGITS}&period={PERIOD}"


def _code_at(secret, counter):
    padded = secret + "=" * (-len(secret) % 8)
    key = base64.b32decode(padded.upper())
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10 ** DIGITS)).zfill(DIGITS)


def now_code(secret, at=None):
    return _code_at(secret, int((at or time.time()) // PERIOD))


def verify(secret, code, *, user_id=None, at=None):
    """
    Check a code, allowing one step of clock drift either way. A code that
    worked once is refused for the rest of its window (no replay).
    """
    code = "".join(ch for ch in str(code or "") if ch.isdigit())
    if not secret or len(code) != DIGITS:
        return False
    counter = int((at or time.time()) // PERIOD)
    for step in (0, -1, 1):
        if hmac.compare_digest(_code_at(secret, counter + step), code):
            if user_id is not None:
                used_key = f"totp-used:{user_id}:{counter + step}"
                if not cache.add(used_key, 1, timeout=PERIOD * 3):
                    return False
            return True
    return False
