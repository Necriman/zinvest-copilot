"""
The emailed six-digit code (accounts.codes) and Sign in with Google
(accounts.google).
"""
import json
import re
from datetime import timedelta
from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts import google
from accounts.models import LoginCode, User

PASSWORD = "correct-horse-battery-9"


def post(client, url, body):
    return client.post(url, data=json.dumps(body), content_type="application/json")


def last_code():
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].subject).group(1)


class CodeSignInTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = User.objects.create_user(email="user@example.com", password=PASSWORD)

    def _challenge(self):
        res = post(self.client, "/api/auth/login", {"email": "user@example.com", "password": PASSWORD})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["code_required"])
        self.assertNotIn("access_token", body)
        return body["challenge"]

    def test_password_alone_opens_nothing_the_code_does(self):
        challenge = self._challenge()
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("refresh_token", self.client.cookies)

        res = post(self.client, "/api/auth/code/verify", {"challenge": challenge, "code": last_code()})
        self.assertEqual(res.status_code, 200)
        self.assertIn("access_token", res.json())
        self.assertFalse(res.json()["created"])
        self.assertIn("refresh_token", res.cookies)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.email_verified_at)  # the code proved the mailbox

    def test_a_code_works_once(self):
        challenge = self._challenge()
        code = last_code()
        self.assertEqual(post(self.client, "/api/auth/code/verify", {"challenge": challenge, "code": code}).status_code, 200)
        again = post(self.client, "/api/auth/code/verify", {"challenge": challenge, "code": code})
        self.assertEqual(again.json()["code"], "code_expired")

    def test_wrong_codes_count_down_then_kill_the_challenge(self):
        challenge = self._challenge()
        right = last_code()
        wrong = "000000" if right != "000000" else "111111"
        for left in (4, 3, 2, 1):
            res = post(self.client, "/api/auth/code/verify", {"challenge": challenge, "code": wrong})
            self.assertEqual(res.json()["attempts_left"], left)
        res = post(self.client, "/api/auth/code/verify", {"challenge": challenge, "code": wrong})
        self.assertEqual(res.json()["code"], "code_expired")
        # Even the right code is refused now.
        res = post(self.client, "/api/auth/code/verify", {"challenge": challenge, "code": right})
        self.assertEqual(res.json()["code"], "code_expired")

    def test_an_old_challenge_is_dead(self):
        challenge = self._challenge()
        LoginCode.objects.filter(pk=challenge).update(expires_at=timezone.now() - timedelta(seconds=1))
        res = post(self.client, "/api/auth/code/verify", {"challenge": challenge, "code": last_code()})
        self.assertEqual(res.json()["code"], "code_expired")

    def test_resend_waits_then_replaces_the_code(self):
        challenge = self._challenge()
        first = last_code()
        res = post(self.client, "/api/auth/code/resend", {"challenge": challenge})
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.json()["code"], "code_cooldown")

        LoginCode.objects.filter(pk=challenge).update(sent_at=timezone.now() - timedelta(minutes=2))
        self.assertEqual(post(self.client, "/api/auth/code/resend", {"challenge": challenge}).status_code, 200)
        second = last_code()
        if first != second:
            res = post(self.client, "/api/auth/code/verify", {"challenge": challenge, "code": first})
            self.assertEqual(res.json()["code"], "code_invalid")
        res = post(self.client, "/api/auth/code/verify", {"challenge": challenge, "code": second})
        self.assertEqual(res.status_code, 200)

    def test_the_code_is_never_stored_in_the_clear(self):
        challenge = self._challenge()
        row = LoginCode.objects.get(pk=challenge)
        self.assertNotIn(last_code(), row.code_hash)
        self.assertEqual(len(row.code_hash), 64)


class CodeSignUpTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_nothing_is_created_until_the_code_is_right(self):
        res = post(self.client, "/api/auth/register", {
            "email": "New@Example.com", "password": PASSWORD, "first_name": "Aziz", "last_name": "K",
            "accept_terms": True, "age_ok": True,
        })
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(email__iexact="new@example.com").exists())
        # The details wait with the password already hashed.
        row = LoginCode.objects.get(pk=res.json()["challenge"])
        self.assertNotIn(PASSWORD, json.dumps(row.payload))

        verify = post(self.client, "/api/auth/code/verify", {"challenge": res.json()["challenge"], "code": last_code()})
        self.assertEqual(verify.status_code, 200)
        self.assertTrue(verify.json()["created"])
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.first_name, "Aziz")
        self.assertIsNotNone(user.email_verified_at)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertIsNotNone(user.terms_accepted_at)
        self.assertTrue(user.age_confirmed)
        row.refresh_from_db()
        self.assertEqual(row.payload, {})  # the hash is not kept once used

    def test_sign_up_needs_the_terms_and_the_age_rule(self):
        for extra in ({}, {"accept_terms": True}, {"age_ok": True}, {"accept_terms": "yes", "age_ok": True}):
            res = post(self.client, "/api/auth/register", {"email": "kid@example.com", "password": PASSWORD, **extra})
            self.assertEqual(res.status_code, 400, extra)
            self.assertEqual(res.json()["code"], "consent_required")
        self.assertFalse(LoginCode.objects.filter(email="kid@example.com").exists())

    def test_a_taken_address_gets_the_same_answer_and_a_letter_to_its_owner(self):
        User.objects.create_user(email="taken@example.com", password=PASSWORD)
        res = post(self.client, "/api/auth/register", {"email": "taken@example.com", "password": "another-pass-123", "accept_terms": True, "age_ok": True})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["code_required"])
        self.assertNotRegex(mail.outbox[-1].subject, r"\d{6}")  # the owner is told, no code is sent
        for guess in ("000000", "123456"):
            verify = post(self.client, "/api/auth/code/verify", {"challenge": res.json()["challenge"], "code": guess})
            self.assertEqual(verify.status_code, 400)
        self.assertEqual(User.objects.filter(email="taken@example.com").count(), 1)
        self.assertFalse(User.objects.get(email="taken@example.com").check_password("another-pass-123"))

    @override_settings(LOGIN_CODE_MAX_PER_EMAIL_HOUR=2)
    def test_letters_to_one_address_are_limited(self):
        for _ in range(2):
            self.assertEqual(post(self.client, "/api/auth/register", {"email": "a@example.com", "password": PASSWORD, "accept_terms": True, "age_ok": True}).status_code, 200)
        res = post(self.client, "/api/auth/register", {"email": "a@example.com", "password": PASSWORD, "accept_terms": True, "age_ok": True})
        self.assertEqual(res.status_code, 429)


@override_settings(
    GOOGLE_CLIENT_ID="test-client.apps.googleusercontent.com",
    GOOGLE_CLIENT_SECRET="test-secret",
    APP_ORIGIN="http://localhost:5181",
    GOOGLE_ALLOWED_ORIGINS=["http://localhost:5181"],
)
class GoogleSignInTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def _start(self):
        res = self.client.get("/api/auth/google/start", {"origin": "http://localhost:5181", "next": "/app/lessons"})
        self.assertEqual(res.status_code, 302)
        query = parse_qs(urlparse(res["Location"]).query)
        self.assertEqual(query["redirect_uri"], ["http://localhost:5181/api/auth/google/callback"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertIn(google.COOKIE, res.cookies)
        return query["state"][0]

    def _claims(self, email="g@example.com", sub="google-sub-1"):
        return {"sub": sub, "email": email, "email_verified": True, "given_name": "Gulnora", "family_name": "T"}

    def _google(self, claims):
        state = self._start()
        with mock.patch.object(google, "_exchange", return_value=claims):
            return self.client.get("/api/auth/google/callback", {"code": "c", "state": state})

    # ---- one account, whichever way in -----------------------------------------
    def test_a_password_account_and_google_with_the_same_address_are_one_account(self):
        user = User.objects.create_user(email="test@gmail.com", password=PASSWORD)
        user.email_verified_at = timezone.now()
        user.save()
        res = self._google(self._claims("test@gmail.com"))
        self.assertIn("refresh_token", res.cookies)
        self.assertEqual(User.objects.filter(email__iexact="test@gmail.com").count(), 1)
        user.refresh_from_db()
        self.assertEqual(user.google_sub, "google-sub-1")
        # Both ways in keep working: the proven password stays.
        self.assertTrue(user.check_password(PASSWORD))
        cache.clear()
        login = post(self.client, "/api/auth/login", {"email": "test@gmail.com", "password": PASSWORD})
        self.assertEqual(login.status_code, 200)

    def test_an_unproven_password_goes_when_google_proves_the_address(self):
        # Someone typed this address into the sign-up form with their own password
        # before its owner ever came: the owner, proven by Google, gets the account.
        squatter = User.objects.create_user(email="victim@gmail.com", password=PASSWORD)
        self.assertIsNone(squatter.email_verified_at)
        from accounts.models import RefreshToken
        RefreshToken.objects.create(
            user=squatter, token_hash="x" * 64, expires_at=timezone.now() + timedelta(days=1)
        )
        res = self._google(self._claims("victim@gmail.com"))
        self.assertIn("refresh_token", res.cookies)
        squatter.refresh_from_db()
        self.assertFalse(squatter.has_usable_password())
        self.assertIsNotNone(squatter.email_verified_at)
        self.assertIsNotNone(squatter.tokens_valid_after)
        self.assertFalse(RefreshToken.objects.filter(user=squatter, token_hash="x" * 64, is_revoked=False).exists())

    def test_the_google_account_is_found_even_after_its_address_changes(self):
        user = User.objects.create_user(email="old@example.com", password=PASSWORD)
        user.google_sub = "google-sub-1"
        user.save()
        res = self._google(self._claims("new@example.com"))
        self.assertIn("refresh_token", res.cookies)
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_an_address_tied_to_another_google_account_is_refused(self):
        user = User.objects.create_user(email="g@example.com", password=PASSWORD)
        user.google_sub = "someone-else"
        user.save()
        res = self._google(self._claims("g@example.com"))
        self.assertIn("google=conflict", res["Location"])
        self.assertNotIn("refresh_token", res.cookies)

    def test_the_profile_says_how_the_account_signs_in(self):
        self._google(self._claims("fresh@example.com"))
        user = User.objects.get(email="fresh@example.com")
        from accounts.jwt_utils import encode_access_token
        token = encode_access_token(user, "00000000-0000-0000-0000-000000000000")
        me = self.client.get("/api/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}").json()
        self.assertFalse(me["has_password"])
        self.assertTrue(me["google_linked"])

    def test_a_new_address_gets_an_account_and_goes_to_the_questions(self):
        state = self._start()
        with mock.patch.object(google, "_exchange", return_value=self._claims()):
            res = self.client.get("/api/auth/google/callback", {"code": "c", "state": state})
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res["Location"].startswith("http://localhost:5181/onboarding"))
        self.assertIn("refresh_token", res.cookies)
        user = User.objects.get(email="g@example.com")
        self.assertEqual(user.first_name, "Gulnora")
        self.assertFalse(user.has_usable_password())

    def test_an_existing_account_signs_in_and_goes_where_it_was_going(self):
        User.objects.create_user(email="g@example.com", password=PASSWORD)
        state = self._start()
        with mock.patch.object(google, "_exchange", return_value=self._claims("G@Example.com")):
            res = self.client.get("/api/auth/google/callback", {"code": "c", "state": state})
        self.assertEqual(res["Location"], "http://localhost:5181/app/lessons")
        self.assertEqual(User.objects.filter(email__iexact="g@example.com").count(), 1)

    def test_a_forged_state_is_refused(self):
        self._start()
        with mock.patch.object(google, "_exchange", return_value=self._claims()) as exchange:
            res = self.client.get("/api/auth/google/callback", {"code": "c", "state": "forged"})
        exchange.assert_not_called()
        self.assertIn("google=expired", res["Location"])
        self.assertFalse(User.objects.filter(email="g@example.com").exists())

    def test_an_unknown_origin_falls_back_to_the_app(self):
        res = self.client.get("/api/auth/google/start", {"origin": "https://evil.example"})
        query = parse_qs(urlparse(res["Location"]).query)
        self.assertEqual(query["redirect_uri"], ["http://localhost:5181/api/auth/google/callback"])


class PasswordlessDeleteTests(TestCase):
    """A Google-only account has no password: it confirms deletion with its
    email address, from a sign-in made in the last fifteen minutes."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="g@example.com", password=None)
        self.client = Client()

    def _delete(self, signed_in_minutes_ago, confirm):
        from django.test import RequestFactory

        from accounts.jwt_utils import encode_access_token
        from accounts.models import RefreshToken
        from accounts.views import _issue_session

        _, family = _issue_session(self.user, RequestFactory().get("/"))
        RefreshToken.objects.filter(family_id=family).update(created_at=timezone.now() - timedelta(minutes=signed_in_minutes_ago))
        token = encode_access_token(self.user, family)
        return self.client.delete(
            "/api/auth/me/delete", data=json.dumps({"confirm": confirm}),
            content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def test_the_email_must_be_typed(self):
        res = self._delete(1, "someone@else.com")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "confirm_email")
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_an_old_sign_in_has_to_sign_in_again(self):
        res = self._delete(30, "G@example.com")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["code"], "reauth_required")
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_a_fresh_sign_in_with_the_email_deletes(self):
        res = self._delete(2, " G@example.com ")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
