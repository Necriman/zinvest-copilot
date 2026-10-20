"""
End-to-end tests for the hybrid-token auth flow.

Covers the pinned wire contract, the full round-trip, and the two behaviours the
security review flagged as blocking: the family theft trap (fires on real reuse)
and the grace window (does NOT fire on a benign immediately-prior refresh).
"""
import json
from datetime import timedelta

import jwt
from django.conf import settings
from django.core.cache import cache
from django.core import mail as django_mail
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.jwt_utils import InvalidAccessToken, decode_access_token, encode_access_token
from accounts.models import RefreshToken, User
from accounts.tokens import hash_refresh_token

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
REFRESH = "/api/auth/refresh"
LOGOUT = "/api/auth/logout"
ME = "/api/auth/me"

REFRESH_COOKIE = "refresh_token"
PASSWORD = "Str0ng-Passphrase!"


# The password step on its own; the emailed code is covered in test_codes.
@override_settings(LOGIN_EMAIL_CODE=False)
class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    # ----- helpers -------------------------------------------------------
    def _post(self, url, body=None, **extra):
        return self.client.post(
            url, data=json.dumps(body or {}), content_type="application/json", **extra
        )

    def _register(self, email="user@example.com"):
        return self._post(
            REGISTER,
            {
                "email": email,
                "password": PASSWORD,
                "first_name": "Ada",
                "last_name": "Lovelace",
                "unique_device_id": "device-abc",
                "accept_terms": True,
                "age_ok": True,
            },
        )

    def _login(self, email="user@example.com"):
        return self._post(LOGIN, {"email": email, "password": PASSWORD, "unique_device_id": "device-abc"})

    def _bearer(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    # ----- contract + round-trip ----------------------------------------
    def test_full_round_trip(self):
        # register -> uniform 200, user actually created
        r = self._register()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(User.objects.filter(email="user@example.com").exists())

        # login -> access_token in body + refresh cookie set
        r = self._login()
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "Bearer")
        self.assertEqual(data["user"]["email"], "user@example.com")
        self.assertIn(REFRESH_COOKIE, r.cookies)
        cookie = r.cookies[REFRESH_COOKIE]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Strict")
        self.assertEqual(cookie["path"], "/api/auth/refresh")
        access = data["access_token"]

        # me -> protected, returns the user
        r = self.client.get(ME, **self._bearer(access))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["email"], "user@example.com")

        # me without token -> 401
        self.assertEqual(self.client.get(ME).status_code, 401)

        # refresh -> new access token + rotated cookie; old hash now revoked
        old_raw = self.client.cookies[REFRESH_COOKIE].value
        r = self._post(REFRESH, {"unique_device_id": "device-abc"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("access_token", r.json())
        self.assertTrue(RefreshToken.objects.get(token_hash=hash_refresh_token(old_raw)).is_revoked)
        new_raw = r.cookies[REFRESH_COOKIE].value
        self.assertNotEqual(old_raw, new_raw)

        # logout -> family revoked, cookie cleared
        r = self._post(LOGOUT, {}, **self._bearer(r.json()["access_token"]))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(RefreshToken.objects.filter(is_revoked=False).exists())

    def test_login_case_insensitive_email(self):
        self._register(email="Mixed@Example.com")
        r = self._post(LOGIN, {"email": "mixed@example.com", "password": PASSWORD})
        self.assertEqual(r.status_code, 200)

    # ----- theft trap (fires OUTSIDE the grace window) -------------------
    def test_reuse_after_grace_revokes_whole_family(self):
        self._register()
        self._login()
        raw1 = self.client.cookies[REFRESH_COOKIE].value

        # First refresh rotates raw1 -> raw2.
        self._post(REFRESH, {})
        family = RefreshToken.objects.get(token_hash=hash_refresh_token(raw1)).family_id

        # Push the rotation timestamp into the past so the grace window has passed.
        RefreshToken.objects.filter(family_id=family).update(
            rotated_at=timezone.now() - timedelta(minutes=5)
        )

        # Replay the already-rotated raw1 -> theft -> 401 + whole family revoked.
        self.client.cookies[REFRESH_COOKIE] = raw1
        r = self._post(REFRESH, {})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(RefreshToken.objects.filter(family_id=family, is_revoked=False).count(), 0)

    # ----- grace window (benign immediately-prior refresh) --------------
    def test_replay_within_grace_does_not_revoke_family(self):
        self._register()
        self._login()
        raw1 = self.client.cookies[REFRESH_COOKIE].value

        # Rotate raw1 -> raw2 (successor stays live; well within the grace window).
        r = self._post(REFRESH, {})
        self.assertEqual(r.status_code, 200)
        family = RefreshToken.objects.get(token_hash=hash_refresh_token(raw1)).family_id

        # Re-present the just-rotated raw1 (simulates a second tab / dropped
        # Set-Cookie). It must succeed via re-rotation and NOT nuke the family.
        self.client.cookies[REFRESH_COOKIE] = raw1
        r = self._post(REFRESH, {})
        self.assertEqual(r.status_code, 200)
        self.assertIn("access_token", r.json())
        # At least one live token remains (the family survived).
        self.assertTrue(RefreshToken.objects.filter(family_id=family, is_revoked=False).exists())

    def test_unknown_refresh_token_is_401(self):
        self.client.cookies[REFRESH_COOKIE] = "not-a-real-token"
        r = self._post(REFRESH, {})
        self.assertEqual(r.status_code, 401)

    # ----- register enumeration resistance ------------------------------
    def test_register_duplicate_is_uniform_by_default(self):
        self.assertEqual(self._register().status_code, 200)
        # Second registration with the same email returns the SAME 200 (no 409),
        # and does not create a second user.
        self.assertEqual(self._register().status_code, 200)
        self.assertEqual(User.objects.filter(email="user@example.com").count(), 1)

    def test_weak_password_rejected(self):
        r = self._post(REGISTER, {"email": "weak@example.com", "password": "123", "accept_terms": True, "age_ok": True})
        self.assertEqual(r.status_code, 400)

    def test_weak_password_names_the_broken_rules(self):
        # The interface translates these codes; the English sentences stay for
        # older clients, and nothing is created.
        r = self._post(REGISTER, {"email": "weak@example.com", "password": "123", "accept_terms": True, "age_ok": True})
        body = r.json()
        self.assertEqual(r.status_code, 400)
        self.assertIn("password_too_short", body["codes"])
        self.assertIn("password_entirely_numeric", body["codes"])
        self.assertEqual(len(body["errors"]), len(body["codes"]))
        self.assertFalse(User.objects.filter(email="weak@example.com").exists())

    # ----- throttle ------------------------------------------------------
    def test_login_throttle_locks_after_max_attempts(self):
        self._register()
        for _ in range(settings.LOGIN_MAX_ATTEMPTS):
            r = self._post(LOGIN, {"email": "user@example.com", "password": "wrong-password"})
            self.assertEqual(r.status_code, 401)
        # Next attempt (even with the CORRECT password) is locked out.
        r = self._login()
        self.assertEqual(r.status_code, 429)


class JwtHardeningTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jwt@example.com", password=PASSWORD)

    def test_valid_token_roundtrips(self):
        token = encode_access_token(self.user, "fam-1")
        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], str(self.user.id))
        self.assertEqual(payload["type"], "access")

    def test_alg_none_rejected(self):
        forged = jwt.encode({"sub": str(self.user.id), "type": "access", "iat": 0, "exp": 9999999999}, None, algorithm="none")
        with self.assertRaises(InvalidAccessToken):
            decode_access_token(forged)

    def test_wrong_signature_rejected(self):
        token = encode_access_token(self.user, "fam-1")
        tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
        with self.assertRaises(InvalidAccessToken):
            decode_access_token(tampered)

    def test_wrong_token_type_rejected(self):
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        refresh_like = jwt.encode(
            {"sub": str(self.user.id), "type": "refresh", "iat": int(now.timestamp()),
             "exp": int((now + datetime.timedelta(minutes=5)).timestamp())},
            settings.JWT_SIGNING_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        with self.assertRaises(InvalidAccessToken):
            decode_access_token(refresh_like)


@override_settings(LOGIN_EMAIL_CODE=False)
class EmailFlowTests(TestCase):
    """Confirming an address, and getting a password link without asking a human."""

    def setUp(self):
        self.client = Client()
        cache.clear()

    @property
    def outbox(self):
        # Django hands every test a fresh outbox, so read it through the module.
        return django_mail.outbox

    def _post(self, url, body=None, **extra):
        return self.client.post(url, data=json.dumps(body or {}), content_type="application/json", **extra)

    def _link(self, index=-1):
        """The URL out of the letter, the way a person would click it."""
        body = self.outbox[index].body
        return body.split("http", 1)[1].split()[0]

    def test_sign_up_mails_a_link_that_confirms_once(self):
        self._post(REGISTER, {"email": "new@example.com", "password": PASSWORD, "lang": "ru", "accept_terms": True, "age_ok": True})
        self.assertEqual(len(self.outbox), 1)
        self.assertIn("Zinvest", self.outbox[0].subject)
        token = self._link().split("token=")[1]

        user = User.objects.get(email="new@example.com")
        self.assertIsNone(user.email_verified_at)
        self.assertEqual(self._post("/api/auth/verify-email", {"token": token}).status_code, 200)
        user.refresh_from_db()
        self.assertIsNotNone(user.email_verified_at)
        # The same link cannot be replayed.
        self.assertEqual(self._post("/api/auth/verify-email", {"token": token}).status_code, 400)

    def test_forgot_password_answers_the_same_for_any_address(self):
        User.objects.create_user(email="real@example.com", password=PASSWORD)
        known = self._post("/api/auth/forgot-password", {"email": "real@example.com"})
        unknown = self._post("/api/auth/forgot-password", {"email": "nobody@example.com"})
        self.assertEqual((known.status_code, known.json()), (unknown.status_code, unknown.json()))
        self.assertEqual([m.to for m in self.outbox], [["real@example.com"]])  # only the real one gets a letter

        token = self._link().split("token=")[1]
        new_password = "An0ther-Passphrase!"
        self.assertEqual(self._post("/api/auth/password-reset", {"token": token, "new_password": new_password}).status_code, 200)
        self.assertEqual(self._post(LOGIN, {"email": "real@example.com", "password": new_password}).status_code, 200)

    @override_settings(FORGOT_MAX_PER_EMAIL_HOUR=2)
    def test_one_address_cannot_be_mail_bombed(self):
        User.objects.create_user(email="target@example.com", password=PASSWORD)
        for _ in range(4):
            self.assertEqual(self._post("/api/auth/forgot-password", {"email": "target@example.com"}).status_code, 200)
        self.assertEqual(len(self.outbox), 2)  # the rest are dropped, quietly

    @override_settings(FORGOT_MAX_PER_IP_HOUR=3)
    def test_one_ip_cannot_walk_through_addresses(self):
        for n in range(3):
            self.assertEqual(self._post("/api/auth/forgot-password", {"email": f"guess{n}@example.com"}).status_code, 200)
        self.assertEqual(self._post("/api/auth/forgot-password", {"email": "guess9@example.com"}).status_code, 429)

    def _signed_in(self, email):
        User.objects.create_user(email=email, password=PASSWORD)
        return self._post(LOGIN, {"email": email, "password": PASSWORD}).json()["access_token"]

    def _change(self, access, new_email):
        return self._post("/api/auth/me/email", {"password": PASSWORD, "new_email": new_email}, HTTP_AUTHORIZATION=f"Bearer {access}")

    def _token_sent_to(self, address):
        body = [m for m in self.outbox if m.to == [address]][-1].body
        return body.split("token=", 1)[1].split()[0]

    def test_the_address_changes_only_once_the_new_one_confirms(self):
        access = self._signed_in("old@example.com")
        response = self._change(access, "fresh@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()["email"], response.json()["pending_email"]), ("old@example.com", "fresh@example.com"))
        self.assertTrue(User.objects.filter(email="old@example.com").exists())  # nothing moved yet
        self.assertEqual(sorted(m.to[0] for m in self.outbox), ["fresh@example.com", "old@example.com"])  # the link, and a heads-up

        moved = self._post("/api/auth/verify-email", {"token": self._token_sent_to("fresh@example.com")})
        self.assertEqual((moved.status_code, moved.json()["changed"], moved.json()["email"]), (200, True, "fresh@example.com"))
        user = User.objects.get(email="fresh@example.com")
        self.assertIsNotNone(user.email_verified_at)
        self.assertEqual(self.client.get("/api/auth/me", HTTP_AUTHORIZATION=f"Bearer {access}").status_code, 401)  # signed out
        self.assertEqual(self.outbox[-1].to, ["old@example.com"])  # the old address is told
        self.assertEqual(self._post(LOGIN, {"email": "fresh@example.com", "password": PASSWORD}).status_code, 200)

    def test_a_taken_address_gets_the_same_answer_and_no_letter(self):
        User.objects.create_user(email="taken@example.com", password=PASSWORD)
        access = self._signed_in("me@example.com")
        taken, free = self._change(access, "taken@example.com"), self._change(access, "free@example.com")
        self.assertEqual((taken.status_code, taken.json()["detail"]), (free.status_code, free.json()["detail"]))
        self.assertNotIn(["taken@example.com"], [m.to for m in self.outbox])

    def test_only_the_latest_link_can_move_the_account(self):
        access = self._signed_in("me@example.com")
        self._change(access, "first@example.com")
        first = self._token_sent_to("first@example.com")
        self._change(access, "second@example.com")
        self.assertEqual(self._post("/api/auth/verify-email", {"token": first}).status_code, 400)
        self.assertTrue(User.objects.filter(email="me@example.com").exists())
