"""The arithmetic and the safety checks behind Zinvest Copilot."""
import json
import unittest
from unittest.mock import patch

from ai_engine.gemini import GeminiResult
from copilot import ai, finance, loans


class CashForecastTests(unittest.TestCase):
    def test_a_loss_making_business_gets_a_date(self):
        r = finance.runway("21000000", {"revenue": "61000000", "expenses": "71333333"})
        self.assertEqual(r["burn"], "10333333")
        self.assertEqual(r["months"], 2.0)
        self.assertEqual(r["status"], "critical")  # under three months

    def test_a_profitable_business_never_runs_out(self):
        r = finance.runway("90000000", {"revenue": "148666667", "expenses": "124666667"})
        self.assertIsNone(r["months"])
        self.assertEqual(r["status"], "ok")


class LoanTests(unittest.TestCase):
    def test_monthly_payment(self):
        # 12 mln UZS at 24% a year over 12 months.
        self.assertEqual(finance.money(finance.annuity(12_000_000, 24, 12)), "1134715")

    def test_only_products_that_fit_are_eligible(self):
        ranked = loans.match(60_000_000, 24, "business", "equipment", 5_000_000)
        eligible = [p for p in ranked if p["eligible"]]
        self.assertTrue(eligible)
        for p in ranked:
            if p["max_amount"] and int(p["max_amount"]) < 60_000_000:
                self.assertFalse(p["eligible"])
                self.assertIn("amount_too_high", p["reasons"])

    def test_cheapest_affordable_comes_first(self):
        ranked = loans.match(50_000_000, 24, "business", "working_capital", 30_000_000)
        self.assertEqual(ranked[0]["bank"], "Hamkorbank")
        self.assertTrue(ranked[0]["affordable"])


class ForecastTests(unittest.TestCase):
    def test_twelve_months_with_the_loan(self):
        rows = finance.projection({"revenue": "100", "fixed": "40", "variable": "20"}, 0, 0, 12, {"amount": "1000", "payment": "10"})
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0]["profit"], "30")
        self.assertEqual(rows[0]["cumulative"], "1030")


class ModelOutputIsCheckedTests(unittest.TestCase):
    """The AI reads and explains; what it returns is checked before anyone sees it."""

    def answer(self, payload):
        return patch("copilot.ai.gemini.generate", return_value=GeminiResult(json.dumps(payload), "test", 1, 1))

    def test_records_read_from_text_keep_only_real_amounts(self):
        with self.answer({"entries": [
            {"type": "revenue", "category": "Bread", "amount": 46000000, "month": "2026-07"},
            {"type": "spending", "category": "Rent", "amount": -5},
            {"type": "gift", "category": "x", "amount": 1},
        ]}):
            parsed, _ = ai.parse_entries("July: bread 46 mln", "en", "UZS")
        self.assertEqual([e["category"] for e in parsed["entries"]], ["Bread"])

    def test_a_loan_the_model_made_up_is_replaced_by_a_real_one(self):
        products = loans.match(50_000_000, 24, "business", "any", 20_000_000)[:3]
        with self.answer({"choice": "imaginary-bank", "why": "x"}):
            explained, _ = ai.explain_loan({}, {}, {}, products, "en", "UZS")
        self.assertEqual(explained["choice"], products[0]["id"])


if __name__ == "__main__":
    unittest.main()
