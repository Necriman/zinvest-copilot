"""Zinvest Copilot: the AI proposes, the owner approves, the history records it."""
import json
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from accounts.jwt_utils import encode_access_token
from accounts.models import User
from ai_engine.gemini import GeminiError, GeminiResult
from ai_engine.models import AIUsageLog
from startup.models import CashFlowEntry, Employee, StartupProfile, StartupTodo

from . import finance, loans
from .models import CopilotAction

PASSWORD = "Str0ng-Passphrase!"


def model(payload):
    return patch("copilot.ai.gemini.generate", return_value=GeminiResult(json.dumps(payload), "test-model", 50, 80))


class FinanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="baker@example.test", password=PASSWORD)

    def add(self, kind, amount, month, cost="variable"):
        CashFlowEntry.objects.create(user=self.user, entry_type=kind, category="x", amount=amount, cost_type=cost, occurred_on=month)

    def test_summary_averages_the_latest_months(self):
        for m in (date(2026, 6, 5), date(2026, 7, 5), date(2026, 8, 5), date(2026, 9, 5)):
            self.add("revenue", 30_000_000, m)
            self.add("spending", 10_000_000, m, "fixed")
            self.add("spending", 8_000_000, m)
        s = finance.summary(self.user)
        self.assertEqual(s["months"], ["2026-07", "2026-08", "2026-09"])  # the last three
        self.assertEqual((s["revenue"], s["fixed"], s["variable"], s["expenses"], s["net"]),
                         ("30000000", "10000000", "8000000", "18000000", "12000000"))
        self.assertEqual(s["margin"], 40.0)

    def test_runway(self):
        losing = {"revenue": "20000000", "expenses": "30000000"}
        r = finance.runway("25000000", losing)
        self.assertEqual((r["burn"], r["months"], r["status"]), ("10000000", 2.5, "critical"))
        self.assertTrue(r["runs_out"])
        self.assertEqual(finance.runway("1", {"revenue": "5", "expenses": "3"})["status"], "ok")

    def test_annuity_and_projection(self):
        self.assertEqual(finance.money(finance.annuity(12_000_000, 24, 12)), "1134715")
        rows = finance.projection({"revenue": "100", "fixed": "40", "variable": "20"}, 0, 0, 12, {"amount": "1000", "payment": "10"})
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0]["profit"], "30")  # 100 - 40 - 20 - 10
        self.assertEqual(rows[0]["cumulative"], "1030")  # the loan arrives in month one

    def test_loan_matching(self):
        ranked = loans.match(50_000_000, 24, "business", "working_capital", 20_000_000)
        best = ranked[0]
        self.assertTrue(best["eligible"])
        self.assertEqual(best["id"], "hamkor-small-business")  # cheapest eligible
        mk = next(p for p in ranked if p["id"] == "mkbank-mahalla-business")
        self.assertFalse(mk["eligible"])
        self.assertIn("amount_too_high", mk["reasons"])
        self.assertIn("wrong_borrower", mk["reasons"])
        forms = {c["id"]: c["forms"] for c in loans.CATALOG}
        person = [p for p in loans.match(20_000_000, 24, "person", "any", 5_000_000) if p["eligible"]]
        self.assertTrue(person)
        self.assertTrue(all("person" in forms[p["id"]] for p in person))


class CopilotFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.test", password=PASSWORD)
        self.other = User.objects.create_user(email="other@example.test", password=PASSWORD)
        self.profile = StartupProfile.objects.create(
            user=self.owner, name="Non Uyi", currency="UZS", onboarding_completed=True,
            onboarding={"description": "A bakery in Chilonzor", "location": "Tashkent"},
        )
        Employee.objects.create(user=self.owner, full_name="Secret Baker", position="Head baker", salary=5_000_000)

    def call(self, method, path, data=None, user=None):
        auth = "Bearer " + encode_access_token(user or self.owner, uuid.uuid4())
        if method == "get":
            return self.client.get("/api/copilot/" + path, HTTP_AUTHORIZATION=auth)
        return getattr(self.client, method)("/api/copilot/" + path, data=json.dumps(data or {}), content_type="application/json", HTTP_AUTHORIZATION=auth)

    def decide(self, action, decision="approve", user=None):
        return self.call("post", f"actions/{action['id']}/decide", {"decision": decision}, user)

    def seed_figures(self):
        today = timezone.localdate()
        CashFlowEntry.objects.create(user=self.owner, entry_type="revenue", category="Bread", amount=40_000_000, occurred_on=today)
        CashFlowEntry.objects.create(user=self.owner, entry_type="spending", category="Rent", amount=12_000_000, cost_type="fixed", occurred_on=today)
        CashFlowEntry.objects.create(user=self.owner, entry_type="spending", category="Flour", amount=36_000_000, occurred_on=today)

    def test_text_becomes_records_only_after_approval(self):
        month = timezone.localdate().strftime("%Y-%m")
        parsed = {"entries": [
            {"type": "revenue", "category": "Хлеб", "amount": 45000000, "month": month, "note": "выручка"},
            {"type": "spending", "category": "Аренда", "amount": "8000000", "cost_type": "fixed", "month": month},
            {"type": "spending", "category": "Мука", "amount": -5, "month": month},  # dropped
            {"type": "gift", "category": "x", "amount": 1},  # dropped
            {"type": "spending", "category": "Old", "amount": 100, "month": "1999-01"},  # month out of range → this month
        ], "unclear": ["свет"]}
        with model(parsed) as gen:
            r = self.call("post", "entries", {"text": "Выручка 45 млн, аренда 8 млн", "language": "ru"})
        self.assertEqual(r.status_code, 201, r.content)
        action = r.json()["action"]
        self.assertEqual(action["status"], "pending")
        self.assertEqual(action["effects"], [{"type": "add_entries", "count": 3}])
        self.assertEqual(len(action["payload"]["entries"]), 3)
        self.assertIn("Russian", gen.call_args.args[1])
        self.assertEqual(CashFlowEntry.objects.filter(user=self.owner).count(), 0)  # nothing yet

        done = self.decide(action).json()["action"]
        self.assertEqual(done["status"], "approved")
        self.assertEqual(done["outcome"], [{"type": "added_entries", "count": 3}])
        self.assertEqual(CashFlowEntry.objects.filter(user=self.owner).count(), 3)
        self.assertEqual(self.decide(action).status_code, 409)  # decided once
        self.assertEqual(AIUsageLog.objects.filter(user=self.owner, feature="COPILOT").count(), 1)

    def test_reject_changes_nothing(self):
        with model({"entries": [{"type": "revenue", "category": "Bread", "amount": 1000000}]}):
            action = self.call("post", "entries", {"text": "bread 1 mln"}).json()["action"]
        done = self.decide(action, "reject").json()["action"]
        self.assertEqual((done["status"], done["outcome"]), ("rejected", [{"type": "nothing_changed"}]))
        self.assertEqual(CashFlowEntry.objects.filter(user=self.owner).count(), 0)

    def test_analysis_needs_figures_then_saves_and_adds_tasks(self):
        self.assertEqual(self.call("post", "analysis", {"language": "en"}).status_code, 400)
        self.seed_figures()
        report = {"headline": "Losing 8 mln a month", "health": "nonsense", "findings": [{"title": "Flour", "detail": "75% of revenue"}],
                  "actions": [{"title": "Raise bread price by 10%", "why": "+4 mln"}, {"title": "", "why": "dropped"}]}
        with model(report) as gen:
            action = self.call("post", "analysis", {"language": "en"}).json()["action"]
        prompt = gen.call_args.args[1]
        self.assertIn("40000000", prompt)
        self.assertNotIn("Secret Baker", prompt)  # titles, never names
        self.assertEqual(action["payload"]["health"], "stable")
        self.assertEqual(action["effects"], [{"type": "save_report"}, {"type": "add_tasks", "count": 1}])
        self.decide(action)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.copilot["analysis"]["headline"], "Losing 8 mln a month")
        self.assertTrue(StartupTodo.objects.filter(user=self.owner, title="Raise bread price by 10%").exists())

    def test_runway_warning_is_computed_not_guessed(self):
        self.seed_figures()
        self.assertEqual(self.call("post", "runway", {}).json()["code"], "no_cash")
        self.assertEqual(self.call("put", "settings", {"cash": "-5"}).status_code, 400)
        self.assertEqual(self.call("put", "settings", {"cash": "16000000", "business_form": "business"}).status_code, 200)
        with model({"message": "Money runs out in 2 months.", "actions": [{"title": "Cut flour waste", "impact": "-3 mln"}]}):
            action = self.call("post", "runway", {"language": "en"}).json()["action"]
        forecast = action["payload"]["forecast"]
        self.assertEqual((forecast["burn"], forecast["months"], forecast["status"]), ("8000000", 2.0, "critical"))
        self.decide(action)
        state = self.call("get", "state").json()
        self.assertEqual(state["runway"]["months"], 2.0)
        self.assertEqual(state["approved"]["runway"]["message"], "Money runs out in 2 months.")

    def test_loan_is_picked_from_the_catalogue_only(self):
        self.seed_figures()
        self.assertEqual(self.call("post", "loan", {"amount": "abc", "months": 12}).status_code, 400)
        self.assertEqual(self.call("post", "loan", {"amount": 99_000_000_000, "months": 12}).status_code, 400)
        with model({"choice": "made-up-bank", "why": "Cheapest", "steps": ["Visit"], "todo": "Apply at the bank"}):
            r = self.call("post", "loan", {"amount": 50_000_000, "months": 24, "purpose": "working_capital", "language": "en"})
        action = r.json()["action"]
        self.assertEqual(action["payload"]["chosen"]["id"], "hamkor-small-business")  # invented choice ignored
        self.assertTrue(action["payload"]["chosen"]["url"].startswith("https://"))
        self.decide(action)
        self.assertTrue(StartupTodo.objects.filter(user=self.owner, title="Apply at the bank").exists())

    def test_plan_carries_a_computed_forecast(self):
        self.seed_figures()
        with model({"title": "Non Uyi plan", "executive_summary": "Bakery", "risks": [{"risk": "Flour price", "mitigation": "Contract"}]}):
            action = self.call("post", "plan", {"language": "uz"}).json()["action"]
        self.assertEqual(len(action["payload"]["forecast"]), 12)
        self.assertEqual(action["payload"]["risks"][0]["risk"], "Flour price")
        self.decide(action)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.copilot["plan"]["title"], "Non Uyi plan")

    def test_history_and_csv(self):
        with model({"entries": [{"type": "revenue", "category": "Хлеб", "amount": 1000000}]}):
            action = self.call("post", "entries", {"text": "хлеб 1 млн"}).json()["action"]
        self.decide(action)
        actions = self.call("get", "history").json()["actions"]
        self.assertEqual([a["status"] for a in actions], ["approved"])
        csv_body = self.call("get", "history?format=csv").content.decode("utf-8")
        self.assertTrue(csv_body.startswith("﻿time,action,status"))
        self.assertIn("Added 1 income and expense records", csv_body)

    def test_each_owner_sees_and_decides_only_their_own(self):
        with model({"entries": [{"type": "revenue", "category": "Bread", "amount": 1000000}]}):
            action = self.call("post", "entries", {"text": "bread"}).json()["action"]
        self.assertEqual(self.decide(action, user=self.other).status_code, 404)
        self.assertEqual(self.call("get", "history", user=self.other).json()["actions"], [])
        self.assertEqual(CopilotAction.objects.get(pk=action["id"]).status, "pending")

    def test_ai_failures_leave_no_proposal(self):
        self.seed_figures()
        with patch("copilot.ai.gemini.generate", return_value=GeminiResult("[STUB]", "stub", 1, 1, is_stub=True)):
            self.assertEqual(self.call("post", "analysis", {}).status_code, 503)
        with patch("copilot.ai.gemini.generate", side_effect=GeminiError("down")):
            self.assertEqual(self.call("post", "analysis", {}).status_code, 502)
        self.assertFalse(CopilotAction.objects.exists())
