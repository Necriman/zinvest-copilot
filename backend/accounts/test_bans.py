"""Automatic bans for clients that keep hammering a rate limit (accounts.bans)."""
import json
import uuid
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts import bans, security
from accounts.jwt_utils import encode_access_token
from accounts.models import Ban, SecurityEvent
from adminpanel.models import AuditLog
from adminpanel.tests import PASSWORD, Client, make_user
from config.ratelimit import local

IP = "198.51.100.7"
SETTINGS = dict(
    RATE_LIMITS_ENABLED=True, AUTO_BAN_ENABLED=True, AUTO_BAN_FACTOR=2, RATE_LIMIT_STORE="db",
    RATE_LIMIT_READ=3, RATE_LIMIT_WRITE=2, RATE_LIMIT_UPLOAD=1, RATE_LIMIT_HEAVY=1, RATE_LIMIT_IP=1000, RATE_LIMIT_GUEST_WRITE=50,
)


class BanTestCase(TestCase):
    def setUp(self):
        local.clear()
        cache.clear()
        bans.forget()
        self.user = make_user("learner@example.test")
        self.other = make_user("other@example.test")

    def auth(self, user):
        return {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(user, uuid.uuid4()), "REMOTE_ADDR": IP}

    def me(self, user):
        return self.client.get("/api/auth/me", **self.auth(user))

    def guest(self, ip=IP):
        return self.client.get("/api/announcements", REMOTE_ADDR=ip)

    def post(self, path, data, ip=IP):
        return self.client.post(path, data=json.dumps(data), content_type="application/json", REMOTE_ADDR=ip)


@override_settings(**SETTINGS)
class AutoBanTests(BanTestCase):
    def test_hitting_a_limit_once_only_slows_you_down(self):
        for _ in range(3):
            self.assertEqual(self.me(self.user).status_code, 200)
        for _ in range(2):  # told twice to wait, stops there
            self.assertEqual(self.me(self.user).json()["code"], "rate_limited")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertFalse(Ban.objects.exists())

    def test_a_script_that_keeps_going_loses_the_account_for_good(self):
        for _ in range(6):  # limit 3, banned at twice that
            self.me(self.user)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIn("api-read", self.user.disabled_reason)
        ban = Ban.objects.get()
        self.assertEqual((ban.kind, ban.value, ban.hits, ban.limit, ban.expires_at), ("user", str(self.user.pk), 6, 3, None))
        event = SecurityEvent.objects.get(kind=SecurityEvent.Kind.AUTO_BAN)
        self.assertEqual((event.user, event.details["until"]), (self.user, "forever"))
        # Its sessions are dead, even once the counter would let it through again.
        security.reset("api-read", f"u:{self.user.pk}")
        self.assertEqual(self.me(self.user).status_code, 401)
        # Others on the same network are untouched.
        self.assertEqual(self.me(self.other).status_code, 200)

    def test_the_owner_of_a_banned_account_is_told_so_only_with_the_password(self):
        bans.ban_user(str(self.user.pk), "api-write", 4, 2)
        right = self.post("/api/auth/login", {"email": self.user.email, "password": PASSWORD})
        self.assertEqual((right.status_code, right.json()["code"]), (403, "account_blocked"))
        wrong = self.post("/api/auth/login", {"email": self.user.email, "password": "not-the-password"})
        self.assertEqual(wrong.status_code, 401)

    def test_a_flooding_guest_gets_its_address_banned_for_an_hour(self):
        for _ in range(6):
            self.guest()
        r = self.client.get("/api/announcements", REMOTE_ADDR=IP, HTTP_ACCEPT_LANGUAGE="ru")
        self.assertEqual((r.status_code, r.json()["code"]), (429, "ip_banned"))
        self.assertIn("заблокирована", r.json()["detail"])
        self.assertTrue(3500 <= int(r["Retry-After"]) <= 3600)
        ban = Ban.objects.get()
        self.assertEqual((ban.kind, ban.value, ban.strike), ("ip", IP, 1))
        # People signed in on that network keep working; other networks are not affected.
        self.assertEqual(self.me(self.user).status_code, 200)
        self.assertNotEqual(self.guest("203.0.113.9").status_code, 429)
        # Refreshing a session someone already has still works from there.
        self.client.cookies["refresh_token"] = "some-refresh-token"
        self.assertNotEqual(self.client.post("/api/auth/refresh", REMOTE_ADDR=IP).json().get("code"), "ip_banned")

    def test_address_bans_grow_with_every_strike_and_lifted_ones_do_not_count(self):
        for expected in (timedelta(hours=1), timedelta(hours=24), timedelta(days=30), timedelta(days=30)):
            ban = bans.ban_ip(IP, "register", 20, 10)
            self.assertAlmostEqual((ban.expires_at - timezone.now()).total_seconds(), expected.total_seconds(), delta=5)
            self.assertEqual(bans.ban_ip(IP, "register", 20, 10), ban)  # one ban at a time
            Ban.objects.filter(pk=ban.pk).update(expires_at=timezone.now() - timedelta(seconds=1))  # served
        Ban.objects.update(lifted_at=timezone.now(), lifted_by="owner@example.test")
        self.assertEqual(bans.ban_ip(IP, "register", 20, 10).strike, 1)

    @override_settings(REGISTER_MAX_PER_IP_HOUR=2)
    def test_mass_sign_ups_from_one_address_ban_it(self):
        sign_up = lambda n: self.post("/api/auth/register", {
            "email": f"bot{n}@example.test", "password": "Str0ng-Passphrase!", "accept_terms": True, "age_ok": True,
        })
        codes = [sign_up(n).status_code for n in range(4)]
        self.assertEqual(codes[2:], [429, 429])
        self.assertEqual(sign_up(5).json()["code"], "ip_banned")
        self.assertEqual(Ban.objects.get().reason, "register")

    @override_settings(LOGIN_MAX_ATTEMPTS=2)
    def test_knocking_on_after_a_sign_in_lockout_bans_the_address(self):
        attempt = lambda: self.post("/api/auth/login", {"email": self.user.email, "password": "guess"})
        for _ in range(2):
            self.assertEqual(attempt().status_code, 401)
        for _ in range(8):  # locked: 4 refusals are allowed, banned at 8
            self.assertEqual(attempt().json()["code"], "rate_limited")
        self.assertEqual(attempt().json()["code"], "ip_banned")
        self.assertEqual(Ban.objects.get().reason, "login-locked")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)  # the account they attacked is fine

    @override_settings(FORGOT_MAX_PER_EMAIL_HOUR=1)
    def test_a_target_is_never_banned_for_being_attacked(self):
        for n in range(4):  # many addresses ask for someone's reset link
            self.post("/api/auth/forgot-password", {"email": self.user.email}, ip=f"198.51.100.{20 + n}")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertFalse(Ban.objects.exists())

    def test_staff_and_loopback_are_never_banned_automatically(self):
        owner = make_user("owner@example.test", role="owner")
        for _ in range(8):
            self.me(owner)
        for _ in range(8):
            self.guest("127.0.0.1")
        owner.refresh_from_db()
        self.assertTrue(owner.is_active)
        self.assertFalse(Ban.objects.exists())
        self.assertEqual(
            sorted(e.details["target"] for e in SecurityEvent.objects.filter(kind=SecurityEvent.Kind.AUTO_BAN)), ["account", "ip"])
        self.assertTrue(all(e.details["banned"] is False for e in SecurityEvent.objects.filter(kind=SecurityEvent.Kind.AUTO_BAN)))

    def test_staff_see_bans_and_live_counters_and_lift_them(self):
        user_ban = bans.ban_user(str(self.user.pk), "api-write", 4, 2)
        ip_ban = bans.ban_ip(IP, "register", 20, 10)
        self.assertEqual(self.guest().json()["code"], "ip_banned")
        self.me(self.other)  # something on the live counters
        owner, support = make_user("owner@example.test", role="owner"), make_user("support@example.test", role="support")
        with self.settings(RATE_LIMITS_ENABLED=False):
            staff = Client(self, owner)
            staff.unlock()
            data = staff.get("/api/admin/security/bans").json()
            self.assertEqual((data["summary"]["accounts"], data["summary"]["addresses"]), (1, 1))
            self.assertEqual({b["kind"] for b in data["results"]}, {"user", "ip"})
            self.assertIn({"scope": "api-read", "who": self.other.email}, [{"scope": c["scope"], "who": c["who"]} for c in data["counters"]])
            helper = Client(self, support)
            helper.unlock()
            self.assertEqual(helper.get("/api/admin/security/bans").status_code, 403)
            self.assertEqual(helper.send("post", f"/api/admin/security/bans/{ip_ban.id}/lift").status_code, 403)
            self.assertEqual(staff.send("post", f"/api/admin/security/bans/{user_ban.id}/lift").status_code, 200)
            self.assertEqual(staff.send("post", f"/api/admin/security/bans/{user_ban.id}/lift").status_code, 409)
            self.assertEqual(staff.send("post", f"/api/admin/security/bans/{ip_ban.id}/lift").status_code, 200)
            self.assertEqual(staff.get("/api/admin/security/bans").json()["total"], 0)
        self.user.refresh_from_db()
        self.assertEqual((self.user.is_active, self.user.disabled_reason), (True, ""))
        self.assertNotEqual(self.guest().status_code, 429)
        self.assertEqual(AuditLog.objects.filter(action="ban.lifted").count(), 2)
        self.assertEqual(SecurityEvent.objects.filter(kind=SecurityEvent.Kind.BAN_LIFTED).count(), 2)

    def test_switching_an_account_back_on_by_hand_closes_its_ban(self):
        ban = bans.ban_user(str(self.user.pk), "export", 10, 5)
        with self.settings(RATE_LIMITS_ENABLED=False):
            staff = Client(self, make_user("owner@example.test", role="owner"))
            staff.unlock()
            self.assertEqual(staff.send("post", f"/api/admin/users/{self.user.pk}/status", {"active": True}).status_code, 200)
        ban.refresh_from_db()
        self.assertIsNotNone(ban.lifted_at)

    def test_a_ban_also_cuts_off_the_telegram_chat(self):
        from telegrambot import handlers
        from telegrambot.models import TelegramLink

        TelegramLink.objects.create(user=self.user, chat_id=4242)
        TelegramLink.objects.create(user=self.other, chat_id=4343)
        self.assertIsNotNone(handlers._link_for(4242))
        bans.ban_user(str(self.user.pk), "api-write", 4, 2)
        self.assertFalse(TelegramLink.objects.filter(user=self.user).exists())
        # And a chat whose account is switched off by hand is not served either.
        self.other.is_active = False
        self.other.save(update_fields=["is_active"])
        self.assertIsNone(handlers._link_for(4343))

    @override_settings(AUTO_BAN_ENABLED=False)
    def test_the_switch_turns_automatic_bans_off(self):
        for _ in range(8):
            self.me(self.user)
        self.assertFalse(Ban.objects.exists())


@override_settings(**{**SETTINGS, "RATE_LIMIT_STORE": "cache"})
class AutoBanWithCacheCountersTests(BanTestCase):
    def test_bans_work_with_counters_in_the_cache_too(self):
        for _ in range(6):
            self.me(self.user)
        for _ in range(6):
            self.guest()
        self.assertEqual(sorted(Ban.objects.values_list("kind", flat=True)), ["ip", "user"])
