"""
Manual JWT encode/decode for the short-lived access token (PyJWT).

The single most important security control here is pinning ``algorithms=[...]``
on decode: it is what rejects ``alg=none`` (PyJWT refuses "none" unless explicitly
allowed) and HS/RS algorithm-confusion (a token forged with RS256 and verified
against the HMAC secret is rejected because RS256 is not in the allow-list).
"""
import datetime

import jwt  # PyJWT 2.10.1
from django.conf import settings

ALGORITHM = settings.JWT_ALGORITHM  # "HS256"
DEFAULT_LEEWAY = datetime.timedelta(seconds=10)  # small clock-skew tolerance


class InvalidAccessToken(Exception):
    """Raised for any structurally or semantically invalid access token."""


def _signing_key():
    # HS256: symmetric — sign & verify with the dedicated JWT key.
    # To swap to RS256: return settings.JWT_PRIVATE_KEY here, return
    # settings.JWT_PUBLIC_KEY in _verifying_key(), and set JWT_ALGORITHM="RS256".
    return settings.JWT_SIGNING_KEY


def _verifying_key():
    return settings.JWT_SIGNING_KEY


def encode_access_token(user, family_id):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "type": "access",             # checked on decode; refresh path never mints this
        "sub": str(user.id),
        "email": user.email,
        "fam": str(family_id),        # enables cookie-less logout (cookie is path-scoped)
        "iat": int(now.timestamp()),
        "iat_ms": int(now.timestamp() * 1000),  # precise, for "signed out after this moment"
        "exp": int((now + settings.ACCESS_TOKEN_TTL).timestamp()),
    }
    return jwt.encode(payload, _signing_key(), algorithm=ALGORITHM)


def decode_access_token(token, *, exp_leeway=None):
    """
    Verify signature + required claims and return the payload, or raise
    InvalidAccessToken.

    ``exp_leeway`` (a timedelta) widens the acceptable expiry window; logout
    passes a small, bounded leeway so a *just*-expired token can still be used
    to revoke a family — never an unlimited window (security review #6).
    Signature is ALWAYS verified.
    """
    leeway = exp_leeway if exp_leeway is not None else DEFAULT_LEEWAY
    try:
        payload = jwt.decode(
            token,
            _verifying_key(),
            algorithms=[ALGORITHM],  # the pin — rejects alg=none and key confusion
            leeway=leeway,
            options={
                "require": ["exp", "iat", "type", "sub"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
            },
        )
    except jwt.ExpiredSignatureError:
        raise InvalidAccessToken("expired")
    except jwt.InvalidTokenError:  # base class for all PyJWT errors
        raise InvalidAccessToken("invalid")

    if payload.get("type") != "access":
        raise InvalidAccessToken("wrong_token_type")
    return payload
