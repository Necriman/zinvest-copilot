"""The AI roadmap (questions → the road to a full startup, walked in order) and the employee card's job title."""
import json
import uuid
from unittest.mock import patch

from django.test import TestCase

from accounts.jwt_utils import encode_access_token
from accounts.models import User
from ai_engine.gemini import GeminiError, GeminiResult
from ai_engine.models import AIUsageLog

from .models import CashFlowEntry, Employee, StartupProfile

QUESTIONS = {
    "questions": [
        {"id": "Has MVP?", "text": "Do you have a working MVP?", "why": "It decides the first phase.",
         "options": ["No, just the idea", "A prototype", "Yes, live", "Yes, and people pay"]},
        {"id": "hours", "text": "How many hours a week can you give?", "options": [], "placeholder": "e.g. 20"},
        {"id": "empty", "text": ""},
        {"id": "hours", "text": "Duplicate id"},
    ]
}

ROADMAP = {
    "position": {
        "stage": "mvp",
        "headline": "Bot built, no paying users yet",
        "summary": "Revenue is 0 against 1 200.00 a month of payroll.",
        "strengths": ["A working prototype"],
        "gaps": ["No price tested", "No demand data"],
        "focus": "Get ten people to pay.",
    },
    "phases": [
        {"title": "Idea", "already_done": True, "milestone": {"title": "Problem confirmed"},
         "steps": [{"title": "ignored for a phase already behind"}]},
        {
            "title": "Prove demand",
            "horizon": "Weeks 1-2",
            "goal": "Ten paying users.",
            "milestone": {"title": "10 paying users", "criteria": "10 payments received"},
            "steps": [
                {"title": "Interview 15 students in Tashkent", "why": "No demand data yet.",
                 "how": ["Post in two university chats", "Ask how they track debts now"],
                 "metric": "15 interviews written up", "area": "customers"},
                {"title": "", "why": "dropped: no title"},
                {"title": "Test a 15 000 UZS price", "why": "Price untested.", "how": "not a list",
                 "metric": "5 payments", "area": "astrology"},
            ],
        },
        {"title": "No steps, dropped", "milestone": {"title": "x"}, "steps": []},
        {"title": "Grow", "horizon": "Month 2", "goal": "50 users.", "milestone": {"title": "50 users"}, "steps": [
            {"title": "Launch a referral offer", "why": "Word of mouth.", "how": ["One free month per friend"],
             "metric": "20 referrals", "area": "marketing"},
        ]},
    ],
}


class RoadmapTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.test", password="Str0ng-Passphrase!")
        self.other = User.objects.create_user(email="other@example.test", password="Str0ng-Passphrase!")
        self.profile = StartupProfile.objects.create(
            user=self.owner, name="Qarz", onboarding_completed=True,
            onboarding={"name": "Qarz", "location": "Tashkent", "stage": "mvp"},
            blocks={"enabled": ["employees", "advisor", "finance"], "offered": ["matches"],
                    "research": {"verdict": "promising", "summary": "Room for it.", "sources": [{"url": "https://x"}]}},
        )
        StartupProfile.objects.create(user=self.other, name="Other", onboarding_completed=True)
        Employee.objects.create(user=self.owner, full_name="Secret Person", position="CTO",
                                role="Builds the bot", salary="1200")
        CashFlowEntry.objects.create(user=self.owner, entry_type="spending", category="Servers", amount="80")

    def call(self, method, path, data=None, user=None):
        auth = "Bearer " + encode_access_token(user or self.owner, uuid.uuid4())
        if method == "get":
            return self.client.get("/api/startup/" + path, HTTP_AUTHORIZATION=auth)
        return getattr(self.client, method)(
            "/api/startup/" + path, data=json.dumps({} if data is None else data), content_type="application/json",
            HTTP_AUTHORIZATION=auth,
        )

    def model(self, payload):
        return patch("startup.roadmap.gemini.generate", return_value=GeminiResult(json.dumps(payload), "test-model", 100, 200))

    def build(self, payload=ROADMAP, answers=None):
        body = {"language": "ru"}
        if answers is not None:
            body["answers"] = answers
        with self.model(payload) as gen:
            response = self.call("post", "roadmap", body)
        return response, gen

    def items(self, plan):
        return [item for phase in plan["phases"] for item in phase["steps"] + [phase]]

    def tick(self, item, done=True, note=None):
        body = {"done": done} if note is None else {"done": done, "note": note}
        return self.call("patch", f"roadmap/items/{item['id']}", body)

    def test_empty_until_built(self):
        self.assertIsNone(self.call("get", "roadmap").json()["roadmap"])

    def test_a_roadmap_from_before_milestones_is_rebuilt_keeping_its_progress(self):
        self.profile.roadmap = {"phases": [{"title": "Old", "steps": [
            {"id": "a1", "title": "Interview 15 students in Tashkent", "done": True, "done_at": "2026-10-10T10:00:00+00:00"}]}]}
        self.profile.save()
        self.assertIsNone(self.call("get", "roadmap").json()["roadmap"])
        plan = self.build()[0].json()["roadmap"]
        self.assertTrue(plan["phases"][1]["steps"][0]["done"])

    def test_needs_the_intake_first(self):
        self.profile.onboarding_completed = False
        self.profile.save()
        with patch("startup.roadmap.gemini.generate") as gen:
            self.assertEqual(self.call("post", "roadmap/questions", {"language": "ru"}).status_code, 400)
            self.assertEqual(self.call("post", "roadmap", {"language": "ru"}).status_code, 400)
        gen.assert_not_called()

    def test_questions_are_shaped(self):
        with self.model(QUESTIONS) as gen:
            response = self.call("post", "roadmap/questions", {"language": "ru"})
        self.assertEqual(response.status_code, 200)
        questions = response.json()["questions"]
        self.assertEqual([q["id"] for q in questions], ["hasmvp", "hours"])  # cleaned key; empty and duplicate dropped
        self.assertEqual(len(questions[0]["options"]), 4)
        self.assertEqual(questions[1]["options"], [])
        self.assertIn("only about the facts above that the", gen.call_args.args[1])
        self.assertEqual(AIUsageLog.objects.filter(user=self.owner, feature="ROADMAP").count(), 1)

    def test_no_questions_when_the_snapshot_is_enough(self):
        with self.model({"questions": []}):
            self.assertEqual(self.call("post", "roadmap/questions", {"language": "en"}).json()["questions"], [])

    def test_build_shapes_and_stores_the_road(self):
        answers = [{"question": "Do you have a working MVP?", "answer": "A prototype"}, {"question": "", "answer": "x"}]
        response, gen = self.build(answers=answers)
        self.assertEqual(response.status_code, 200)
        plan = response.json()["roadmap"]
        self.assertEqual(plan["position"]["stage"], "mvp")
        self.assertEqual(plan["language"], "ru")
        self.assertEqual(plan["answers"], [answers[0]])
        # The phase without steps is dropped; the phase behind keeps no steps and is done.
        self.assertEqual([p["title"] for p in plan["phases"]], ["Idea", "Prove demand", "Grow"])
        behind, ahead = plan["phases"][0], plan["phases"][1]
        self.assertTrue(behind["already_done"] and behind["done"])
        self.assertEqual(behind["steps"], [])
        self.assertEqual(ahead["milestone"], {"title": "10 paying users", "criteria": "10 payments received"})
        self.assertEqual([s["title"] for s in ahead["steps"]], ["Interview 15 students in Tashkent", "Test a 15 000 UZS price"])
        self.assertEqual(ahead["steps"][1]["area"], "operations")  # unknown area
        self.assertEqual(ahead["steps"][1]["how"], [])  # not a list
        self.assertFalse(ahead["done"])
        self.assertIsNone(plan["completed_at"])
        # The founder's answers reach the model.
        self.assertIn("A prototype", gen.call_args.args[1])
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.roadmap["phases"][2]["steps"][0]["title"], "Launch a referral offer")
        self.assertIsNotNone(response.json()["quota"])

    def test_rebuild_reuses_the_stored_answers(self):
        self.build(answers=[{"question": "MVP?", "answer": "Live since May"}])
        _, gen = self.build()
        self.assertIn("Live since May", gen.call_args.args[1])

    def test_the_model_reads_the_startup_but_not_names(self):
        _, gen = self.build()
        prompt = gen.call_args.args[1]
        self.assertIn('"title": "CTO"', prompt)
        self.assertIn("1200.00", prompt)  # payroll
        self.assertIn("80.00", prompt)  # spending
        self.assertIn("Room for it.", prompt)  # market check
        self.assertNotIn("Secret Person", prompt)
        self.assertNotIn("https://x", prompt)  # research sources stay out
        self.assertIn("Russian", prompt)

    def test_walked_in_order_to_a_full_startup(self):
        plan = self.build()[0].json()["roadmap"]
        items = self.items(plan)
        open_items = [i for i in items if not i.get("already_done")]
        # Only the next item can be finished.
        self.assertEqual(self.tick(open_items[1]).status_code, 409)
        self.assertEqual(self.tick(open_items[0], note="Talked to 16").status_code, 200)
        # Only the latest finished item can be reopened; the phase behind never.
        self.assertEqual(self.tick(items[0], done=False).status_code, 409)
        reopened = self.tick(open_items[0], done=False)
        self.assertEqual(reopened.status_code, 200)
        for item in open_items[:-1]:
            self.assertEqual(self.tick(item).status_code, 200, item.get("title"))
        last = self.tick(open_items[-1]).json()["roadmap"]
        self.assertTrue(all(i["done"] for i in self.items(last)))
        self.assertTrue(last["completed_at"])
        self.assertEqual(last["phases"][1]["steps"][0]["note"], "Talked to 16")

    def test_progress_survives_a_rebuild(self):
        plan = self.build()[0].json()["roadmap"]
        ahead = plan["phases"][1]
        self.tick(ahead["steps"][0], note="16 interviews")
        self.tick(ahead["steps"][1])
        saved = self.tick(ahead).json()["roadmap"]["phases"][1]  # milestone reached
        self.assertTrue(saved["done"])

        again = json.loads(json.dumps(ROADMAP))
        again["phases"][1]["steps"][0]["title"] = "  interview 15 STUDENTS in Tashkent "
        again["phases"][1]["steps"][1]["title"] = "Something new"
        response, gen = self.build(again)
        self.assertIn("16 interviews", gen.call_args.args[1])  # told what is done, with the note
        phase = response.json()["roadmap"]["phases"][1]
        self.assertTrue(phase["steps"][0]["done"])
        self.assertEqual(phase["steps"][0]["note"], "16 interviews")
        self.assertFalse(phase["steps"][1]["done"])
        # The milestone was reached before, but the run is broken by the new step.
        self.assertFalse(phase["done"])

    def test_items_belong_to_their_founder(self):
        step = self.build()[0].json()["roadmap"]["phases"][1]["steps"][0]
        self.assertEqual(self.tick(step).status_code, 200)
        self.assertEqual(self.call("patch", f"roadmap/items/{step['id']}", {"done": False}, user=self.other).status_code, 404)
        self.assertEqual(self.call("patch", f"roadmap/items/{step['id']}", {"done": "yes"}).status_code, 400)
        self.assertEqual(self.call("patch", "roadmap/items/nope", {"done": True}).status_code, 404)

    def test_failures_keep_the_old_roadmap(self):
        self.build()
        before = StartupProfile.objects.get(pk=self.profile.pk).roadmap
        stub = GeminiResult("[STUB]", "stub", 1, 1, is_stub=True)
        with patch("startup.roadmap.gemini.generate", return_value=stub):
            self.assertEqual(self.call("post", "roadmap", {"language": "en"}).status_code, 503)
            self.assertEqual(self.call("post", "roadmap/questions", {"language": "en"}).status_code, 503)
        with patch("startup.roadmap.gemini.generate", side_effect=GeminiError("down")):
            self.assertEqual(self.call("post", "roadmap", {"language": "en"}).status_code, 502)
        with patch("startup.roadmap.gemini.generate", return_value=GeminiResult("not json", "m", 1, 1)):
            self.assertEqual(self.call("post", "roadmap", {"language": "en"}).status_code, 502)
        only_behind = {"position": {}, "phases": [ROADMAP["phases"][0]]}
        with self.model(only_behind):
            self.assertEqual(self.call("post", "roadmap", {"language": "en"}).status_code, 502)
        self.assertEqual(StartupProfile.objects.get(pk=self.profile.pk).roadmap, before)

    def test_the_advice_is_grounded_in_the_playbook_and_real_cases(self):
        picked = [{"name": "DoorDash", "stage": "validation", "story": "Delivered by hand.", "lesson": "Concierge."},
                  {"name": "Zappos", "stage": "idea", "story": "Bought shoes per order.", "lesson": "Test first."}]
        payload = json.loads(json.dumps(ROADMAP))
        payload["phases"][1]["stage"] = "validation"
        steps = payload["phases"][1]["steps"]
        steps[0]["case"] = {"name": "doordash", "what_they_did": "Доставляли сами.", "apply": "Возите сами."}
        steps[0]["pitfall"] = "Building the app first."
        steps[2]["case"] = {"name": "Made Up Inc", "what_they_did": "x", "apply": "y"}  # not a picked case
        payload["phases"][3]["steps"][0]["case"] = {"name": "DoorDash", "what_they_did": "again", "apply": "z"}  # used twice
        with patch("startup.roadmap.playbook.pick_cases", return_value=picked):
            response, gen = self.build(payload)
        prompt = gen.call_args.args[1]
        self.assertIn("Exit criteria", prompt)  # the playbook
        self.assertIn("Mom Test", prompt)
        self.assertIn("DoorDash (validation): Delivered by hand.", prompt)  # the picked cases
        self.assertIn("my.gov.uz", prompt)  # local context
        plan = response.json()["roadmap"]
        ahead = plan["phases"][1]
        self.assertEqual(ahead["stage"], "validation")
        self.assertEqual(ahead["steps"][0]["case"], {"name": "DoorDash", "what_they_did": "Доставляли сами.", "apply": "Возите сами."})
        self.assertEqual(ahead["steps"][0]["pitfall"], "Building the app first.")
        self.assertIsNone(ahead["steps"][1]["case"])  # invented name dropped
        self.assertIsNone(plan["phases"][2]["steps"][0]["case"])  # each case once

    def test_existing_workspaces_get_the_block_once(self):
        enabled = self.call("get", "profile").json()["blocks"]["enabled"]
        self.assertEqual(enabled[enabled.index("advisor") + 1], "roadmap")
        hidden = [k for k in enabled if k != "roadmap"]
        self.call("put", "profile", {"blocks": hidden})
        self.assertNotIn("roadmap", self.call("get", "profile").json()["blocks"]["enabled"])


class EmployeePositionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.test", password="Str0ng-Passphrase!")

    def call(self, method, path, data):
        return getattr(self.client, method)(
            "/api/startup/" + path, data=json.dumps(data), content_type="application/json",
            HTTP_AUTHORIZATION="Bearer " + encode_access_token(self.owner, uuid.uuid4()),
        )

    def test_position_is_saved_updated_and_imported(self):
        r = self.call("post", "employees", {"full_name": "Aziza Karimova", "position": "  Head chef ", "role": "Runs the kitchen"})
        self.assertEqual(r.status_code, 201)
        emp = r.json()["employee"]
        self.assertEqual((emp["position"], emp["role"]), ("Head chef", "Runs the kitchen"))
        updated = self.call("put", f"employees/{emp['id']}", {"position": "C" * 200}).json()["employee"]
        self.assertEqual(len(updated["position"]), 80)
        imported = self.call("post", "employees/import", {"rows": [{"full_name": "Bekzod", "position": "Courier"}]})
        self.assertEqual(imported.status_code, 201)
        self.assertEqual(Employee.objects.get(full_name="Bekzod").position, "Courier")


class PlaybookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="cook@example.test", password="Str0ng-Passphrase!")

    def profile(self, **onboarding):
        return StartupProfile.objects.create(user=self.user, onboarding=onboarding)

    def test_cases_are_picked_for_the_startup(self):
        from .playbook import CASES, PLAYBOOK, pick_cases

        food = self.profile(stage="operational", market="b2c", description="Lunch delivery to offices in Tashkent")
        names = [c["name"] for c in pick_cases(food)]
        self.assertEqual(len(names), 8)
        self.assertIn("DoorDash", names)
        self.assertTrue({"Careem", "Gojek", "Uzum"} & set(names))
        # Every case is complete and sits on a playbook stage.
        stages = {p["stage"] for p in PLAYBOOK}
        for name, tags, stage, story, lesson in CASES:
            self.assertIn(stage, stages, name)
            self.assertTrue(tags and story and lesson, name)

    def test_cases_follow_the_stage(self):
        from .playbook import pick_cases

        tutors = StartupProfile.objects.create(
            user=User.objects.create_user(email="tutor@example.test", password="Str0ng-Passphrase!"),
            onboarding={"stage": "idea", "market": "b2c", "description": "Репетиторы по математике для школьников"},
        )
        picked = pick_cases(tutors)
        self.assertTrue(any(c["stage"] in ("idea", "validation") for c in picked[-2:]))
        self.assertIn("Canva", [c["name"] for c in picked])  # education, proven in a niche first
