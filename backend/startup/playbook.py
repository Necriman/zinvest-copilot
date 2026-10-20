"""
What the roadmap AI knows about building startups, so its advice comes from
how startups actually grew rather than from generic business vocabulary.

PLAYBOOK is the road in stages, each with the exit criteria (with numbers)
that show a stage is really done, the tactics that are known to work there,
and the mistakes founders make there. It follows the standard practice of
the field: customer-development interviews ("The Mom Test"), concierge and
Wizard-of-Oz MVPs, founder-led sales, Sean Ellis's product-market-fit survey,
retention cohorts, unit economics (LTV/CAC, payback) and channel testing.

CASES are short, well-documented stories of real startups at the stage they
illustrate. The roadmap shows only cases picked from this list (by name), so
the stories the founder reads are the ones written here, not invented ones.
`pick_cases` chooses the ones closest to a given startup.

Kept in English: it is read by the model, which writes in the founder's language.
"""
import re

LOCAL = """Local context (Uzbekistan and Central Asia):
- Customers are reached through Telegram (channels, groups, bots), Instagram,
  OLX.uz classifieds, and word of mouth in the neighbourhood (mahalla), school
  or office. A Telegram bot or channel is usually a faster MVP than an app.
- People pay with Click, Payme, Uzum and Humo/Uzcard cards, and still often
  in cash: cash on delivery and paying after the first result build trust.
- A founder can register as an individual entrepreneur or an LLC online
  (my.gov.uz); IT companies can apply for IT Park residency, which has tax
  benefits. Terms change, so a step should say to check the current rules.
- Trust is the main barrier to buying from someone new: reviews, guarantees,
  a real phone number and meeting in person matter more than in the US."""

PLAYBOOK = [
    {
        "stage": "idea",
        "goal": "Prove the problem is real, frequent and painful for a specific group of people.",
        "exit": [
            "15-30 problem interviews with the target customer (not friends), about past behaviour",
            "at least half describe the problem unprompted and already spend money or time on a workaround",
            "one sentence: who exactly the customer is and what they do today instead",
        ],
        "tactics": [
            "Mom Test interviews: ask what happened the last time, what they did, what it cost; never 'would you use it?'",
            "find customers where they already gather: Telegram groups, parents' chats, markets, office lobbies",
            "smoke test: a landing page or Telegram channel with the offer and a sign-up or pre-order button",
            "ask for a commitment: a deposit, a pre-order or a time slot is a signal, a compliment is not",
        ],
        "mistakes": [
            "building or ordering an app before talking to customers",
            "asking friends and family, or running surveys instead of conversations",
            "researching competitors for weeks instead of talking to customers",
        ],
    },
    {
        "stage": "validation",
        "goal": "Deliver the solution by hand to a few real customers and get paid for it.",
        "exit": [
            "a concierge or no-code version delivers the core value to 5-10 real customers",
            "3-5 customers have paid (or paid a deposit) at a real price",
            "the founder can list what customers actually use and what they ignore",
        ],
        "tactics": [
            "concierge MVP: do the service manually behind a simple front (Telegram bot, Google Form, phone)",
            "Wizard-of-Oz: the customer sees a product, the founder does the work behind it",
            "charge from the first customer, even a small amount; free users do not prove demand",
            "launch densely in one small place (one district, one school, one office centre) not the whole city",
        ],
        "mistakes": [
            "writing a technical specification and hiring developers before anyone has paid",
            "making it free to get users",
            "spreading the first customers across the whole city or country",
        ],
    },
    {
        "stage": "mvp",
        "goal": "Turn what worked by hand into the smallest product that delivers the core value repeatedly.",
        "exit": [
            "an MVP built in 2-6 weeks around one core use case, automating only what took the most time by hand",
            "10-30 active users who come back every week",
            "first cohort retention measured: share of users still active after 4 weeks",
        ],
        "tactics": [
            "build only the steps that were the bottleneck in the manual version; keep the rest manual",
            "onboard every early user personally and watch them use it",
            "weekly loop: talk to users, ship one change, measure",
            "no-code first (Telegram bot builders, Tilda, Google Sheets) unless the product itself is the technology",
        ],
        "mistakes": [
            "many features and perfect design before retention is proven",
            "an iOS/Android app when a bot or website would do",
            "counting sign-ups instead of weekly active users",
        ],
    },
    {
        "stage": "first_customers",
        "goal": "Get the first 20-100 paying customers through founder-led sales and keep them.",
        "exit": [
            "20-100 paying customers, most of them strangers, not the founder's network",
            "repeat purchase or subscription renewal is happening",
            "the founder knows the sales script that works and the top 3 objections",
        ],
        "tactics": [
            "founder-led sales: the founder sells personally until the script is repeatable",
            "do things that don't scale: personal onboarding, calling every customer, delivering yourself",
            "remove the main fear of buying: a guarantee, a free first session, pay after the result",
            "ask every happy customer for a referral and a review",
        ],
        "mistakes": [
            "hiring a salesperson before the founder has closed deals personally",
            "paid ads before the offer converts in direct conversations",
            "discounts to win customers instead of fixing the value",
        ],
    },
    {
        "stage": "traction",
        "goal": "Prove product-market fit and unit economics: customers stay, and each one earns more than it costs.",
        "exit": [
            "Sean Ellis test: at least 40% of active users would be 'very disappointed' without the product",
            "retention curve flattens: a stable share of each cohort keeps using or buying",
            "unit economics known: customer acquisition cost (CAC), lifetime value (LTV), margin per order; LTV at least 3 x CAC, or a positive margin on every order",
            "growth of 5-7% a week (or 20%+ a month) in revenue or active users for several months",
        ],
        "tactics": [
            "run the Sean Ellis survey and build for the users who said 'very disappointed'",
            "test 3-5 acquisition channels cheaply (Telegram ads, Instagram, partners, referrals, OLX), then double down on the one that works",
            "raise prices or cut cost per order until every order makes money",
            "weekly metrics dashboard: new customers, retention, revenue, CAC",
        ],
        "mistakes": [
            "scaling marketing while each order loses money",
            "averaging all users together instead of looking at cohorts",
            "adding new products before the core one has product-market fit",
        ],
    },
    {
        "stage": "growth",
        "goal": "Make the business run without the founder doing every job: a team, processes and a legal base.",
        "exit": [
            "a registered company with bookkeeping, contracts and taxes in order",
            "first hires do the work that took most of the founders' time, with written checklists",
            "monthly financial report and 3-6 months of runway",
        ],
        "tactics": [
            "hire for the bottleneck the founders do every day; write the checklist before hiring",
            "turn the manual playbook into simple written processes (one page each)",
            "register the right legal form before contracts and payments grow (check current rules on my.gov.uz)",
            "repeat what worked in one district/segment in the next one, with the same playbook",
        ],
        "mistakes": [
            "hiring a big team on expected, not actual, revenue",
            "raising money before traction, or giving away a large share early",
            "entering a new city before the first one is profitable",
        ],
    },
    {
        "stage": "scale",
        "goal": "A full startup: a working product, paying customers, economics that work, a team and a predictable way to grow.",
        "exit": [
            "a registered company with a product customers pay for repeatedly",
            "positive unit economics and at least one acquisition channel with predictable CAC",
            "a team beyond the founders with clear roles, and monthly reporting",
            "a plan for the next market or a round of investment backed by the numbers",
        ],
        "tactics": [
            "expand to an adjacent segment or city with the proven playbook",
            "talk to investors with metrics: growth, retention, unit economics",
            "add a second product only on top of a frequent core use",
        ],
        "mistakes": [
            "expanding to many markets at once",
            "losing the founder's contact with customers",
        ],
    },
]

FULL_STARTUP = (
    "A full startup means: a registered company, a product customers pay for repeatedly, unit economics that work, "
    "at least one predictable acquisition channel, a team beyond the founders with clear roles, and monthly financial reporting."
)

# name, tags, stage, story (what they did, verifiable), lesson
CASES = [
    ("Airbnb", {"marketplace", "travel", "b2c", "services"}, "validation",
     "In 2007 the founders rented air mattresses in their own flat during a sold-out design conference to see if strangers would pay to stay in a home. When bookings stalled they flew to New York, met hosts in person and re-photographed their listings themselves.",
     "Test demand with a manual version, then go meet your first users and fix the experience by hand."),
    ("DoorDash", {"delivery", "food", "local", "marketplace"}, "validation",
     "In 2013 Stanford students put up PaloAltoDelivery.com with PDF menus of local restaurants and a phone number; the founders took the orders and delivered the food themselves before writing dispatch software.",
     "Concierge MVP: deliver the service by hand to prove demand, automate later."),
    ("Zappos", {"ecommerce", "retail", "b2c"}, "idea",
     "In 1999 Nick Swinmurn photographed shoes in local stores and put them online; when someone ordered, he bought the pair at full price and shipped it, proving people would buy shoes online before holding any stock.",
     "Wizard-of-Oz: test demand before buying inventory."),
    ("Dropbox", {"saas", "software", "b2c", "tech"}, "idea",
     "Before the product was ready, Drew Houston published a short demo video showing how it would work; the beta waiting list grew from about 5,000 to 75,000 sign-ups overnight.",
     "When the product is hard to build, sell the demo first and collect a waiting list."),
    ("Buffer", {"saas", "software", "b2c", "b2b", "pricing"}, "idea",
     "In 2010 Joel Gascoigne put up a landing page describing the product with a 'Plans and pricing' button, then a page with paid plans, to see if people would pay before building it. He launched a simple version weeks later and had his first paying customer within days.",
     "Test willingness to pay with a landing page and a pricing page before building."),
    ("Stripe", {"fintech", "payments", "b2b", "saas", "software"}, "first_customers",
     "When a startup agreed to try Stripe, the founders did not send a link: they asked for the laptop and set Stripe up on the spot ('Collison installation').",
     "Remove every step between 'yes' and using the product; onboard first customers by hand."),
    ("Instagram", {"app", "b2c", "social"}, "mvp",
     "It began as Burbn, a check-in app with many features. Users mostly shared photos, so the founders cut everything else and relaunched as Instagram, which got 25,000 users on its first day in 2010.",
     "Watch what users actually use and cut the rest."),
    ("Slack", {"saas", "b2b", "software"}, "mvp",
     "Slack was the team's internal chat tool while they built a game (Glitch) that failed. They turned the tool into the product, gave it first to friendly companies and changed it on their feedback before opening it to everyone.",
     "Launch to a small group of real teams, iterate on their feedback, then open."),
    ("Groupon", {"marketplace", "local", "services", "b2c"}, "validation",
     "The first version in 2008 was a WordPress blog with one deal a day; the team emailed PDF coupons to buyers by hand.",
     "The simplest technology that delivers the value is enough to test demand."),
    ("Tinder", {"app", "b2c", "social", "network"}, "first_customers",
     "Early growth came from college campuses: a co-founder presented the app at sororities and fraternities so many students from the same campus joined at once.",
     "For network products, launch densely in one small community instead of everywhere."),
    ("Facebook", {"social", "network", "b2c", "app"}, "first_customers",
     "In 2004 it opened only at Harvard, then campus by campus, entering a new school only when it was ready.",
     "Win one small market completely before expanding."),
    ("Uber", {"mobility", "marketplace", "local", "transport"}, "growth",
     "It started as UberCab in San Francisco with a few black cars and expanded city by city, each launch run by a local team that recruited drivers before riders.",
     "Solve supply in one city first, then expand with a repeatable city playbook."),
    ("Amazon", {"ecommerce", "retail", "marketplace"}, "first_customers",
     "In 1995 it sold only books, a category with a huge catalogue that is easy to ship, before adding any other category.",
     "Start with one narrow category where you can be the best option."),
    ("Shopify", {"saas", "ecommerce", "software", "b2b"}, "validation",
     "The founders wanted to sell snowboards online (Snowdevil), found existing shop software poor, built their own, and then turned that software into the business.",
     "Your own painful problem can be the business; sell the tool, not only the goods."),
    ("Gojek", {"mobility", "delivery", "local", "marketplace", "emerging"}, "validation",
     "It started in Jakarta in 2010 as a call centre connecting customers with about 20 motorcycle-taxi drivers. The app came only in 2015, and later payments and food delivery.",
     "In emerging markets start with the channel people already use (phone, messenger); build the app when demand is proven."),
    ("Flipkart", {"ecommerce", "retail", "emerging", "b2c"}, "first_customers",
     "It started in 2007 selling books in India; the founders packed and delivered early orders themselves and introduced cash on delivery so people who did not trust online payment could still buy.",
     "Adapt to local trust: cash on delivery and personal service."),
    ("Zomato", {"food", "marketplace", "local", "emerging", "content"}, "idea",
     "It began in 2008 as Foodiebay: the founders scanned restaurant menus and put them online because colleagues kept asking for them. Revenue models came later.",
     "Start with information people already ask you for."),
    ("Careem", {"mobility", "b2b", "emerging", "transport"}, "first_customers",
     "It started in 2012 with car bookings for companies in Dubai before moving to consumer ride-hailing; Uber bought it in 2019 for $3.1 billion.",
     "Business customers can bring predictable early revenue and clear feedback."),
    ("Kaspi.kz", {"fintech", "payments", "ecommerce", "marketplace", "emerging", "central_asia"}, "scale",
     "In Kazakhstan it grew from a bank into one app for payments, bill pay and a marketplace, using everyday payments to bring people back to the app daily before adding more services.",
     "Win a frequent everyday use first, then add services on top of it."),
    ("Uzum", {"ecommerce", "marketplace", "fintech", "emerging", "central_asia", "delivery"}, "scale",
     "Uzum Market launched in Uzbekistan in 2022 with its own pick-up points and delivery, then built Uzum Bank, Uzum Nasiya instalments and Uzum Tezkor delivery around it; in 2024 it became Uzbekistan's first unicorn.",
     "Solve the market's trust and delivery problems (pick-up points, instalments) and build an ecosystem on a working core."),
    ("Superhuman", {"saas", "software", "b2c", "b2b"}, "traction",
     "Rahul Vohra asked users 'How would you feel if you could no longer use Superhuman?'. Only 22% answered 'very disappointed' at first; the team built for those users and raised it to 58%.",
     "Measure product-market fit with the 40% test and build for the users who love you."),
    ("Mailchimp", {"saas", "software", "b2b", "bootstrapped"}, "traction",
     "It grew for years as a side product of a web agency, funded by its own revenue; adding a free plan in 2009 multiplied its users.",
     "Grow on revenue without investors; a free tier can drive growth once the paid product works."),
    ("Canva", {"saas", "software", "edtech", "design"}, "idea",
     "Melanie Perkins first built Fusion Books in 2007, an online tool for designing school yearbooks, to prove the idea in a narrow market; Canva for all design came in 2013.",
     "Prove the idea in a narrow niche before the big vision."),
    ("WhatsApp", {"app", "b2c", "social"}, "mvp",
     "It began in 2009 as an app for status updates; once users started using statuses to message each other, the founders turned it into a messenger, run by a very small team.",
     "Follow what users do with the product, not the original plan."),
    ("PayPal", {"fintech", "payments", "b2c", "network"}, "traction",
     "It moved from payments between PalmPilots to email payments after seeing eBay sellers adopt it, and paid new users cash bonuses for signing up and inviting friends.",
     "Find the community that already needs you; referral rewards work when each user brings value."),
    ("Hotmail", {"app", "b2c", "network"}, "traction",
     "Every email sent from Hotmail ended with a line inviting the reader to get a free account, which spread it to millions of users within about 18 months.",
     "Build sharing into the product itself."),
    ("Wise", {"fintech", "payments", "b2c"}, "idea",
     "In 2011 two Estonians in London, tired of bank fees, swapped money with each other at the market rate; TransferWise turned that matching into a service.",
     "A cheaper way you already use yourself can be the product."),
    ("Pinterest", {"social", "b2c", "content", "network"}, "first_customers",
     "Early growth was slow; Ben Silbermann wrote personally to the first users and grew through a community that loved the product, including design bloggers, with meet-ups.",
     "Find the niche that loves you and grow through it by hand."),
    ("Warby Parker", {"ecommerce", "retail", "d2c", "b2c"}, "first_customers",
     "In 2010 it offered free home try-on of five frames to remove the fear of buying glasses online; early orders were handled from the founders' flat.",
     "Remove the customer's main fear of buying with a trial or guarantee."),
    ("Twitch", {"content", "b2c", "app"}, "traction",
     "Justin.tv was a general live-streaming site; gaming streams grew fastest, so the team spun them out as Twitch, which Amazon bought in 2014 for about $970 million.",
     "Double down on the segment that grows fastest."),
    ("Duolingo", {"edtech", "app", "b2c"}, "traction",
     "It first planned to earn by selling translations made by learners, then switched to a subscription (2017) and ads; it grows through streaks and constant A/B tests.",
     "Test the business model; in education, retention mechanics drive growth."),
    ("Basecamp", {"saas", "software", "b2b", "services", "bootstrapped"}, "validation",
     "The web agency 37signals built a project tool for its own client work, then sold it to others; it became the main business.",
     "Services can fund and validate a product."),
]

STAGE_ORDER = [p["stage"] for p in PLAYBOOK]

# Words in the intake (English, Russian, Uzbek) → case tags.
KEYWORDS = {
    "food": r"food|restaurant|cafe|meal|lunch|еда|кафе|ресторан|обед|блюд|ovqat|taom|restoran|kafe|tushlik",
    "delivery": r"deliver|courier|доставк|курьер|yetkaz|kuryer",
    "marketplace": r"marketplace|platform|match|connect|маркетплейс|платформ|площадк|связыва|соединя|подбор|bog'la|bog‘la|ulay|platforma",
    "app": r"\bapp\b|mobile|приложени|бот|bot\b|telegram|ilova",
    "saas": r"saas|software|crm|subscription for business|автоматиз|программ|сервис для бизнес|dastur",
    "b2b": r"b2b|business|office|бизнес|компани|офис|korxona|kompaniya|ofis",
    "edtech": r"educat|school|tutor|course|learn|обуч|школ|репетитор|курс|учени|ta'lim|ta‘lim|maktab|repetitor|kurs|o'quv|o‘quv",
    "fintech": r"fintech|payment|loan|credit|bank|insur|платеж|платёж|кредит|банк|финанс|страхов|to'lov|to‘lov|kredit|bank",
    "ecommerce": r"shop|store|e-?commerce|retail|goods|магазин|товар|интернет-магазин|продаж|do'kon|do‘kon|savdo|mahsulot",
    "mobility": r"taxi|ride|transport|logistic|такси|транспорт|логист|taksi",
    "d2c": r"brand|clothes|cosmetic|apparel|бренд|одежд|косметик|kiyim|kosmetika",
    "services": r"service|repair|clean|beauty|услуг|ремонт|уборк|салон|xizmat|ta'mir",
    "content": r"media|content|blog|video|контент|медиа|видео|блог",
    "travel": r"travel|hotel|tour|туризм|отель|тур\b|sayohat|mehmonxona",
    "social": r"social|community|сообществ|социальн|jamiyat",
}


def _stage_of(profile, answers):
    """A rough stage from the intake and the money, used only to choose cases."""
    stage = (profile.onboarding or {}).get("stage")
    said = " ".join(a.get("answer", "") for a in answers or []).lower()
    if stage == "operational":
        return "first_customers"
    if stage == "mvp" or re.search(r"mvp|прототип|prototype|работает|ishlay", said):
        return "mvp"
    return "idea"


def tags_of(profile, answers=None):
    o = profile.onboarding or {}
    text = " ".join(str(o.get(k, "")) for k in ("name", "problem", "description", "revenue_model", "alternatives"))
    text = f"{text} {profile.industry} " + " ".join(a.get("answer", "") for a in answers or [])
    text = text.lower()
    tags = {tag for tag, pattern in KEYWORDS.items() if re.search(pattern, text)}
    market = o.get("market")
    if market in ("b2b", "both"):
        tags.add("b2b")
    if market in ("b2c", "both"):
        tags.add("b2c")
    tags.update({"emerging", "central_asia", "local"})
    return tags


# Broad tags say little about how alike two startups are.
WEAK_TAGS = {"b2c", "b2b", "app"}
REGION_TAGS = {"emerging", "central_asia", "local"}


def pick_cases(profile, answers=None, n=8):
    """
    The cases closest to this startup: shared tags first, then stages near
    where it is. Two places are kept for the cases of its current and next
    stage, whatever their tags, so the near steps always have a model to copy.
    """
    tags = tags_of(profile, answers)
    here = STAGE_ORDER.index(_stage_of(profile, answers))

    def score(case):
        _, case_tags, stage, _, _ = case
        shared = case_tags & tags - REGION_TAGS
        overlap = sum(1 if t in WEAK_TAGS else 3 for t in shared)
        local = 2 if case_tags & {"emerging", "central_asia"} else 0
        distance = STAGE_ORDER.index(stage) - here
        # The stages just ahead matter most; the ones far behind least.
        nearness = 2 if 0 <= distance <= 2 else (1 if distance > 2 else 0)
        return (overlap + local + nearness, -abs(distance))

    ranked = sorted(CASES, key=score, reverse=True)
    chosen = ranked[: n - 2]
    near = [c for c in ranked if c not in chosen and STAGE_ORDER.index(c[2]) - here in (0, 1)]
    chosen += near[:2]
    return [{"name": c[0], "stage": c[2], "story": c[3], "lesson": c[4]} for c in chosen]


def playbook_text():
    """The playbook as compact text for the prompt."""
    lines = []
    for i, p in enumerate(PLAYBOOK, 1):
        lines.append(f'{i}. "{p["stage"]}" — {p["goal"]}')
        lines.append("   Exit criteria: " + "; ".join(p["exit"]))
        lines.append("   Proven tactics: " + "; ".join(p["tactics"]))
        lines.append("   Mistakes to avoid: " + "; ".join(p["mistakes"]))
    lines.append(FULL_STARTUP)
    return "\n".join(lines)
