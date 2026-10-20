import json
import uuid
from datetime import timedelta

from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from accounts import security, totp
from accounts.jwt_utils import encode_access_token
from accounts.models import RefreshToken, SecurityEvent, User
from learning.models import Lesson, LessonProgress, Unit
from startup.models import BusinessPost, StartupProfile

from .models import Announcement, AuditLog, PlatformSettings, Report, SudoGrant

PASSWORD = "Str0ng-Passphrase!"


def make_user(email, role="", **extra):
    user = User.objects.create_user(email=email, password=PASSWORD, **extra)
    if role:
        user.staff_role = role
        user.save(update_fields=["staff_role"])
    return user


class Client:
    """A signed-in API client for one user on one device."""

    def __init__(self, test, user):
        self.test, self.user, self.family = test, user, str(uuid.uuid4())
        self.auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(user, self.family)}

    def get(self, path, **extra):
        return self.test.client.get(path, **self.auth, **extra)

    def send(self, method, path, data=None, **extra):
        return getattr(self.test.client, method)(path, data=json.dumps(data or {}), content_type="application/json", **self.auth, **extra)

    def unlock(self):
        response = self.send("post", "/api/admin/unlock", {"password": PASSWORD})
        self.test.assertEqual(response.status_code, 200, response.content)
        return response


class SecurityHardeningTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_client_ip_only_trusts_proxy_headers_from_proxies(self):
        factory = RequestFactory()
        spoofed = factory.get("/", REMOTE_ADDR="203.0.113.5", HTTP_X_REAL_IP="1.2.3.4", HTTP_X_FORWARDED_FOR="5.6.7.8")
        self.assertEqual(security.client_ip(spoofed), "203.0.113.5")
        proxied = factory.get("/", REMOTE_ADDR="127.0.0.1", HTTP_X_REAL_IP="198.51.100.7")
        self.assertEqual(security.client_ip(proxied), "198.51.100.7")
        chain = factory.get("/", REMOTE_ADDR="10.0.0.2", HTTP_X_FORWARDED_FOR="6.6.6.6, 198.51.100.9, 10.0.0.3")
        self.assertEqual(security.client_ip(chain), "198.51.100.9")

    def login(self, email, password, ip):
        return self.client.post("/api/auth/login", data=json.dumps({"email": email, "password": password}), content_type="application/json", REMOTE_ADDR=ip)

    @override_settings(LOGIN_MAX_ATTEMPTS=10, IP_MAX_ATTEMPTS=4)
    def test_own_login_does_not_reset_the_ip_counter(self):
        for email in ("one@example.test", "two@example.test", "attacker@example.test"):
            make_user(email)
        for _ in range(3):
            self.assertEqual(self.login("one@example.test", "wrong-guess", "203.0.113.9").status_code, 401)
        # Signing into their own account must not wipe the spray counter for the IP...
        self.assertEqual(self.login("attacker@example.test", PASSWORD, "203.0.113.9").status_code, 200)
        self.assertEqual(self.login("two@example.test", "wrong-guess", "203.0.113.9").status_code, 401)
        # ...so the fourth failure from this IP pauses it, whichever account is next.
        self.assertEqual(self.login("two@example.test", PASSWORD, "203.0.113.9").status_code, 429)
        self.assertTrue(SecurityEvent.objects.filter(kind=SecurityEvent.Kind.LOGIN_FAILED, email="one@example.test").exists())

    @override_settings(EMAIL_MAX_ATTEMPTS=3)
    def test_many_addresses_cannot_keep_guessing_one_account(self):
        make_user("target@example.test")
        for n in range(3):
            self.assertEqual(self.login("target@example.test", "nope", f"203.0.113.{n + 1}").status_code, 401)
        self.assertEqual(self.login("target@example.test", PASSWORD, "198.51.100.50").status_code, 429)

    @override_settings(REGISTER_MAX_PER_IP_HOUR=2)
    def test_sign_ups_are_limited_per_ip_and_can_be_paused(self):
        def register(n, ip="203.0.113.20"):
            return self.client.post("/api/auth/register", data=json.dumps({"email": f"new{n}@example.test", "password": PASSWORD, "accept_terms": True, "age_ok": True}), content_type="application/json", REMOTE_ADDR=ip)

        self.assertEqual(register(1).status_code, 200)
        self.assertEqual(register(2).status_code, 200)
        throttled = register(3)
        # The app shows coded answers in the learner's language.
        self.assertEqual((throttled.status_code, throttled.json()["code"]), (429, "rate_limited"))
        settings_row = PlatformSettings.current()
        settings_row.registration_open = False
        settings_row.save()
        closed = register(4, ip="198.51.100.3")
        self.assertEqual((closed.status_code, closed.json()["code"]), (503, "registration_closed"))

    @override_settings(PASSWORD_CHECK_MAX=2)
    def test_wrong_current_password_is_limited(self):
        user = make_user("pw@example.test")
        api = Client(self, user)
        for _ in range(2):
            self.assertEqual(api.send("post", "/api/auth/me/password", {"current_password": "bad", "new_password": "An0ther-Passphrase!"}).status_code, 400)
        self.assertEqual(api.send("post", "/api/auth/me/password", {"current_password": PASSWORD, "new_password": "An0ther-Passphrase!"}).status_code, 429)

    def test_signing_out_everywhere_kills_access_tokens_at_once(self):
        user = make_user("tokens@example.test")
        old = Client(self, user)
        self.assertEqual(old.get("/api/auth/me").status_code, 200)
        user.tokens_valid_after = timezone.now() + timedelta(seconds=1)
        user.save(update_fields=["tokens_valid_after"])
        self.assertEqual(old.get("/api/auth/me").status_code, 401)


@override_settings(ADMIN_REQUIRE_2FA=False, ADMIN_SUDO_MINUTES=30)
class AdminPanelTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = make_user("owner@example.test", role="owner")
        self.support = make_user("support@example.test", role="support")
        self.analyst = make_user("analyst@example.test", role="analyst")
        self.learner = make_user("learner@example.test", first_name="Lina")

    def test_only_the_team_gets_in_and_only_after_confirming(self):
        learner = Client(self, self.learner)
        self.assertEqual(learner.get("/api/admin/me").status_code, 403)
        self.assertEqual(learner.get("/api/admin/overview").status_code, 403)
        owner = Client(self, self.owner)
        me = owner.get("/api/admin/me").json()
        self.assertEqual((me["role"], me["unlocked"]), ("owner", False))
        self.assertEqual(owner.get("/api/admin/overview").json()["code"], "unlock_required")
        self.assertEqual(owner.send("post", "/api/admin/unlock", {"password": "wrong"}).status_code, 400)
        owner.unlock()
        overview = owner.get("/api/admin/overview")
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(overview.json()["users"]["total"], 4)
        # The confirmation belongs to this device only.
        self.assertEqual(Client(self, self.owner).get("/api/admin/overview").json()["code"], "unlock_required")

    def test_roles_limit_what_can_be_done(self):
        analyst = Client(self, self.analyst)
        analyst.unlock()
        self.assertEqual(analyst.get("/api/admin/users").status_code, 200)
        self.assertEqual(analyst.send("post", f"/api/admin/users/{self.learner.pk}/status", {"active": False, "reason": "x"}).status_code, 403)

        support = Client(self, self.support)
        support.unlock()
        # Support looks after learners...
        self.assertEqual(support.send("post", f"/api/admin/users/{self.learner.pk}/status", {"active": False, "reason": "Spam"}).status_code, 200)
        self.learner.refresh_from_db()
        self.assertFalse(self.learner.is_active)
        # ...but cannot touch team accounts, nor give roles.
        self.assertEqual(support.send("post", f"/api/admin/users/{self.analyst.pk}/status", {"active": False, "reason": "x"}).status_code, 403)
        self.assertEqual(support.send("post", f"/api/admin/users/{self.analyst.pk}/reset-link").status_code, 403)
        self.assertEqual(support.send("post", f"/api/admin/users/{self.learner.pk}/role", {"role": "admin"}).status_code, 403)
        self.assertTrue(AuditLog.objects.filter(action="user.disabled", actor=self.support).exists())

    def test_changes_need_a_fresh_confirmation(self):
        owner = Client(self, self.owner)
        owner.unlock()
        SudoGrant.objects.filter(user=self.owner).update(created_at=timezone.now() - timedelta(minutes=45))
        self.assertEqual(owner.get("/api/admin/users").status_code, 200)  # still open for reading
        response = owner.send("post", f"/api/admin/users/{self.learner.pk}/coins", {"delta": 50, "reason": "Contest"})
        self.assertEqual(response.json()["code"], "sudo_required")
        owner.unlock()
        self.assertEqual(owner.send("post", f"/api/admin/users/{self.learner.pk}/coins", {"delta": 50, "reason": "Contest"}).json()["coins"], 50)

    def test_two_factor_setup_and_codes(self):
        owner = Client(self, self.owner)
        secret = owner.send("post", "/api/admin/totp/setup", {"password": PASSWORD}).json()["secret"]
        self.assertEqual(owner.send("post", "/api/admin/totp/enable", {"code": "000000" if totp.now_code(secret) != "000000" else "111111"}).status_code, 400)
        code = totp.now_code(secret)
        me = owner.send("post", "/api/admin/totp/enable", {"code": code}).json()
        self.assertTrue(me["totp_enabled"] and me["unlocked"])
        self.owner.refresh_from_db()
        self.assertNotIn(secret, self.owner.totp_secret)  # stored encrypted
        other_device = Client(self, self.owner)
        self.assertEqual(other_device.send("post", "/api/admin/unlock", {"password": PASSWORD}).status_code, 400)
        # The code that just worked cannot be replayed.
        self.assertEqual(other_device.send("post", "/api/admin/unlock", {"password": PASSWORD, "code": code}).status_code, 400)

    @override_settings(ADMIN_REQUIRE_2FA=True)
    def test_two_factor_can_be_required(self):
        response = Client(self, self.support).send("post", "/api/admin/unlock", {"password": PASSWORD})
        self.assertEqual(response.json()["code"], "totp_setup_required")

    def test_reset_link_sets_a_new_password_once(self):
        victim_session = Client(self, self.learner)
        support = Client(self, self.support)
        support.unlock()
        url = support.send("post", f"/api/admin/users/{self.learner.pk}/reset-link").json()["url"]
        token = url.split("token=")[1]
        reset = lambda: self.client.post("/api/auth/password-reset", data=json.dumps({"token": token, "new_password": "Brand-New-Passphrase1"}), content_type="application/json")
        self.assertEqual(reset().status_code, 200)
        self.assertEqual(reset().status_code, 400)  # single use
        self.learner.refresh_from_db()
        self.assertTrue(self.learner.check_password("Brand-New-Passphrase1"))
        self.assertEqual(victim_session.get("/api/auth/me").status_code, 401)

    def test_reports_and_hiding_a_post(self):
        author = make_user("author@example.test")
        StartupProfile.objects.create(user=author, name="Loud Co", public_visible=True, onboarding_completed=True)
        StartupProfile.objects.create(user=self.learner, name="Quiet Co", public_visible=True, onboarding_completed=True)
        post = BusinessPost.objects.create(user=author, title="Buy followers", text="cheap")
        learner = Client(self, self.learner)
        self.assertEqual(learner.send("post", "/api/reports", {"target_type": "post", "target_id": str(post.pk), "reason": "spam"}).status_code, 201)
        self.assertEqual(learner.send("post", "/api/reports", {"target_type": "post", "target_id": str(post.pk), "reason": "spam"}).status_code, 201)
        self.assertEqual(Report.objects.count(), 1)  # one open report per person and target
        self.assertEqual(learner.send("post", "/api/reports", {"target_type": "post", "target_id": str(uuid.uuid4()), "reason": "spam"}).status_code, 404)

        support = Client(self, self.support)
        support.unlock()
        report = support.get("/api/admin/moderation/reports").json()["results"][0]
        done = support.send("post", f"/api/admin/moderation/reports/{report['id']}", {"status": "resolved", "action": "hide_post", "note": "Spam"})
        self.assertEqual(done.json()["status"], "resolved")
        feed = [p["title"] for p in learner.get("/api/startup/network/posts").json()["posts"]]
        self.assertNotIn("Buy followers", feed)
        own = Client(self, author).get("/api/startup/network/posts").json()["posts"]
        self.assertTrue(own[0]["hidden"])

    def test_content_import_previews_then_updates_in_place(self):
        unit = Unit.objects.create(code="01", slug="basics", title="Basics", order=1)
        kept = Lesson.objects.create(unit=unit, slug="old", title="Old lesson", order=1)
        LessonProgress.objects.create(user=self.learner, lesson=kept, status=LessonProgress.Status.COMPLETED)
        document = {
            "code": "01", "slug": "basics", "title": "Basics, revised", "order": 1,
            "test_questions": [{"id": "q1", "prompt": "2+2?", "choices": ["3", "4"], "answer_index": 1}],
            "lessons": [{"slug": "money", "title": "What is money", "intro": "Money stores value.", "bullets": ["Exchange"], "table": [["Role", "Example"], ["Store", "Savings"]]}],
        }
        owner = Client(self, self.owner)
        owner.unlock()
        preview = owner.send("post", "/api/admin/content/import", {"document": document, "dry_run": True}).json()
        self.assertEqual(preview["plan"][0]["action"], "update")
        self.assertTrue(preview["warnings"])  # "old" is not in the file and stays
        bad = owner.send("post", "/api/admin/content/import", {"document": {**document, "test_questions": [{"id": "q", "prompt": "?", "choices": ["a"], "answer_index": 3}]}, "dry_run": True})
        self.assertEqual(bad.status_code, 400)
        done = owner.send("post", "/api/admin/content/import", {"document": document, "dry_run": False})
        self.assertEqual(done.status_code, 200, done.content)
        unit.refresh_from_db()
        self.assertEqual(unit.title, "Basics, revised")
        self.assertEqual(list(unit.lessons.order_by("order").values_list("slug", flat=True)), ["money", "old"])
        self.assertTrue(LessonProgress.objects.filter(lesson=kept).exists())

    def test_announcements_are_safe_and_reach_the_right_people(self):
        owner = Client(self, self.owner)
        owner.unlock()
        bad = owner.send("post", "/api/admin/announcements", {"title": "Hi", "link_url": "javascript:alert(1)"})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(owner.send("post", "/api/admin/announcements", {"title": "Hi", "link_url": "/\\evil.example"}).status_code, 400)
        self.assertEqual(owner.send("post", "/api/admin/announcements", {"title": "New lessons", "link_url": "/app/lessons", "audience": "all"}).status_code, 201)
        self.assertEqual(owner.send("post", "/api/admin/announcements", {"title": "Founders only", "audience": "founders"}).status_code, 201)
        seen = [a["title"] for a in Client(self, self.learner).get("/api/announcements").json()["announcements"]]
        self.assertEqual(seen, ["New lessons"])

    def test_csv_export_neutralises_formulas(self):
        make_user("sheet@example.test", first_name="=HYPERLINK(\"http://x\")")
        owner = Client(self, self.owner)
        owner.unlock()
        text = owner.get("/api/admin/users.csv").content.decode("utf-8-sig")
        self.assertIn("'=HYPERLINK", text)

    def test_ai_can_be_paused(self):
        row = PlatformSettings.current()
        row.ai_enabled = False
        row.save()
        response = Client(self, self.learner).send("post", "/api/ai/advisor", {"question": "Hi"})
        self.assertEqual((response.status_code, response.json()["code"]), (503, "ai_paused"))

    def test_revoking_sessions_signs_the_learner_out_now(self):
        learner = Client(self, self.learner)
        RefreshToken.objects.create(user=self.learner, token_hash="x" * 64, family_id=uuid.UUID(learner.family), expires_at=timezone.now() + timedelta(days=1))
        owner = Client(self, self.owner)
        owner.unlock()
        self.assertEqual(owner.send("post", f"/api/admin/users/{self.learner.pk}/sessions/revoke").json()["sessions_revoked"], 1)
        self.assertEqual(learner.get("/api/auth/me").status_code, 401)

    def test_team_page_lists_staff_and_the_rules(self):
        support = Client(self, self.support)
        support.unlock()
        data = support.get("/api/admin/staff").json()
        self.assertEqual({row["email"] for row in data["results"]}, {"owner@example.test", "support@example.test", "analyst@example.test"})
        self.assertEqual(data["roles"], ["owner", "admin", "support", "content", "analyst"])
        self.assertEqual(data["permissions"]["users.delete"], ["owner"])
        self.assertIn("support", data["permissions"]["moderation.manage"])


class PasswordlessStaffTests(TestCase):
    """An owner who signs in only with Google has no password to confirm with:
    a sign-in from the last fifteen minutes sets up two-factor, and from then
    on the authenticator code is the proof."""

    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user(email="google-owner@example.test", password=None)
        self.owner.staff_role = "owner"
        self.owner.save(update_fields=["staff_role"])

    def _client(self, signed_in_minutes_ago):
        from accounts.views import _issue_session

        client = Client(self, self.owner)
        _, family = _issue_session(self.owner, RequestFactory().get("/"))
        RefreshToken.objects.filter(family_id=family).update(created_at=timezone.now() - timedelta(minutes=signed_in_minutes_ago))
        client.family = str(family)
        client.auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(self.owner, client.family)}
        return client

    @override_settings(ADMIN_REQUIRE_2FA=True)
    def test_setup_needs_a_fresh_sign_in_then_the_code_unlocks(self):
        stale = self._client(60)
        self.assertFalse(stale.get("/api/admin/me").json()["has_password"])
        self.assertEqual(stale.send("post", "/api/admin/totp/setup").json()["code"], "reauth_required")

        fresh = self._client(2)
        secret = fresh.send("post", "/api/admin/totp/setup").json()["secret"]
        me = fresh.send("post", "/api/admin/totp/enable", {"code": totp.now_code(secret)}).json()
        self.assertTrue(me["unlocked"])

        # Hours later, on another device: the code alone opens it, a wrong one does not.
        later = self._client(300)
        self.assertEqual(later.send("post", "/api/admin/unlock", {"code": "12345"}).status_code, 400)
        cache.clear()  # the replay guard remembers the code used for setup
        response = later.send("post", "/api/admin/unlock", {"code": totp.now_code(secret)})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["unlocked"])


class SystemAndStartupsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = make_user("owner@example.test", role="owner")
        self.support = make_user("support@example.test", role="support")
        founder = make_user("founder@example.test")
        StartupProfile.objects.create(
            user=founder, name="StudyBudget", onboarding_completed=True,
            onboarding={"location": "Uzbekistan, Tashkent", "stage": "idea", "market": "b2c", "team": "solo"},
            blocks={"enabled": ["advisor"], "analysis": "ok", "research": {"verdict": "promising", "searched": True, "competitors": [{"name": "Payme"}]}},
        )
        StartupProfile.objects.create(user=make_user("other@example.test"), name="Other")

    def test_system_checks_are_owner_and_admin_only_and_hold_no_secrets(self):
        support = Client(self, self.support)
        support.unlock()
        self.assertEqual(support.get("/api/admin/system").status_code, 403)
        owner = Client(self, self.owner)
        owner.unlock()
        response = owner.get("/api/admin/system")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        keys = {c["key"] for c in data["checks"]}
        self.assertTrue({"debug_off", "gemini", "migrations", "staff_2fa", "login_codes"} <= keys)
        self.assertEqual(data["accounts"]["staff"], 2)
        from django.conf import settings

        for secret in (settings.SECRET_KEY, settings.JWT_SIGNING_KEY):
            self.assertNotIn(secret, response.content.decode())

    def test_startups_list_filters_by_verdict_and_opens_one(self):
        support = Client(self, self.support)
        support.unlock()
        data = support.get("/api/admin/startups").json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["summary"]["verdicts"]["promising"], 1)
        only = support.get("/api/admin/startups", data={"verdict": "promising"}).json()["results"]
        self.assertEqual([r["name"] for r in only], ["StudyBudget"])
        self.assertEqual(only[0]["location"], "Uzbekistan, Tashkent")
        none = support.get("/api/admin/startups", data={"verdict": "none"}).json()["results"]
        self.assertEqual([r["name"] for r in none], ["Other"])
        detail = support.get(f"/api/admin/startups/{only[0]['id']}").json()
        self.assertEqual(detail["research"]["competitors"][0]["name"], "Payme")
        learner = Client(self, make_user("learner@example.test"))
        self.assertEqual(learner.get("/api/admin/startups").status_code, 403)
