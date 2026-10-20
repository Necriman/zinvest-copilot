"""
Opaque refresh tokens.

The raw token is 512 bits of CSPRNG entropy and is the ONLY thing ever placed in
the cookie; the database stores only its SHA-256 digest. Because the input is a
full-entropy random secret looked up by an indexed equality on the digest, an
unsalted hash and a plain (non-constant-time) DB comparison are correct here —
there is no low-entropy, adaptively-probeable secret to leak via timing.
"""
import hashlib
import secrets


def generate_refresh_token():
    return secrets.token_urlsafe(64)


def hash_refresh_token(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
