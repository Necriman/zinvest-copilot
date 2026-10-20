"""The API rate limits (config/ratelimit.py)."""
import json
import uuid

from django.core.cache import cache
from django.test import TestCase, override_settings

from accounts.jwt_utils import encode_access_token
from accounts.models import User
from config.ratelimit import local

LIMITS = dict(
    RATE_LIMITS_ENABLED=True,
    RATE_LIMIT_READ=3,
    RATE_LIMIT_WRITE=2,
    RATE_LIMIT_UPLOAD=1,
    RATE_LIMIT_HEAVY=1,
    RATE_LIMIT_IP=100,
    RATE_LIMIT_GUEST_WRITE=4,
)


@override_settings(**LIMITS)
class RateLimitTests(TestCase):
    def setUp(self):
        local.clear()
        cache.clear()
        self.a = User.objects.create_user(email="a@example.test", password="Str0ng-Passphrase!")
        self.b = User.objects.create_user(email="b@example.test", password="Str0ng-Passphrase!")

    def auth(self, user):
        return {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(user, uuid.uuid4())}

    def test_guests_are_limited_by_ip_with_a_clear_answer(self):
        for _ in range(3):
            self.assertNotEqual(self.client.get("/api/announcements").status_code, 429)
        r = self.client.get("/api/announcements", HTTP_ACCEPT_LANGUAGE="ru")
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.json()["code"], "rate_limited")
        self.assertIn("Слишком много запросов", r.json()["detail"])
        self.assertTrue(1 <= int(r["Retry-After"]) <= 60)

    def test_signed_in_users_are_counted_each_on_their_own(self):
        # Same IP (a school behind one address): one busy user does not lock out the other.
        for _ in range(3):
            self.assertEqual(self.client.get("/api/auth/me", **self.auth(self.a)).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", **self.auth(self.a)).status_code, 429)
        self.assertEqual(self.client.get("/api/auth/me", **self.auth(self.b)).status_code, 200)

    def test_writes_have_their_own_lower_limit(self):
        post = lambda: self.client.post("/api/startup/todos", data=json.dumps({"title": "x"}), content_type="application/json", **self.auth(self.a))
        self.assertEqual(post().status_code, 201)
        self.assertEqual(post().status_code, 201)
        self.assertEqual(post().status_code, 429)
        # Reads still work.
        self.assertEqual(self.client.get("/api/startup/todos", **self.auth(self.a)).status_code, 200)

    def test_uploads_and_ai_are_limited_hardest(self):
        upload = lambda: self.client.post("/api/auth/me/avatar", data={}, **self.auth(self.a))  # multipart, no file
        self.assertEqual(upload().status_code, 400)
        self.assertEqual(upload().status_code, 429)
        ask = lambda: self.client.post("/api/startup/roadmap/questions", data="{}", content_type="application/json", **self.auth(self.a))
        self.assertNotEqual(ask().status_code, 429)
        self.assertEqual(ask().status_code, 429)

    def test_guests_writing_share_a_higher_limit_per_ip(self):
        login = lambda: self.client.post("/api/auth/login", data="{}", content_type="application/json")
        for _ in range(4):
            self.assertNotEqual(login().status_code, 429)
        self.assertEqual(login().status_code, 429)

    @override_settings(RATE_LIMIT_IP=4, RATE_LIMIT_READ=100)
    def test_one_ip_has_a_ceiling_whoever_it_claims_to_be(self):
        for user in (self.a, self.b, self.a, self.b):
            self.assertEqual(self.client.get("/api/auth/me", **self.auth(user)).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", **self.auth(self.a)).status_code, 429)

    def test_a_forged_token_counts_as_the_ip(self):
        forged = {"HTTP_AUTHORIZATION": "Bearer not.a.token"}
        for _ in range(3):
            self.client.get("/api/announcements", **forged)
        self.assertEqual(self.client.get("/api/announcements").status_code, 429)

    @override_settings(RATE_LIMIT_MEDIA=2)
    def test_uploaded_files_are_counted_per_address_too(self):
        for _ in range(2):
            self.assertNotEqual(self.client.get("/media/avatars/x.png").status_code, 429)
        self.assertEqual(self.client.get("/media/avatars/x.png").status_code, 429)

    def test_api_answers_are_never_kept_in_a_shared_cache(self):
        self.assertEqual(self.client.get("/api/auth/me", **self.auth(self.a))["Cache-Control"], "no-store")

    def test_signed_callers_and_pages_are_not_limited(self):
        for _ in range(6):
            self.assertNotEqual(self.client.post("/api/telegram/webhook", data="{}", content_type="application/json").status_code, 429)
            self.assertNotEqual(self.client.get("/api/cron/nudges").status_code, 429)
            self.assertNotEqual(self.client.get("/not-api/").status_code, 429)

    @override_settings(RATE_LIMITS_ENABLED=False)
    def test_can_be_switched_off(self):
        for _ in range(6):
            self.assertNotEqual(self.client.get("/api/announcements").status_code, 429)


@override_settings(RATE_LIMIT_STORE="db")
class DatabaseCounterTests(TestCase):
    """On Vercel the counters live in the RateBucket table: exact under concurrency."""

    def test_counts_and_window(self):
        from unittest.mock import patch

        from accounts import security
        from accounts.models import RateBucket

        self.assertTrue(security.hit("t", "k", 2, 60))
        self.assertTrue(security.hit("t", "k", 2, 60))
        self.assertFalse(security.hit("t", "k", 2, 60))
        self.assertTrue(security.over("t", "k", 2))
        self.assertEqual(RateBucket.objects.get(name="t:k").hits, 3)
        # A new window starts once the old one has passed.
        with patch("accounts.security.time.time", return_value=__import__("time").time() + 61):
            self.assertTrue(security.hit("t", "k", 2, 60))
            self.assertFalse(security.over("t", "k", 2))
        security.reset("t", "k")
        self.assertFalse(RateBucket.objects.filter(name="t:k").exists())

    def test_parallel_requests_lose_no_count(self):
        import threading

        from django.db import connection

        from accounts import security
        from accounts.models import RateBucket

        if connection.vendor == "sqlite":
            # SQLite serialises writers; the point is that each upsert is one statement.
            for _ in range(20):
                security.hit("p", "k", 100, 60)
        else:  # pragma: no cover - Postgres in CI
            threads = [threading.Thread(target=security.hit, args=("p", "k", 100, 60)) for _ in range(20)]
            [t.start() for t in threads]
            [t.join() for t in threads]
        self.assertEqual(RateBucket.objects.get(name="p:k").hits, 20)

    @override_settings(**LIMITS)
    def test_the_middleware_uses_it(self):
        local.clear()
        for _ in range(3):
            self.client.get("/api/announcements")
        self.assertEqual(self.client.get("/api/announcements").status_code, 429)
