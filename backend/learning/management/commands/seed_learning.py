"""
Seed the 4 course units + their lessons (idempotent), and optionally a demo user
with a live current-week streak, startup profile, and cash-flow entries.

    python manage.py seed_learning
    python manage.py seed_learning --demo-user you@example.com

Dates for the demo streak/cashflow are computed relative to timezone.now(), so
the dashboard's current-week calendar and streak always look "live" — which is
why this is a management command rather than a fixture (fixtures hardcode dates).
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from learning.content import course_i18n
from learning.models import (
    DailyActivity,
    Lesson,
    LessonProgress,
    Unit,
    UserStats,
)

User = get_user_model()

FONT_H1 = "700 30px 'Plus Jakarta Sans'"
FONT_H2 = "700 20px 'Plus Jakarta Sans'"
FONT_BODY = "400 16px 'Plus Jakarta Sans'"
FONT_TABLE = "400 15px 'Plus Jakarta Sans'"
FONT_TABLE_H = "700 15px 'Plus Jakarta Sans'"
INK = "#0F172A"
MUTED = "#475569"
LINE = "#E2E8F0"
PANEL = "#F8FAFC"


def canvas(title, intro, bullets, table=None, heading=course_i18n.KEY_POINTS["en"]):
    """Build a coordinate-based Canvas payload matching CanvasWorkspace's schema."""
    elements = [
        {"type": "text", "x": 40, "y": 44, "text": title, "font": FONT_H1, "color": INK,
         "baseline": "top", "maxWidth": 720, "lineHeight": 38},
        {"type": "rect", "x": 40, "y": 96, "w": 720, "h": 2, "fill": LINE},
        {"type": "text", "x": 40, "y": 120, "text": intro, "font": FONT_BODY, "color": MUTED,
         "baseline": "top", "maxWidth": 720, "lineHeight": 26},
    ]
    y = 200
    elements.append({"type": "text", "x": 40, "y": y, "text": heading, "font": FONT_H2,
                     "color": INK, "baseline": "top"})
    y += 40
    elements.append({"type": "roundRect", "x": 40, "y": y, "w": 720, "h": 40 + 30 * len(bullets),
                     "radius": 16, "fill": PANEL, "stroke": "#CBD5E1", "lineWidth": 1})
    by = y + 22
    for b in bullets:
        elements.append({"type": "text", "x": 64, "y": by, "text": f"•  {b}", "font": FONT_BODY,
                         "color": INK, "baseline": "top", "maxWidth": 672, "lineHeight": 24})
        by += 30
    y = by + 30

    if table:
        elements.append({"type": "text", "x": 40, "y": y, "text": table["title"], "font": FONT_H2,
                         "color": INK, "baseline": "top"})
        y += 36
        elements.append({
            "type": "table", "x": 40, "y": y, "colWidths": table["colWidths"], "rowHeight": 38,
            "header": True, "rows": table["rows"], "font": FONT_TABLE, "headerFont": FONT_TABLE_H,
            "color": INK, "gridColor": LINE, "headerFill": PANEL,
        })
        y += 38 * len(table["rows"]) + 20

    return {"width": 800, "height": max(700, y + 40), "background": "#FFFFFF", "elements": elements}


def q(qid, prompt, choices, answer_index, explanation=""):
    return {"id": qid, "prompt": prompt, "choices": choices, "answer_index": answer_index,
            "explanation": explanation}


UNITS = [
    {
        "code": "01", "slug": "finance-fundamentals", "title": "Finance Fundamentals",
        "subtitle": "The core language of money", "order": 1, "accent_color": "brand", "icon": "chart",
        "test_questions": [
            q("u1q1", "What does 'net worth' equal?", ["Assets + Liabilities", "Assets − Liabilities", "Income − Expenses", "Revenue − Costs"], 1,
              "Net worth is what you own minus what you owe."),
            q("u1q2", "An emergency fund typically covers…", ["1 day of expenses", "3–6 months of expenses", "10 years of expenses", "Only rent"], 1),
            q("u1q3", "Compound interest means interest is earned on…", ["Only the principal", "Principal plus accumulated interest", "Taxes", "Nothing"], 1),
        ],
        "lessons": [
            {"slug": "what-is-money", "title": "What is money?", "coin_reward": 10,
             "canvas": canvas("What is money?", "Money is a tool for storing and exchanging value. Understanding its roles is the first step to mastery.",
                              ["A medium of exchange", "A unit of account", "A store of value"],
                              {"title": "Roles at a glance", "colWidths": [240, 480],
                               "rows": [["Role", "Example"], ["Exchange", "Buying groceries"], ["Account", "Pricing a product"], ["Store", "Savings account"]]})},
            {"slug": "assets-liabilities", "title": "Assets vs. liabilities", "coin_reward": 12,
             "canvas": canvas("Assets vs. liabilities", "Assets put money in your pocket; liabilities take it out. Net worth is the difference.",
                              ["Assets: cash, investments, property", "Liabilities: loans, credit-card debt", "Net worth = Assets − Liabilities"],
                              {"title": "Sample balance", "colWidths": [360, 360],
                               "rows": [["Assets", "Liabilities"], ["Cash $2,000", "Card $500"], ["Investments $3,000", "Loan $1,500"]]})},
            {"slug": "budgeting-basics", "title": "Budgeting basics", "coin_reward": 12,
             "canvas": canvas("Budgeting basics", "A budget is a plan for every dollar. The 50/30/20 rule is a simple starting framework.",
                              ["50% needs", "30% wants", "20% savings & debt payoff"],
                              {"title": "50 / 30 / 20 on $3,000", "colWidths": [240, 240, 240],
                               "rows": [["Needs", "Wants", "Savings"], ["$1,500", "$900", "$600"]]})},
        ],
    },
    {
        "code": "02", "slug": "investing-basics", "title": "Investing Basics",
        "subtitle": "Make your money work", "order": 2, "accent_color": "invest", "icon": "trending",
        "test_questions": [
            q("u2q1", "Diversification primarily reduces…", ["Returns", "Risk", "Taxes", "Fees"], 1),
            q("u2q2", "A stock represents…", ["A loan to a company", "Ownership in a company", "A government bond", "Cash"], 1),
            q("u2q3", "Index funds are popular because they are…", ["Actively traded", "Low-cost and diversified", "Guaranteed", "Tax-free"], 1),
        ],
        "lessons": [
            {"slug": "stocks-and-bonds", "title": "Stocks and bonds", "coin_reward": 12,
             "canvas": canvas("Stocks and bonds", "Stocks are ownership; bonds are loans. Together they form the core of most portfolios.",
                              ["Stocks: higher risk, higher potential return", "Bonds: lower risk, steadier income", "Mix depends on your goals"],
                              {"title": "Risk vs. return", "colWidths": [360, 360],
                               "rows": [["Asset", "Profile"], ["Stocks", "Growth"], ["Bonds", "Stability"]]})},
            {"slug": "diversification", "title": "Diversification", "coin_reward": 14,
             "canvas": canvas("Diversification", "Don't put all your eggs in one basket. Spreading investments lowers overall risk.",
                              ["Across asset classes", "Across sectors", "Across geographies"])},
            {"slug": "index-funds", "title": "Index funds & ETFs", "coin_reward": 14,
             "canvas": canvas("Index funds & ETFs", "Index funds track a market and keep costs low — a favorite of long-term investors.",
                              ["Broad diversification instantly", "Low fees compound over time", "Passive, hands-off approach"])},
            {"slug": "risk-and-return", "title": "Risk and return", "coin_reward": 16,
             "canvas": canvas("Risk and return", "Higher expected returns come with wider swings along the way. The goal isn't to avoid risk — it's to take only the risk you get paid for.",
                              ["Volatility is the price of higher returns", "Diversifiable risk earns no extra premium", "Match risk to your time horizon"],
                              {"title": "Long-run U.S. averages", "colWidths": [240, 240, 240],
                               "rows": [["Asset", "Return", "Volatility"], ["Cash", "~3%/yr", "Very low"], ["Bonds", "~5%/yr", "Low"], ["Stocks", "~10%/yr", "High"]]})},
            {"slug": "power-of-compounding", "title": "The power of compounding", "coin_reward": 16,
             "canvas": canvas("The power of compounding", "Compounding is when your returns start earning returns. Given enough time it contributes more than the money you put in.",
                              ["Growth accelerates the longer you stay invested", "Rule of 72: 72 ÷ rate ≈ years to double", "Reinvest dividends and interest automatically"])},
        ],
    },
    {
        "code": "03", "slug": "financial-analysis", "title": "Financial Analysis",
        "subtitle": "Read the numbers", "order": 3, "accent_color": "risk", "icon": "target",
        "test_questions": [
            q("u3q1", "The income statement shows…", ["Assets and liabilities", "Revenue and expenses over time", "Only cash", "Owner names"], 1),
            q("u3q2", "Gross margin equals…", ["Revenue − COGS, ÷ Revenue", "Revenue + COGS", "Net income × 2", "Cash ÷ Debt"], 0),
            q("u3q3", "Runway measures…", ["Total revenue", "Months until cash runs out", "Number of employees", "Profit margin"], 1),
        ],
        "lessons": [
            {"slug": "the-three-statements", "title": "The three statements", "coin_reward": 14,
             "canvas": canvas("The three statements", "Income statement, balance sheet, and cash-flow statement together tell a company's story.",
                              ["Income: profitability", "Balance sheet: financial position", "Cash flow: liquidity"],
                              {"title": "What each answers", "colWidths": [280, 440],
                               "rows": [["Statement", "Question"], ["Income", "Are we profitable?"], ["Balance", "What do we own/owe?"], ["Cash flow", "Are we liquid?"]]})},
            {"slug": "key-ratios", "title": "Key ratios", "coin_reward": 16,
             "canvas": canvas("Key ratios", "Ratios turn raw numbers into insight. A few core ratios reveal health quickly.",
                              ["Gross margin", "Current ratio", "Debt-to-equity"])},
            {"slug": "runway-and-burn", "title": "Runway & burn", "coin_reward": 16,
             "canvas": canvas("Runway & burn", "Burn is how fast you spend cash; runway is how long until it's gone.",
                              ["Burn = monthly net cash out", "Runway = cash ÷ burn", "Extend runway by cutting burn or raising revenue"],
                              {"title": "Example", "colWidths": [360, 360],
                               "rows": [["Metric", "Value"], ["Cash", "$60,000"], ["Burn/mo", "$10,000"], ["Runway", "6 months"]]})},
            {"slug": "unit-economics", "title": "Unit economics", "coin_reward": 18,
             "canvas": canvas("Unit economics", "Unit economics zoom in on a single customer or product to ask whether growth actually creates value or just burns cash faster.",
                              ["Contribution margin = price − variable cost", "CAC is what it costs to win one customer", "Aim for an LTV:CAC of 3:1 or better"],
                              {"title": "Per-customer example", "colWidths": [360, 360],
                               "rows": [["Metric", "Value"], ["Price / mo", "$50"], ["Variable cost / mo", "$15"], ["CAC", "$210"], ["Payback", "6 months"]]})},
        ],
    },
    {
        "code": "04", "slug": "personal-finance-wealth", "title": "Personal Finance & Wealth",
        "subtitle": "Build lasting wealth", "order": 4, "accent_color": "budget", "icon": "wallet",
        "test_questions": [
            q("u4q1", "Paying yourself first means…", ["Spending then saving", "Saving before spending", "Never saving", "Only paying bills"], 1),
            q("u4q2", "A higher credit score usually leads to…", ["Higher interest rates", "Lower interest rates", "No effect", "More debt"], 1),
            q("u4q3", "The main benefit of starting to invest early is…", ["Luck", "More time for compounding", "Guaranteed returns", "Lower taxes only"], 1),
        ],
        "lessons": [
            {"slug": "pay-yourself-first", "title": "Pay yourself first", "coin_reward": 14,
             "canvas": canvas("Pay yourself first", "Automate savings before you spend. What you don't see, you won't miss.",
                              ["Automate a transfer on payday", "Treat savings like a bill", "Increase the rate over time"])},
            {"slug": "credit-and-debt", "title": "Credit & debt", "coin_reward": 16,
             "canvas": canvas("Credit & debt", "Good credit lowers your cost of borrowing. Manage debt deliberately.",
                              ["Pay on time, every time", "Keep utilization low", "Attack high-interest debt first"])},
            {"slug": "long-term-wealth", "title": "Long-term wealth", "coin_reward": 18,
             "canvas": canvas("Long-term wealth", "Time in the market beats timing the market. Start early and stay consistent.",
                              ["Invest consistently", "Reinvest returns", "Let compounding work for decades"],
                              {"title": "Compounding $200/mo at 7%", "colWidths": [240, 480],
                               "rows": [["Years", "Approx. value"], ["10", "$34,000"], ["20", "$104,000"], ["30", "$243,000"]]})},
            {"slug": "emergency-fund", "title": "Emergency funds", "coin_reward": 18,
             "canvas": canvas("Emergency funds", "An emergency fund is cash set aside for the unexpected. It keeps a surprise bill from turning into high-interest debt.",
                              ["Target 3–6 months of essential expenses", "Keep it liquid — savings, not stocks", "Refill it before resuming other goals"])},
            {"slug": "debt-payoff-strategies", "title": "Debt payoff strategies", "coin_reward": 20,
             "canvas": canvas("Debt payoff strategies", "Two proven methods: the avalanche minimizes interest paid, the snowball builds momentum. The best one is the one you'll actually finish.",
                              ["Avalanche: highest interest rate first", "Snowball: smallest balance first", "Always cover every minimum payment"],
                              {"title": "Avalanche vs. snowball", "colWidths": [240, 240, 240],
                               "rows": [["Method", "Order by", "Wins on"], ["Avalanche", "Highest rate", "Total interest"], ["Snowball", "Smallest balance", "Motivation"]]})},
            {"slug": "retirement-accounts", "title": "Retirement accounts", "coin_reward": 20,
             "canvas": canvas("Retirement accounts", "Tax-advantaged accounts let investments grow without the yearly drag of taxes. The account is the wrapper — the investments go inside it.",
                              ["401(k): pre-tax now, taxed at withdrawal", "Roth IRA: taxed now, withdrawals tax-free", "Capture the full employer match first"])},
        ],
    },
]


def _english_table(payload):
    return next((el for el in (payload or {}).get("elements", []) if el.get("type") == "table"), None)


def unit_i18n(u):
    """Unit.i18n from course_i18n, checked against the English test."""
    out = {}
    ids = [q["id"] for q in u["test_questions"]]
    for lang, words in course_i18n.UNITS.get(u["code"], {}).items():
        for question in words.get("test_questions", []):
            english = next((q for q in u["test_questions"] if q["id"] == question["id"]), None)
            if english is None or len(question["choices"]) != len(english["choices"]):
                raise CommandError(f"unit {u['code']} ({lang}): {question['id']} does not match the English test")
        if [q["id"] for q in words.get("test_questions", [])] != ids:
            raise CommandError(f"unit {u['code']} ({lang}): translate every test question, in order")
        out[lang] = words
    return out


def lesson_i18n(les):
    """Lesson.i18n from course_i18n: the lesson rebuilt in each language on the English layout."""
    out = {}
    table = _english_table(les["canvas"])
    for lang, words in course_i18n.LESSONS.get(les["slug"], {}).items():
        translated_table = None
        if table:
            if "table" not in words or [len(r) for r in words["table"]["rows"]] != [len(r) for r in table["rows"]]:
                raise CommandError(f"lesson {les['slug']} ({lang}): the table must match the English one")
            translated_table = {"title": words["table"]["title"], "colWidths": table["colWidths"], "rows": words["table"]["rows"]}
        out[lang] = {
            "title": words["title"],
            "canvas_payload": canvas(words["title"], words["intro"], words["bullets"], translated_table,
                                     heading=course_i18n.KEY_POINTS[lang]),
        }
    return out


class Command(BaseCommand):
    help = "Seed the 4 course units + lessons, and optionally a demo user's progress."

    def add_arguments(self, parser):
        parser.add_argument("--demo-user", type=str, default=None,
                            help="Email of a user to seed with a live streak + startup demo data.")
        parser.add_argument("--legacy", action="store_true",
                            help="Write the old four demo units even over an imported course.")

    @transaction.atomic
    def handle(self, *args, **options):
        # The real course comes from the unit files (manage.py import_units).
        # Over it, these four demo units would bring the old lessons back.
        if Lesson.objects.exclude(content_html="").exists() and not options.get("legacy"):
            self.stdout.write(self.style.WARNING(
                "The course is imported from learning/content/units (import_units): demo units skipped."))
            if options.get("demo_user"):
                self._seed_demo_user(options["demo_user"])
            return
        for u in UNITS:
            unit, _ = Unit.objects.update_or_create(
                code=u["code"],
                defaults={
                    "slug": u["slug"], "title": u["title"], "subtitle": u["subtitle"],
                    "order": u["order"], "accent_color": u["accent_color"], "icon": u["icon"],
                    "test_questions": u["test_questions"], "test_pass_threshold": 0.7,
                    "i18n": unit_i18n(u),
                },
            )
            for i, les in enumerate(u["lessons"], start=1):
                Lesson.objects.update_or_create(
                    unit=unit, slug=les["slug"],
                    defaults={"title": les["title"], "order": i,
                              "coin_reward": les["coin_reward"], "canvas_payload": les["canvas"],
                              "i18n": lesson_i18n(les)},
                )
        missing = [les["slug"] for u in UNITS for les in u["lessons"] if les["slug"] not in course_i18n.LESSONS]
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Unit.objects.count()} units / {Lesson.objects.count()} lessons"
            f" (ru/uz translations: {Lesson.objects.count() - len(missing)} lessons)."))
        if missing:
            self.stdout.write(self.style.WARNING(f"Not translated yet: {', '.join(missing)}"))

        email = options.get("demo_user")
        if email:
            self._seed_demo_user(email)

    def _seed_demo_user(self, email):
        try:
            user = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"No user with email {email!r}. Create it first."))
            return

        today = timezone.localdate()
        now = timezone.now()

        # Live current-week streak: activity for the last 3 days (incl. today).
        for delta in range(3):
            DailyActivity.objects.get_or_create(user=user, date=today - timedelta(days=delta))

        stats, _ = UserStats.objects.get_or_create(user=user)
        stats.coins = 80
        stats.day_streak = 1
        stats.longest_streak = max(stats.longest_streak, 3)
        stats.last_activity_date = today
        stats.weekly_xp = 80
        stats.financial_goal = "Reach financial independence"
        stats.target_score = 90
        stats.save()

        # Complete the first lesson of unit 1 so progress isn't all zeros.
        first_lesson = Lesson.objects.filter(unit__code="01", order=1).first()
        if first_lesson:
            LessonProgress.objects.update_or_create(
                user=user, lesson=first_lesson,
                defaults={"status": LessonProgress.Status.COMPLETED, "completed_at": now},
            )

        # Startup demo data (imported here so learning stays decoupled from startup).
        from startup.models import CashFlowEntry, StartupProfile

        StartupProfile.objects.update_or_create(
            user=user, defaults={"name": "Zinvest Labs", "industry": "EdTech", "currency": "USD"}
        )
        CashFlowEntry.objects.get_or_create(
            user=user, entry_type=CashFlowEntry.Type.REVENUE, category="Subscriptions",
            defaults={"amount": "1200.00", "occurred_on": today - timedelta(days=2),
                      "description": "Monthly plans"},
        )
        CashFlowEntry.objects.get_or_create(
            user=user, entry_type=CashFlowEntry.Type.SPENDING, category="Hosting",
            defaults={"amount": "300.00", "occurred_on": today - timedelta(days=1),
                      "description": "Cloud infra"},
        )
        self.stdout.write(self.style.SUCCESS(f"Seeded demo data for {email}."))
