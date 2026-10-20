"""
Sign-up assessment → personalised study plan.

Ten questions in two parts: five about the learner (no right answers) and a
five-question knowledge quiz (right answers, never sent to the client). Any of
them can be skipped. Both feed a Gemini call that picks and orders lessons.

The AI is strictly an *optimisation*: every failure path — no API key, a stub
response, malformed JSON, hallucinated lesson ids — falls back to the default
unit/lesson order, so onboarding always produces a usable plan.
"""
import json
import logging
import re

from django.db import transaction
from django.utils import timezone

from ai_engine.gemini import FEATURE_STUDY_PLAN, GeminiError, generate
from ai_engine.models import UserAIQuota
from ai_engine.quota import consume_and_log
from config import languages

from .models import Lesson, OnboardingAssessment, StudyPlan, StudyPlanItem

log = logging.getLogger("learning")

# --------------------------------------------------------------------------- #
# Question bank
# --------------------------------------------------------------------------- #
# Self-reported context. `id` values are stable keys stored in answers["profile"].
PROFILE_QUESTIONS = [
    {
        "id": "experience",
        "prompt": "How would you describe your experience with personal finance?",
        "choices": [
            "Complete beginner — I'm starting from scratch",
            "I know the basics but not much more",
            "I'm comfortable and want to go deeper",
        ],
    },
    {
        "id": "goal",
        "prompt": "What do you most want to get out of Zinvest?",
        "choices": [
            "Budget better and stop living paycheck to paycheck",
            "Start investing with confidence",
            "Understand business and launch a startup",
            "General financial literacy",
        ],
    },
    {
        "id": "time",
        "prompt": "How much time can you spend learning each week?",
        "choices": ["Under 1 hour", "1–3 hours", "More than 3 hours"],
    },
    {
        "id": "status",
        "prompt": "What best describes you right now?",
        "choices": [
            "At school",
            "At university or college",
            "Working for someone",
            "Running my own business",
        ],
    },
    {
        "id": "cushion",
        "prompt": "If your income stopped tomorrow, how long would your savings last?",
        "choices": [
            "I have no savings yet",
            "Less than a month",
            "One to three months",
            "More than three months",
        ],
    },
]

# Knowledge check. `answer_index` is stripped before this ever reaches a client.
QUIZ_QUESTIONS = [
    {
        "id": "q_compound",
        "prompt": "What does compound interest mean?",
        "choices": [
            "Interest paid only on the original amount",
            "Interest earned on both the original amount and past interest",
            "A fee charged when you withdraw early",
            "The tax applied to investment gains",
        ],
        "answer_index": 1,
    },
    {
        "id": "q_asset",
        "prompt": "Which of these is a liability rather than an asset?",
        "choices": [
            "A savings account balance",
            "A car you own outright",
            "An outstanding credit-card balance",
            "Shares in a company",
        ],
        "answer_index": 2,
    },
    {
        "id": "q_emergency",
        "prompt": "What is an emergency fund for?",
        "choices": [
            "Maximising long-term investment returns",
            "Covering unexpected costs without borrowing",
            "Paying your regular monthly bills",
            "Speculating on short-term market moves",
        ],
        "answer_index": 1,
    },
    {
        "id": "q_diversify",
        "prompt": "Diversifying a portfolio mainly reduces which risk?",
        "choices": [
            "The risk that any single investment performs badly",
            "The risk that inflation rises",
            "The risk of paying too much tax",
            "The risk that interest rates change",
        ],
        "answer_index": 0,
    },
    {
        "id": "q_net",
        "prompt": "What is net income?",
        "choices": [
            "Total earnings before any deductions",
            "Earnings left after taxes and deductions",
            "Money held in a current account",
            "Revenue minus the cost of goods only",
        ],
        "answer_index": 1,
    },
]

LEVEL_THRESHOLDS = ((0.8, "advanced"), (0.5, "intermediate"))

# The questions in the learner's language. English stays in the definitions
# above — the plan prompt is written from it — and only the words shown to the
# learner change; answers are indexes, so they mean the same in every language.
TRANSLATIONS = {
    "ru": {
        "experience": {"prompt": "Какой у вас опыт с личными финансами?",
                       "choices": ["Полный новичок — начинаю с нуля", "Знаю основы, но не больше",
                                   "Чувствую себя уверенно и хочу глубже"]},
        "goal": {"prompt": "Чего вы больше всего хотите от Zinvest?",
                 "choices": ["Лучше вести бюджет и перестать жить от зарплаты до зарплаты",
                             "Уверенно начать инвестировать", "Разобраться в бизнесе и запустить стартап",
                             "Общая финансовая грамотность"]},
        "time": {"prompt": "Сколько времени в неделю вы готовы учиться?",
                 "choices": ["Меньше часа", "1–3 часа", "Больше 3 часов"]},
        "status": {"prompt": "Кто вы сейчас?",
                   "choices": ["Учусь в школе", "Учусь в университете или колледже",
                               "Работаю по найму", "Веду свой бизнес"]},
        "cushion": {"prompt": "Если доход завтра пропадёт, на сколько хватит ваших сбережений?",
                    "choices": ["Сбережений пока нет", "Меньше чем на месяц",
                                "На один–три месяца", "Больше чем на три месяца"]},
        "q_compound": {"prompt": "Что такое сложный процент?",
                       "choices": ["Проценты только на исходную сумму",
                                   "Проценты и на исходную сумму, и на уже начисленные проценты",
                                   "Комиссия за досрочное снятие", "Налог на инвестиционный доход"]},
        "q_asset": {"prompt": "Что из этого — пассив, а не актив?",
                    "choices": ["Остаток на сберегательном счёте", "Машина, полностью ваша",
                                "Непогашенный долг по кредитной карте", "Акции компании"]},
        "q_emergency": {"prompt": "Для чего нужен резервный фонд?",
                        "choices": ["Чтобы максимизировать долгосрочную доходность",
                                    "Чтобы покрыть непредвиденные расходы без долгов",
                                    "Чтобы оплачивать обычные ежемесячные счета",
                                    "Чтобы спекулировать на краткосрочных движениях рынка"]},
        "q_diversify": {"prompt": "Диверсификация портфеля в основном снижает какой риск?",
                        "choices": ["Что одно конкретное вложение окажется неудачным", "Что вырастет инфляция",
                                    "Что придётся заплатить слишком много налогов", "Что изменятся процентные ставки"]},
        "q_net": {"prompt": "Что такое чистый доход?",
                  "choices": ["Весь заработок до любых вычетов", "Заработок после налогов и вычетов",
                              "Деньги на текущем счёте", "Выручка минус только себестоимость"]},
    },
    "uz": {
        "experience": {"prompt": "Shaxsiy moliya bo‘yicha tajribangiz qanday?",
                       "choices": ["Mutlaqo yangi boshlovchiman — noldan boshlayapman",
                                   "Asoslarni bilaman, lekin undan ko‘p emas",
                                   "O‘zimni ishonchli his qilaman va chuqurroq o‘rganmoqchiman"]},
        "goal": {"prompt": "Zinvest’dan eng ko‘p nimani kutasiz?",
                 "choices": ["Byudjetni yaxshiroq yuritish va maoshdan maoshgacha yashashni to‘xtatish",
                             "Ishonch bilan investitsiya qilishni boshlash", "Biznesni tushunish va startap ochish",
                             "Umumiy moliyaviy savodxonlik"]},
        "time": {"prompt": "Haftasiga o‘qishga qancha vaqt ajrata olasiz?",
                 "choices": ["1 soatdan kam", "1–3 soat", "3 soatdan ko‘p"]},
        "status": {"prompt": "Hozir kimsiz?",
                   "choices": ["Maktabda o‘qiyman", "Universitet yoki kollejda o‘qiyman",
                               "Ishlayman", "O‘z biznesimni yuritaman"]},
        "cushion": {"prompt": "Agar ertaga daromad to‘xtasa, jamg‘armangiz qancha vaqtga yetadi?",
                    "choices": ["Hozircha jamg‘arma yo‘q", "Bir oydan kamga",
                                "Bir oydan uch oygacha", "Uch oydan ko‘proqqa"]},
        "q_compound": {"prompt": "Murakkab foiz nima?",
                       "choices": ["Faqat dastlabki summaga hisoblanadigan foiz",
                                   "Ham dastlabki summaga, ham oldingi foizlarga hisoblanadigan foiz",
                                   "Muddatidan oldin yechib olish uchun komissiya", "Investitsiya daromadiga soliq"]},
        "q_asset": {"prompt": "Qaysi biri aktiv emas, balki majburiyat?",
                    "choices": ["Jamg‘arma hisobidagi qoldiq", "To‘liq o‘zingizniki bo‘lgan mashina",
                                "Kredit karta bo‘yicha to‘lanmagan qarz", "Kompaniya aksiyalari"]},
        "q_emergency": {"prompt": "Favqulodda jamg‘arma nima uchun kerak?",
                        "choices": ["Uzoq muddatli investitsiya daromadini maksimal qilish uchun",
                                    "Kutilmagan xarajatlarni qarz olmasdan qoplash uchun",
                                    "Oddiy oylik hisoblarni to‘lash uchun",
                                    "Bozordagi qisqa muddatli o‘zgarishlarda chayqovchilik uchun"]},
        "q_diversify": {"prompt": "Portfelni diversifikatsiya qilish asosan qaysi riskni kamaytiradi?",
                        "choices": ["Bitta investitsiya yomon natija berish riskini", "Inflyatsiya o‘sish riskini",
                                    "Ortiqcha soliq to‘lash riskini", "Foiz stavkalari o‘zgarish riskini"]},
        "q_net": {"prompt": "Sof daromad nima?",
                  "choices": ["Har qanday ushlanmalardan oldingi umumiy daromad",
                              "Soliq va ushlanmalardan keyin qolgan daromad",
                              "Joriy hisobdagi pul", "Tushum minus faqat tannarx"]},
    },
}


def _in_language(question, lang):
    """The question's words in `lang`, keeping its id (and never the answer)."""
    said = TRANSLATIONS.get(lang, {}).get(question["id"], {})
    choices = said.get("choices")
    if not choices or len(choices) != len(question["choices"]):
        choices = question["choices"]
    return {"id": question["id"], "prompt": said.get("prompt") or question["prompt"], "choices": choices}


def public_questions(lang=None):
    """The questionnaire as the client sees it, in its language — quiz answers stripped."""
    lang = languages.normalize(lang) or languages.current()
    return {
        "profile": [_in_language(q, lang) for q in PROFILE_QUESTIONS],
        "quiz": [_in_language(q, lang) for q in QUIZ_QUESTIONS],
    }


def grade_quiz(submitted):
    """Score the quiz. `submitted` is [{question_id, choice_index}, …]."""
    picked = {a.get("question_id"): a.get("choice_index") for a in submitted or []}
    graded = []
    correct = 0
    for q in QUIZ_QUESTIONS:
        got = picked.get(q["id"])
        is_right = got == q["answer_index"]
        correct += int(is_right)
        graded.append({"id": q["id"], "choice_index": got, "correct": is_right})
    score = correct / len(QUIZ_QUESTIONS) if QUIZ_QUESTIONS else 0.0
    return score, graded


def level_for(score):
    for threshold, level in LEVEL_THRESHOLDS:
        if score >= threshold:
            return level
    return "beginner"


# --------------------------------------------------------------------------- #
# Plan generation
# --------------------------------------------------------------------------- #
def _catalogue():
    return list(Lesson.objects.select_related("unit").order_by("unit__order", "order"))


def _profile_summary(profile):
    def label(qid):
        question = next((q for q in PROFILE_QUESTIONS if q["id"] == qid), None)
        idx = profile.get(qid)
        if question and isinstance(idx, int) and 0 <= idx < len(question["choices"]):
            return question["choices"][idx]
        return "not answered"

    return {q["id"]: label(q["id"]) for q in PROFILE_QUESTIONS}


def _prompt(lessons, profile, score, level):
    catalogue = "\n".join(
        f"- {les.id} | {les.unit.code} {les.unit.title} | {les.title}" for les in lessons
    )
    summary = _profile_summary(profile)
    return (
        "You are building a personalised financial-literacy study plan.\n\n"
        f"Learner profile:\n"
        f"- Experience: {summary.get('experience')}\n"
        f"- Main goal: {summary.get('goal')}\n"
        f"- Weekly time: {summary.get('time')}\n"
        f"- Right now: {summary.get('status')}\n"
        f"- Savings would last: {summary.get('cushion')}\n"
        f"- Knowledge quiz score: {score:.0%} (assessed level: {level})\n\n"
        f"Available lessons (id | unit | title):\n{catalogue}\n\n"
        "Order EVERY lesson id above into the sequence this learner should follow. "
        "Put the most relevant material for their goal and level first; do not omit "
        "or invent ids. Give each a reason of at most 12 words.\n"
        f"Write the rationale and every reason in {languages.name()} — the language "
        "the learner uses the app in.\n\n"
        'Reply with JSON only: {"rationale": "<=200 chars", '
        '"lessons": [{"id": "<uuid>", "reason": "<short>"}]}'
    )


def _parse_plan(text, valid_ids):
    """Pull the lesson ordering out of a model reply. Returns [] if unusable."""
    if not text:
        return [], ""
    blob = text.strip()
    # Models like to wrap JSON in ``` fences or prose; grab the outermost object.
    match = re.search(r"\{.*\}", blob, re.DOTALL)
    if not match:
        return [], ""
    try:
        data = json.loads(match.group(0))
    except (json.JSONDecodeError, ValueError):
        return [], ""

    ordered = []
    seen = set()
    for item in data.get("lessons") or []:
        lid = str(item.get("id", "")).strip()
        if lid in valid_ids and lid not in seen:
            seen.add(lid)
            ordered.append((lid, str(item.get("reason") or "")[:200]))
    return ordered, str(data.get("rationale") or "")[:500]


# Ordering lessons needs no long reasoning: with "thinking" on, Flash took
# ~20 s here and the learner watched "Building…" with nothing happening; off,
# it answers in ~5 s with the same plan. The timeout caps the wait for good —
# past it the default order is used, which is always a working plan.
PLAN_TIMEOUT_MS = 12000


def _plan_config():
    try:
        from google.genai import types
    except ImportError:  # no SDK: generate() answers with a stub anyway
        return None
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        response_mime_type="application/json",
        http_options=types.HttpOptions(timeout=PLAN_TIMEOUT_MS),
    )


def build_plan(user, assessment):
    """Generate and persist the user's plan. Always leaves a usable plan behind."""
    lessons = _catalogue()
    if not lessons:
        return None

    by_id = {str(les.id): les for les in lessons}
    profile = (assessment.answers or {}).get("profile") or {}
    ordered, rationale, source = [], "", StudyPlan.Source.DEFAULT

    # Quota is checked here rather than via @check_ai_quota: onboarding must never
    # hard-fail with a 429 — an exhausted allowance just means the default order.
    from adminpanel.models import PlatformSettings  # local: avoid an import cycle

    if PlatformSettings.current().ai_enabled and UserAIQuota.get_or_create_for(user).has_allowance():
        try:
            result = generate(
                FEATURE_STUDY_PLAN,
                _prompt(lessons, profile, assessment.quiz_score, assessment.level),
                config=_plan_config(),
            )
            consume_and_log(user, FEATURE_STUDY_PLAN, result)
            if not result.is_stub:
                ordered, rationale = _parse_plan(result.text, set(by_id))
                if ordered:
                    source = StudyPlan.Source.AI
        except GeminiError as exc:
            log.warning("study_plan_ai_failed user=%s err=%s", user.pk, exc)

    # Fallback / top-up: anything the model dropped keeps its default position.
    placed = {lid for lid, _ in ordered}
    ordered += [(str(les.id), "") for les in lessons if str(les.id) not in placed]

    with transaction.atomic():
        plan, _ = StudyPlan.objects.get_or_create(user=user)
        plan.source = source
        plan.level = assessment.level
        plan.rationale = rationale
        plan.save()
        plan.items.all().delete()
        StudyPlanItem.objects.bulk_create(
            [
                StudyPlanItem(plan=plan, lesson=by_id[lid], order=i, reason=reason)
                for i, (lid, reason) in enumerate(ordered)
            ]
        )
    return plan


def submit(user, profile_answers, quiz_answers):
    """Record the assessment and (re)build the plan from it."""
    score, graded = grade_quiz(quiz_answers)
    level = level_for(score)

    assessment, _ = OnboardingAssessment.objects.get_or_create(user=user)
    assessment.answers = {"profile": profile_answers or {}, "quiz": graded}
    assessment.quiz_score = score
    assessment.level = level
    assessment.completed_at = timezone.now()
    assessment.save()

    return assessment, build_plan(user, assessment)
